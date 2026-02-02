import json
import os
from pathlib import Path

import pytest

from zor import context_injector as ci


def test_find_context_file_upwards(tmp_path):
    base = tmp_path / "repo"
    sub = base / "sub" / "inner"
    sub.mkdir(parents=True)
    proj_ctx = base / ".context.md"
    proj_ctx.write_text("project facts")

    found = ci.find_context_file(start_path=sub)
    assert found is not None
    assert found.resolve() == proj_ctx.resolve()


def test_assemble_messages_with_global_and_project(tmp_path, monkeypatch):
    # Create project and global context files
    proj = tmp_path / "proj"
    proj.mkdir()
    proj_file = proj / ".context.md"
    proj_file.write_text("Project: X")

    global_file = tmp_path / "global.md"
    global_file.write_text("Global: Y")

    # Monkeypatch DEFAULT_GLOBAL to our file and start path
    monkeypatch.setattr(ci, "DEFAULT_GLOBAL", global_file)

    msgs = ci.assemble_messages("Hello", start_path=proj)
    assert any(m["role"] == "system" for m in msgs)
    sys = next(m for m in msgs if m["role"] == "system")
    assert "Global: Y" in sys["content"]
    assert "Project: X" in sys["content"]


def test_token_guard_and_approximation():
    short = "word " * 10
    over = "word " * 5000
    is_over_short, tokens_short = ci.token_guard(short, limit=2000)
    assert not is_over_short
    is_over_long, tokens_long = ci.token_guard(over, limit=2000)
    assert is_over_long
    assert tokens_long > 2000


def test_secret_scanner_detects():
    t = "this contains sk-ABCDEF1234567890 and AI_KEY in text"
    matches = ci.secret_scanner(t)
    assert matches


def test_init_and_clear(tmp_path):
    created = ci.init_command(target=tmp_path)
    assert created.exists()
    assert ".context.md" in created.name

    history = ci.clear_command(target=tmp_path)
    assert history.exists()
    assert json.loads(history.read_text(encoding="utf-8")) == []


def test_send_query_without_litellm(tmp_path, monkeypatch):
    # Ensure litellm is None for fallback behavior
    monkeypatch.setattr(ci, "litellm", None)
    res = ci.send_query("Hi there", start_path=tmp_path)
    assert res.get("note") == "litellm not installed"
    assert "payload" in res


def test_send_query_with_mocked_litellm(tmp_path, monkeypatch):
    class FakeChat:
        def create(self, model, messages):
            return {"id": "fake", "model": model, "messages": messages}

    class FakeClient:
        def __init__(self, **kwargs):
            self.chat = FakeChat()

    fake_module = type("fake", (), {"Client": FakeClient})
    monkeypatch.setattr(ci, "litellm", fake_module)

    # write a small context file so token guard doesn't block
    (tmp_path / ".context.md").write_text("short context")

    res = ci.send_query("Please summarize", start_path=tmp_path)
    assert res.get("sent") is True
    assert "response" in res
