"""Persistent Context Injection System

Provides discovery of `.context.md` files, prompt assembly with global fallback,
token guard, secret scanning, and simple CLI automation commands `init` and
`clear`.

Designed to be lightweight and dependency-tolerant. Uses `litellm` if
available for sending chat completions; otherwise prints the assembled payload.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import List, Optional, Tuple

try:
    import litellm
except Exception:  # pragma: no cover - optional dependency
    litellm = None

try:
    import tiktoken
except Exception:  # pragma: no cover - optional dependency
    tiktoken = None


DEFAULT_GLOBAL = Path.home() / ".config" / "ai" / "global.md"
HISTORY_FILENAME = ".context_history.json"


def find_context_file(start_path: Optional[Path] = None) -> Optional[Path]:
    """Search upwards for `.context.md`. If not found, fall back to
    `~/.config/ai/global.md` if it exists.

    Returns the Path to the project context if found, otherwise the global
    fallback Path if it exists, or None.
    """
    if start_path is None:
        start_path = Path.cwd()
    start_path = start_path.resolve()

    for current in [start_path] + list(start_path.parents):
        candidate = current / ".context.md"
        if candidate.is_file():
            return candidate

    if DEFAULT_GLOBAL.is_file():
        return DEFAULT_GLOBAL

    return None


def read_context_file(path: Path) -> str:
    with path.open("r", encoding="utf-8") as f:
        return f.read()


def assemble_messages(user_query: str, start_path: Optional[Path] = None) -> List[dict]:
    """Assemble chat messages with system message containing global +
    project context, followed by the user message.
    """
    project_ctx_path = find_context_file(start_path)
    global_ctx = ""
    project_ctx = ""

    # If the found file is the global fallback, treat it as global only.
    if project_ctx_path:
        try:
            if project_ctx_path.resolve() == DEFAULT_GLOBAL.resolve():
                global_ctx = read_context_file(project_ctx_path)
            else:
                # Try to read a global context too if present
                if DEFAULT_GLOBAL.is_file():
                    global_ctx = read_context_file(DEFAULT_GLOBAL)
                project_ctx = read_context_file(project_ctx_path)
        except Exception:
            # Best-effort: if resolving fails, just read what we can
            try:
                project_ctx = read_context_file(project_ctx_path)
            except Exception:
                project_ctx = ""

    system_parts = []
    if global_ctx:
        system_parts.append("[Global Context]\n" + global_ctx)
    if project_ctx:
        system_parts.append("[Project Context]\n" + project_ctx)

    system_message = "\n\n".join(system_parts).strip()

    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})

    messages.append({"role": "user", "content": user_query})
    return messages


def approximate_token_count(text: str) -> int:
    """Estimate tokens. Prefer `tiktoken` if available, else use a
    conservative approximation (words * 1.3).
    """
    if tiktoken is not None:
        try:
            enc = tiktoken.encoding_for_model("gpt-4o")
        except Exception:
            enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))

    # Fallback estimate
    words = len(re.findall(r"\S+", text))
    return int(words * 1.3)


def token_guard(text: str, limit: int = 2000) -> Tuple[bool, int]:
    """Return (is_over_limit, token_count)."""
    count = approximate_token_count(text)
    return (count > limit, count)


_SECRET_RE = re.compile(r"\b(sk-[A-Za-z0-9]{16,}|AI_KEY)\b")


def secret_scanner(text: str) -> List[str]:
    """Return list of discovered secret matches (may be empty)."""
    return _SECRET_RE.findall(text)


def init_command(target: Optional[Path] = None) -> Path:
    """Create a starter `.context.md` based on simple heuristics.

    Returns path to created file.
    """
    if target is None:
        target = Path.cwd()
    target = Path(target)

    ctx_path = target / ".context.md"
    if ctx_path.exists():
        raise FileExistsError(f"{ctx_path} already exists")

    hints = []
    # Inspect common files
    pkg = target / "package.json"
    req = target / "requirements.txt"
    pyproj = target / "pyproject.toml"

    if pkg.exists():
        try:
            pkg_json = json.loads(pkg.read_text(encoding="utf-8"))
            hints.append(f"Project: {pkg_json.get('name')} - {pkg_json.get('description','')}")
        except Exception:
            hints.append("JavaScript/Node project (package.json detected)")

    if req.exists():
        hints.append("Python dependencies listed in requirements.txt")

    if pyproj.exists():
        hints.append("Python project with pyproject.toml")

    # Basic folder heuristics
    if (target / "src").is_dir() or any(p.is_dir() for p in target.glob("*/src")):
        hints.append("Source code under `src/`")

    template = (Path(__file__).parent / "prompts" / "context_template.md")
    if template.exists():
        content = template.read_text(encoding="utf-8")
    else:
        content = (
            "# Project Context\n\n"
            "Provide short, relevant facts about this project. Keep it concise.\n\n"
            "- What the project does\n- Primary languages/frameworks\n- Important conventions\n"
        )

    if hints:
        header = "\n\n<!-- Auto-generated hints: " + ", ".join(hints) + " -->\n\n"
        content = content + header

    ctx_path.write_text(content, encoding="utf-8")
    return ctx_path


def clear_command(target: Optional[Path] = None) -> Path:
    """Clear conversation history file but keep `.context.md` intact.

    Returns the path to the history file that was cleared/created.
    """
    if target is None:
        target = Path.cwd()
    history_path = Path(target) / HISTORY_FILENAME
    history_path.write_text("[]", encoding="utf-8")
    return history_path


def save_history_entry(entry: dict, target: Optional[Path] = None) -> None:
    if target is None:
        target = Path.cwd()
    history_path = Path(target) / HISTORY_FILENAME
    if history_path.exists():
        try:
            data = json.loads(history_path.read_text(encoding="utf-8"))
        except Exception:
            data = []
    else:
        data = []
    data.append(entry)
    history_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def send_query(user_query: str, start_path: Optional[Path] = None, model: str = "gpt-4o") -> dict:
    """Assemble messages, run guards, and send to the LLM (or print payload).

    Returns dict with keys: `sent` (bool), `payload` (messages), and extra info.
    """
    messages = assemble_messages(user_query, start_path)

    # Check secrets and token counts on system messages
    system_text = ""
    for m in messages:
        if m["role"] == "system":
            system_text += "\n\n" + m["content"]

    secrets = secret_scanner(system_text)
    if secrets:
        return {"sent": False, "error": "secrets_detected", "secrets": secrets, "payload": messages}

    is_over, token_count = token_guard(system_text)
    if is_over:
        return {"sent": False, "error": "token_limit_exceeded", "tokens": token_count, "payload": messages}

    payload = {"messages": messages, "model": model}

    if litellm is None:
        # Fallback: don't call API, just return payload for the caller to handle
        save_history_entry({"user_query": user_query, "payload": payload}, start_path)
        return {"sent": False, "payload": payload, "note": "litellm not installed"}

    # Use litellm chat completion API pattern
    try:
        # Allow API key configuration via environment variables. Do NOT
        # encourage pasting keys into files; prefer `export ZOR_API_KEY=...`.
        kwargs = {}
        for env_name in ("ZOR_API_KEY", "AI_API_KEY", "LITELLM_API_KEY"):
            val = os.getenv(env_name)
            if val:
                kwargs["api_key"] = val
                break

        client = litellm.Client(**kwargs) if kwargs else litellm.Client()
        resp = client.chat.create(model=model, messages=messages)
        save_history_entry({"user_query": user_query, "response": resp}, start_path)
        return {"sent": True, "response": resp}
    except Exception as e:
        return {"sent": False, "error": str(e), "payload": payload}


def _cli():
    p = argparse.ArgumentParser(description="Persistent Context Injection CLI")
    sub = p.add_subparsers(dest="cmd")

    send_p = sub.add_parser("send", help="Send a user query to the LLM with context")
    send_p.add_argument("query", nargs="+", help="User query text")

    init_p = sub.add_parser("init", help="Create a starter .context.md in cwd")
    init_p.add_argument("path", nargs="?", help="Target directory (default cwd)")

    clear_p = sub.add_parser("clear", help="Clear conversation history")
    clear_p.add_argument("path", nargs="?", help="Target directory (default cwd)")

    args = p.parse_args()
    if args.cmd == "send":
        query = " ".join(args.query)
        res = send_query(query)
        print(json.dumps(res, indent=2, default=str))
    elif args.cmd == "init":
        target = Path(args.path) if args.path else None
        try:
            created = init_command(target)
            print(f"Created {created}")
        except FileExistsError as e:
            print(str(e))
    elif args.cmd == "clear":
        target = Path(args.path) if args.path else None
        cleared = clear_command(target)
        print(f"Cleared history at {cleared}")
    else:
        p.print_help()


if __name__ == "__main__":
    _cli()
