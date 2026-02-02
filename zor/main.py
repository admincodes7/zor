import os
import typer
from dotenv import load_dotenv
import google.generativeai as genai
from pathlib import Path
from .context import get_codebase_context
from .file_ops import edit_file, show_diff
from .git_utils import git_commit
from .api import generate_with_context
from .config import load_config, save_config
from .context_injector import init_command, clear_command, send_query
import json
from typing import Optional, Annotated, Callable, List
from functools import wraps
from typer.core import TyperGroup
from rich.console import Console
from rich.panel import Panel
import subprocess
import shutil

app = typer.Typer()

# load prompts
def load_prompt(prompt_name: str) -> str:
    """Load a prompt from the prompts directory"""
    prompt_path = Path(__file__).parent / "prompts" / f"{prompt_name}.txt"
    try:
        with open(prompt_path, "r") as f:
            return f.read()
    except FileNotFoundError:
        raise ValueError(f"Prompt file not found: {prompt_path}")

load_dotenv()

# Global flag to track if API key is validated
api_key_valid = False

# Load API key from environment or config
def load_api_key():
    global api_key_valid
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        config = load_config()
        api_key = config.get("api_key")
    
    if api_key:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content("Test")
            api_key_valid = True
            return True
        except Exception:
            api_key_valid = False
            return False
    
    api_key_valid = False
    return False

# Try to load API key on startup
load_api_key()

# Decorator to ensure API key exists before running commands
def require_api_key(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        global api_key_valid
        
        # Skip API key check for setup command
        if func.__name__ == "setup":
            return func(*args, **kwargs)
        
        # Check if API key is valid
        if not api_key_valid:
            typer.echo("No valid Gemini API key found. Please run 'zor setup' to configure your API key.", err=True)
            raise typer.Exit(1)
            
        return func(*args, **kwargs)
    return wrapper

@app.command()
def help():
    """Display all available commands and their descriptions"""
    from rich.console import Console
    from rich.table import Table
    
    console = Console()
    
    table = Table(title="Available Commands")
    table.add_column("Command", style="cyan")
    table.add_column("Description", style="green")
    
    commands = [
        ("ask", "Ask Zor about your codebase"),
        ("init", "Create a new project based on natural language instructions"),
        ("edit", "Edit a file based on natural language instructions"),
        ("commit", "Create a git commit with the given message"),
        ("config", "View configuration"),
        ("interactive", "Start an interactive session with the Zor AI assistant"),
        ("history", "Show conversation history"),
        ("generate-test", "Generate tests for a specific file"),
        ("refactor", "Refactor code across multiple files based on instructions"),
        ("setup", "Configure your Gemini API key"),
        ("help", "Display all available commands and their descriptions"),
        ("review", "Analyses the codebase and gives suggestions")
    ]
    
    for cmd, desc in commands:
        table.add_row(cmd, desc)
    
    console.print(table)
    console.print("\nFor more details on a specific command, run: zor [COMMAND] --help")

    if not api_key_valid:
        console.print("\n[bold red]Warning:[/bold red] No valid API key configured. Please run 'zor setup' first.", style="red")


@app.command()
@require_api_key
def ask(prompt: str):
    """Ask Zor about your codebase"""
    context = get_codebase_context()
    response = generate_with_context(prompt, context)
    print(response)


@app.command()
@require_api_key
def edit(file_path: str, prompt: str):
    """Edit a file based on natural language instructions"""
    # Check if file exists first
    if not Path(file_path).exists():
        typer.echo(f"Error: File {file_path} does not exist", err=True)
        return
        
    # Get current content of the file
    with open(file_path, "r") as f:
        original_content = f.read()
        
    context = get_codebase_context()
    instruction = f"Modify the file {file_path} to: {prompt}. Return only the complete new file content."
    response = generate_with_context(instruction, context)
    
    # Clean md res
    import re
    pattern = r"```(?:\w+)?\n(.*?)```"
    matches = re.findall(pattern, response, re.DOTALL)
    
    if matches:
        # Use the first code block found
        new_content = matches[0]
    else:
        # If no code block markers, use the response as is
        new_content = response
    
    # Show diff to user before confirmation
    show_diff(original_content, new_content, file_path)
    
    if typer.confirm("Apply these changes?"):
        if edit_file(file_path, new_content, preview=False):  # Set preview=False to avoid showing diff twice
            typer.echo("File updated successfully")
        else:
            typer.echo("File update failed", err=True)

@app.command()
def commit(message: str):
    """Create a git commit with the given message"""
    if git_commit(message):
        typer.echo("Commit created successfully")
    else:
        typer.echo("Commit failed", err=True)

@app.command()
def config(key: str = None, value: str = None):
    """View configuration"""
    current_config = load_config()
    
    if key is None and value is None:
        # Display current config
        for k, v in current_config.items():
            if k == "api_key" and v:
                # Don't show the actual API key, just indicate if it exists
                typer.echo(f"{k}: ***** (configured)")
            else:
                typer.echo(f"{k}: {v}")
                
        # Show API key status
        if not api_key_valid:
            typer.echo("\nWarning: No valid API key configured. Please run 'zor setup'.", err=True)
        return
    
    if key not in current_config:
        typer.echo(f"Unknown configuration key: {key}", err=True)
        return
    
    if value is None:
        if key == "api_key" and current_config[key]:
            typer.echo(f"{key}: ***** (configured)")
        else:
            typer.echo(f"{key}: {current_config[key]}")
        return

    current_type = type(current_config[key])
    if current_type == bool:
        current_config[key] = value.lower() in ("true", "1", "yes", "y")
    elif current_type == int:
        current_config[key] = int(value)
    elif current_type == float:
        current_config[key] = float(value)
    elif current_type == list:
        current_config[key] = value.split(",")
    else:
        current_config[key] = value
    
    save_config(current_config)
    typer.echo(f"Updated {key} to {current_config[key]}")

def extract_code_blocks(text):
    """Extract code blocks from markdown text"""
    import re
    pattern = r"```(?:\w+)?\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    return matches


@app.command("context-init")
def context_init(path: Optional[str] = typer.Argument(None)):
    """Create a starter .context.md using project heuristics (no API key required)."""
    target = Path(path) if path else Path(os.getcwd())
    try:
        created = init_command(target)
        typer.echo(f"Created {created}")
    except FileExistsError as e:
        typer.echo(str(e), err=True)


@app.command("context-clear")
def context_clear(path: Optional[str] = typer.Argument(None)):
    """Clear conversation history file (keeps `.context.md`)."""
    target = Path(path) if path else Path(os.getcwd())
    cleared = clear_command(target)
    typer.echo(f"Cleared history at {cleared}")


@app.command("context-send")
def context_send(query: str):
    """Assemble context and send a query using the configured environment API key.

    This command does NOT require the Gemini API key used elsewhere in this
    project; it uses the environment variables `ZOR_API_KEY`, `AI_API_KEY`, or
    `LITELLM_API_KEY` for the `litellm` client.
    """
    res = send_query(query, start_path=Path(os.getcwd()))
    typer.echo(json.dumps(res, indent=2, default=str))

@app.command()
@require_api_key
def interactive():
    """Start an interactive session with the Zor AI assistant"""
    typer.echo("Starting interactive session. Type 'exit' to quit.")
    typer.echo("Loading codebase context...")
    
    # load context once at the start
    context = get_codebase_context()
    typer.echo(f"Loaded context : {len(context)} tokens")
    
    # conversation history
    history = []
    
    while True:
        try:
            prompt = typer.prompt("\nWhat would you like to do?", prompt_suffix="\n> ")
            
            if prompt.lower() in ("exit", "quit"):
                break
                
            # add prompt to history
            history.append({"role": "user", "content": prompt})
            
            # create history string
            history_str = "\n".join(
                f"{'User' if h['role'] == 'user' else 'Assistant'}: {h['content']}" 
                for h in history[:-1]
            )
            
            # Create context for API call
            context_with_history = context.copy()
            if history_str:
                context_with_history["_conversation_history"] = history_str
            
            try:
                answer = generate_with_context(prompt, context_with_history)
                typer.echo(f"\n{answer}")
                
                # Add response to history
                history.append({"role": "assistant", "content": answer})
                
                # Check if we need to perform file operations
                if "```" in answer and "edit file" in prompt.lower():
                    # Simple extraction of code blocks (would need more sophisticated parsing in production)
                    file_to_edit = typer.prompt("Enter file path to edit")
                    if file_to_edit and Path(file_to_edit).exists():
                        code_blocks = extract_code_blocks(answer)
                        if code_blocks and typer.confirm("Apply these changes?"):
                            edit_file(file_to_edit, code_blocks[0], backup=True)
                            typer.echo(f"Updated {file_to_edit}")
                
            except Exception as e:
                typer.echo(f"Error: {e}", err=True)
                
        except KeyboardInterrupt:
            typer.echo("\nExiting interactive mode.")
            break
    
    typer.echo("Interactive session ended.")

@app.command()
@require_api_key
def history(limit: int = 5):
    """Show conversation history"""
    from rich.console import Console
    from rich.table import Table
    from .history import load_history
    
    console = Console()
    history_items = load_history(max_items=limit)
    
    if not history_items:
        console.print("No history found")
        return
    
    table = Table(title="Conversation History")
    table.add_column("Date", style="cyan")
    table.add_column("Prompt", style="green")
    table.add_column("Response", style="yellow")
    
    for item in history_items[-limit:]:
        # Truncate long text
        prompt = item["prompt"][:50] + "..." if len(item["prompt"]) > 50 else item["prompt"]
        response = item["response"][:50] + "..." if len(item["response"]) > 50 else item["response"]
        
        table.add_row(item["datetime"], prompt, response)
    
    console.print(table)

@app.command()
@require_api_key
def generate_test(file_path: str, test_framework: str = "pytest"):
    """Generate tests for a specific file"""
    if not Path(file_path).exists():
        typer.echo(f"Error: File {file_path} does not exist", err=True)
        return

    context = get_codebase_context()
    
    # Read the target file
    with open(file_path, "r") as f:
        target_file = f.read()
    
    # Create the prompt
    prompt = load_prompt("generate_test_prompt").format(
        test_framework=test_framework,
        target_file=target_file
    )
    
    # Generate the tests
    tests = generate_with_context(prompt, context)
    
    # Determine test file path
    test_file_path = str(Path(file_path).parent / f"test_{Path(file_path).name}")

    # clean
    code_blocks = extract_code_blocks(tests)

    if code_blocks:
        test_code = code_blocks[0]
    else:
        test_code = tests
    
    from rich.console import Console
    from rich.syntax import Syntax
    
    console = Console()
    console.print("\nGenerated test:")
    syntax = Syntax(test_code, "python", theme="monokai", line_numbers=True)
    console.print(syntax)
    
    # if test exists -> show diff
    if Path(test_file_path).exists():
        with open(test_file_path, "r") as f:
            existing_test_code = f.read()
        show_diff(existing_test_code, test_code, test_file_path)
    else:
        typer.echo(f"Note: Creating new test file at {test_file_path}")
    
    # Ask to save
    if typer.confirm(f"Save tests to {test_file_path}?"):
        with open(test_file_path, "w") as f:
            f.write(tests)
        typer.echo(f"Tests saved to {test_file_path}")

@app.command()
@require_api_key
def refactor(prompt: str):
    """Refactor code across multiple files based on instructions"""
    context = get_codebase_context()
    
    instruction = load_prompt("refactor_prompt").format(
        prompt=prompt
    )

    refactoring_plan = generate_with_context(instruction, context)
    
    # Parse the plan to extract file paths and contents
    import re
    file_changes = re.findall(r"FILE: (.+?)\n```(?:python|java|javascript|typescript)?\n(.+?)```", 
                             refactoring_plan, re.DOTALL)
    
    if not file_changes:
        typer.echo("No file changes were specified in the response.", err=True)
        return
    
    # Show summary of changes
    typer.echo(f"\nRefactoring will modify or create {len(file_changes)} files:")
    for file_path, _ in file_changes:
        file_path = file_path.strip()
        if Path(file_path).exists():
            typer.echo(f"- {file_path} (modify)")
        else:
            typer.echo(f"- {file_path} (create)")
    
    # Show diffs and ask for confirmation
    if typer.confirm("Show detailed changes?"):
        for file_path, new_content in file_changes:
            file_path = file_path.strip()
            try:
                # Read current content if file exists
                if Path(file_path).exists():
                    with open(file_path, "r") as f:
                        current_content = f.read()
                    show_diff(current_content, new_content, file_path)
                else:
                    typer.echo(f"\nNew file: {file_path}")
                    typer.echo("---")
                    typer.echo(new_content)
                    typer.echo("---")

            except Exception as e:
                typer.echo(f"Error processing {file_path}: {e}", err=True)
    
    # Confirm and apply changes
    if typer.confirm("Apply these changes?"):
        for file_path, new_content in file_changes:
            file_path = file_path.strip()
            try:
                # Create directory if needed
                Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
                # Write the new content to the file
                with open(file_path, "w") as f:
                    f.write(new_content)
                
                if Path(file_path).exists():
                    typer.echo(f"Updated {file_path}")
                else:
                    typer.echo(f"Failed to update {file_path}", err=True)
            except Exception as e:
                typer.echo(f"Error writing to {file_path}: {e}", err=True)

        # Offer to commit changes
        if typer.confirm("Commit these changes?"):
            commit_msg = typer.prompt("Enter commit message", default=f"Refactor: {prompt[:50]}")
            if git_commit(commit_msg):
                typer.echo("Changes committed successfully")

@app.command()
def setup():
    """Configure your Gemini API key"""
    global api_key_valid

    zor_ascii = """
███████╗ ██████╗ ██████╗
╚══███╔╝██╔═══██╗██╔══██╗
  ███╔╝ ██║   ██║██████╔╝
 ███╔╝  ██║   ██║██╔══██╗
███████╗╚██████╔╝██║  ██║
╚══════╝ ╚═════╝ ╚═╝  ╚═╝
"""
    # console = Console()
    #console.print(zor_ascii, style="bold green")
    typer.echo(zor_ascii)
    typer.echo("\n")
    
    config = load_config()
    current_api_key = config.get("api_key")
    
    # Check if API key already exists
    if current_api_key:
        if not typer.confirm("An API key is already configured. Do you want to replace it?", default=False):
            typer.echo("Setup cancelled. Keeping existing API key.")
            return

    api_key = typer.prompt("Enter your Gemini API key", hide_input=False, confirmation_prompt=True)
    
    # Validate API key
    typer.echo("Validating API key...")
    try:
        # Configure temporarily with the new key
        genai.configure(api_key=api_key)
        
        # Try a simple API call to validate the key
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content("Just respond with 'OK' if this API key is valid.")
        
        if not response or not hasattr(response, 'text') or "error" in response.text.lower():
            typer.echo("Error: The API key appears to be invalid.", err=True)
            return
            
        typer.echo("API key validated successfully!")
        api_key_valid = True
    except Exception as e:
        typer.echo(f"Error: Unable to validate API key: {str(e)}", err=True)
        if not typer.confirm("The API key could not be validated. Save it anyway?", default=False):
            return
    
    # Create .env file or update existing one
    env_path = Path(".env")
    
    # Check if file exists and contains the API key
    env_content = ""
    if env_path.exists():
        with open(env_path, "r") as f:
            env_content = f.read()
    
    # Update or add the API key
    if "GEMINI_API_KEY=" in env_content:
        import re
        env_content = re.sub(r"GEMINI_API_KEY=.*", f"GEMINI_API_KEY={api_key}", env_content)
    else:
        env_content += f"\nGEMINI_API_KEY={api_key}\n"
    
    # Write the updated content
    try:
        with open(env_path, "w") as f:
            f.write(env_content)
        
        # Also store in global config
        config["api_key"] = api_key
        save_config(config)
        
        # Update the current session's API key
        genai.configure(api_key=api_key)
        
        typer.echo("API key configured and saved successfully!")
        typer.echo("You can now use zor with your Gemini API key.")
    except Exception as e:
        typer.echo(f"Error saving API key: {str(e)}", err=True)

# NEW FEAT: INIT
@app.command()
@require_api_key
def init(prompt: str, directory: str = None, install: bool = typer.Option(True, "--install", "-i", help="Install dependencies after project creation"), run: bool = typer.Option(True, "--run", "-r", help="Run the application after setup")):
    """Create a new project based on natural language instructions and optionally install dependencies and run the app"""
    console = Console()
    
    # Handle project directory
    if directory:
        project_dir = Path(directory)
    else:
        # Extract project name from prompt using more intelligent parsing
        words = prompt.lower().split()
        project_name = words[0].replace(" ", "_")
        
        # Check for actual project name in the first few words
        name_indicators = ["called", "named", "name", "project"]
        for i, word in enumerate(words):
            if word in name_indicators and i+1 < len(words):
                project_name = words[i+1].replace(" ", "_")
                break
        
        # Confirm with user
        project_dir = Path(typer.prompt(
            "Project directory name", 
            default=project_name
        ))
    
    # Store the original user-specified directory
    orig_project_dir = project_dir
    
    # Check if directory exists
    if project_dir.exists() and any(project_dir.iterdir()):
        if not typer.confirm(f"Directory {project_dir} exists and is not empty. Continue anyway?", default=False):
            typer.echo("Project initialization cancelled.")
            raise typer.Exit()
    
    # Create directory if it doesn't exist
    project_dir.mkdir(exist_ok=True, parents=True)
    
    # Generate project structure based on prompt
    with console.status("[bold green]Analyzing project requirements...", spinner="dots") as status:
        context = {"project_prompt": prompt}

        planning_prompt = load_prompt("planning_prompt").format(
                prompt=prompt,
        )
        status.update("[bold green]Generating project blueprint...")
        plan_response = generate_with_context(planning_prompt, context)
        
        # Parse the response to extract project information
        import re
        import shlex
        import subprocess
        import sys
        import os
        import shutil
        import json
        
        # Extract all sections with improved regex patterns
        sections = {
            "project_type": re.search(r"PROJECT_TYPE:\s*(.*?)(?:\n\s*\n|\n\s*[A-Z_]+:)", plan_response + "\n\n", re.DOTALL),
            "main_technologies": re.search(r"MAIN_TECHNOLOGIES:\s*(.*?)(?:\n\s*\n|\n\s*[A-Z_]+:)", plan_response + "\n\n", re.DOTALL),
            "architecture": re.search(r"ARCHITECTURE:\s*(.*?)(?:\n\s*\n|\n\s*[A-Z_]+:)", plan_response + "\n\n", re.DOTALL),
            "scaffold_command": re.search(r"SCAFFOLD_COMMAND:\s*(.*?)(?:\n\s*\n|\n\s*[A-Z_]+:)", plan_response + "\n\n", re.DOTALL),
            "scaffold_type": re.search(r"SCAFFOLD_TYPE:\s*(.*?)(?:\n\s*\n|\n\s*[A-Z_]+:)", plan_response + "\n\n", re.DOTALL),
            "dependencies": re.search(r"DEPENDENCIES:(.*?)(?:\n\s*\n|\n\s*[A-Z_]+:)", plan_response + "\n\n", re.DOTALL),
            "setup_commands": re.search(r"SETUP_COMMANDS:(.*?)(?:\n\s*\n|\n\s*[A-Z_]+:)", plan_response + "\n\n", re.DOTALL),
            "development_recommendations": re.search(r"DEVELOPMENT_RECOMMENDATIONS:(.*?)(?:\n\s*\n|\n\s*[A-Z_]+:|$)", plan_response + "\n\n", re.DOTALL)
        }
        
        # Process extracted sections
        project_info = {}
        for key, match in sections.items():
            project_info[key] = match.group(1).strip() if match else "Not specified"
        
        # Get project information with fallbacks
        project_type = project_info.get("project_type", "Unknown")
        scaffold_command = project_info.get("scaffold_command", "NONE")
        scaffold_type = project_info.get("scaffold_type", "NONE").upper()
        dependencies = project_info.get("dependencies", "")
        
        # Extract specific dependencies for later installation
        extracted_dependencies = []
        if dependencies != "Not specified":
            # Parse dependencies from the formatted list
            dep_lines = dependencies.strip().split('\n')
            for line in dep_lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = re.split(r'[:,\s]\s*', line.lstrip('- ').strip())
                    if parts:
                        package_name = parts[0].strip()
                        version = parts[1].strip() if len(parts) > 1 else ""
                        if package_name and not package_name.startswith('#'):
                            if version and version.startswith('^') or version.startswith('~'):
                                extracted_dependencies.append(f"{package_name}@{version}")
                            else:
                                extracted_dependencies.append(package_name)
        
        # Show the project plan to the user with improved formatting
        status.stop()
        
        console.print("\n[bold cyan]📋 Project Blueprint[/bold cyan]")
        console.print(f"\n[bold]Project Type:[/bold] {project_type}")
        
        if project_info.get("main_technologies") != "Not specified":
            console.print(f"\n[bold]Main Technologies:[/bold]")
            console.print(project_info.get("main_technologies"))
            
        if project_info.get("architecture") != "Not specified":
            console.print(f"\n[bold]Architecture:[/bold]")
            console.print(project_info.get("architecture"))
        
        console.print("\n[bold]Project Plan:[/bold]")
        console.print(plan_response)
        
        # Confirm with user before proceeding
        if not typer.confirm("\nProceed with project creation?", default=True):
            typer.echo("Project initialization cancelled.")
            raise typer.Exit()
        

        # Replace the existing scaffold command execution section with this improved version
        if scaffold_command and scaffold_command.lower() != "none":
            # Parse the original scaffold command
            command_parts = shlex.split(scaffold_command)
            project_name = project_dir.name
            
            # Handle different scaffold types properly
            if scaffold_type == "CREATES_OWN_DIR":
                if "create-react-app" in scaffold_command:
                    # For create-react-app, the format is: npx create-react-app project-name
                    scaffold_command = f"npx create-react-app {project_name}"
                elif "vue@latest" in scaffold_command:
                    # For Vue: npm init vue@latest project-name
                    scaffold_command = f"npm init vue@latest {project_name}"
                elif "ng new" in scaffold_command:
                    # For Angular: ng new project-name
                    scaffold_command = f"ng new {project_name}"
                elif "create-next-app" in scaffold_command:
                    # For Next.js: npx create-next-app project-name
                    # Determine flags for Next.js interactive prompts
                    next_flags = ""
                    
                    # Only add flags if the user wants to bypass interactive mode
                    if not typer.confirm("Do you want to use Next.js interactive setup? (No will use default settings)", default=True):
                        # Get user preferences for Next.js setup
                        use_typescript = typer.confirm("Use TypeScript?", default=True)
                        use_eslint = typer.confirm("Use ESLint?", default=True)
                        use_tailwind = typer.confirm("Use Tailwind CSS?", default=True)
                        use_src_dir = typer.confirm("Use src/ directory?", default=True)
                        use_app_router = typer.confirm("Use App Router? (recommended)", default=True)
                        customize_import_alias = typer.confirm("Customize import alias?", default=False)
                        
                        # Build flags based on preferences
                        if use_typescript:
                            next_flags += " --typescript"
                        else:
                            next_flags += " --no-typescript"
                            
                        if use_eslint:
                            next_flags += " --eslint"
                        else:
                            next_flags += " --no-eslint"
                            
                        if use_tailwind:
                            next_flags += " --tailwind"
                        else:
                            next_flags += " --no-tailwind"
                            
                        if use_src_dir:
                            next_flags += " --src-dir"
                        else:
                            next_flags += " --no-src-dir"
                            
                        if use_app_router:
                            next_flags += " --app"
                        else:
                            next_flags += " --no-app"
                            
                        if customize_import_alias:
                            import_alias = typer.prompt("Import alias (default is @)", default="@")
                            next_flags += f" --import-alias=\"{import_alias}\""
                        
                        # Add all flags to the command
                        scaffold_command = f"npx create-next-app {project_name}{next_flags}"
                    else:
                        scaffold_command = f"npx create-next-app {project_name}"
                    # For Vue.js interactive setup
                elif "vue@latest" in scaffold_command:
                    # For Vue: npm init vue@latest project-name
                    if typer.confirm("Do you want to use Vue.js interactive setup? (No will use default settings)", default=True):
                        scaffold_command = f"npm init vue@latest {project_name}"
                    else:
                        # Get user preferences for Vue.js setup
                        use_typescript = typer.confirm("Add TypeScript?", default=False)
                        use_jsx = typer.confirm("Add JSX Support?", default=False)
                        use_router = typer.confirm("Add Vue Router for Single Page Application development?", default=True)
                        use_pinia = typer.confirm("Add Pinia for state management?", default=False)
                        use_vitest = typer.confirm("Add Vitest for unit testing?", default=False)
                        use_eslint = typer.confirm("Add ESLint for code quality?", default=True)
                        use_prettier = typer.confirm("Add Prettier for code formatting?", default=True)
                        
                        # Build the command with all the flags
                        vue_flags = ""
                        if use_typescript:
                            vue_flags += " --typescript"
                        if use_jsx:
                            vue_flags += " --jsx"
                        if use_router:
                            vue_flags += " --router"
                        if use_pinia:
                            vue_flags += " --pinia"
                        if use_vitest:
                            vue_flags += " --vitest"
                        if use_eslint:
                            vue_flags += " --eslint"
                        if use_prettier:
                            vue_flags += " --prettier"
                            
                        # Add all flags to the command (note: Vue CLI requires -- to pass flags)
                        scaffold_command = f"npm init vue@latest {project_name} -- {vue_flags}"

                # For Angular with interactive prompts
                elif "ng new" in scaffold_command:
                    if typer.confirm("Do you want to use Angular interactive setup? (No will use default settings)", default=True):
                        scaffold_command = f"ng new {project_name}"
                    else:
                        # Get user preferences for Angular setup
                        use_routing = typer.confirm("Would you like to add Angular routing?", default=True)
                        style_format = typer.prompt(
                            "Which stylesheet format would you like to use?",
                            default="CSS",
                            type=click.Choice(["CSS", "SCSS", "Sass", "Less"])
                        )
                        
                        # Build the command with all the flags
                        ng_flags = ""
                        if use_routing:
                            ng_flags += " --routing=true"
                        else:
                            ng_flags += " --routing=false"
                            
                        ng_flags += f" --style={style_format.lower()}"
                        
                        # Add all flags to the command
                        scaffold_command = f"ng new {project_name}{ng_flags}"
                else:
                    # Default behavior for other commands
                    has_project_arg = False
                    project_name_position = -1
                    for i, part in enumerate(command_parts[1:], 1): 
                        if not part.startswith("-") and "/" not in part and "=" not in part:
                            has_project_arg = True
                            project_name_position = i
                            break

                    if has_project_arg:
                        original_name = command_parts[project_name_position]
                        command_parts[project_name_position] = project_name
                        scaffold_command = " ".join(command_parts)
                    else:
                        scaffold_command = f"{scaffold_command} {project_name}"

                if project_dir.exists():
                    if any(project_dir.iterdir()):
                        if typer.confirm(f"Directory {project_dir} exists. Remove it for clean scaffolding?", default=False):
                            try:
                                shutil.rmtree(project_dir)
                                console.print(f"[bold]Removed existing directory: {project_dir}[/bold]")
                            except Exception as e:
                                console.print(f"[bold red]Error removing directory: {str(e)}[/bold red]")
                                if not typer.confirm("Continue anyway?", default=False):
                                    typer.echo("Project initialization cancelled.")
                                    raise typer.Exit()
                    else:
                        # If directory exists but is empty, remove it anyway for clean scaffolding
                        try:
                            project_dir.rmdir()
                            console.print(f"[bold]Removed empty directory: {project_dir}[/bold]")
                        except Exception as e:
                            console.print(f"[bold yellow]Could not remove empty directory: {str(e)}[/bold yellow]")
                
                # The working directory will be the parent directory
                working_dir = project_dir.parent

                
                
            elif scaffold_type == "NEEDS_EMPTY_DIR":
                # For NEEDS_EMPTY_DIR, we'll run inside the project directory but ensure it's empty
                if any(project_dir.iterdir()):
                    if typer.confirm(f"Directory {project_dir} is not empty. Clear it for scaffolding?", default=False):
                        try:
                            # Remove all contents but keep the directory
                            for item in project_dir.iterdir():
                                if item.is_dir():
                                    shutil.rmtree(item)
                                else:
                                    item.unlink()
                            console.print(f"[bold]Cleared directory contents: {project_dir}[/bold]")
                        except Exception as e:
                            console.print(f"[bold red]Error clearing directory: {str(e)}[/bold red]")
                            if not typer.confirm("Continue anyway?", default=False):
                                typer.echo("Project initialization cancelled.")
                                raise typer.Exit()
                
                # Check if the command has a project name and remove it if needed
                for i, part in enumerate(command_parts[1:], 1):
                    if not part.startswith("-") and "/" not in part and "=" not in part:
                        # Remove the project name since we're running in the directory already
                        command_parts.pop(i)
                        scaffold_command = " ".join(command_parts)
                        break
                
                working_dir = project_dir
                
            else:  # IN_PLACE or default
                # For IN_PLACE, we'll just run in the directory
                working_dir = project_dir
            
            # If command has placeholders, replace them
            if "{project_name}" in scaffold_command:
                scaffold_command = scaffold_command.replace("{project_name}", project_name)
            if "{project_dir}" in scaffold_command:
                scaffold_command = scaffold_command.replace("{project_dir}", str(project_dir))
            
            # Ask user permission to run the scaffold command
            console.print(f"\n[bold]Official scaffolding command detected:[/bold]")
            console.print(f"[green]{scaffold_command}[/green]")
            console.print(f"Scaffold type: [cyan]{scaffold_type}[/cyan]")
            console.print(f"Will execute in: [cyan]{working_dir}[/cyan]")
            
            if typer.confirm("\nRun this scaffolding command?", default=True):
                console.print("\n[bold green]Executing scaffolding command...[/bold green]")
                
                # Replace the existing subprocess.run block with this improved version that handles interactive inputs
                try:
                    # Handle platform-specific command execution
                    shell = False
                    if sys.platform == "win32":
                        shell = True
                        # On Windows, use shell=True for npm/npx commands
                        
                        # Check if this is an interactive command (Next.js, Vue, etc.)
                        requires_interaction = (
                            "create-next-app" in scaffold_command and "--typescript" not in scaffold_command or
                            "vue@latest" in scaffold_command and "--typescript" not in scaffold_command or
                            "ng new" in scaffold_command and "--routing" not in scaffold_command
                        )
                        
                        if requires_interaction:
                            console.print("[yellow]Running interactive command. Please respond to prompts...[/yellow]")
                            # For interactive commands, don't capture output so user can interact directly
                            process = subprocess.run(
                                scaffold_command,
                                cwd=working_dir,
                                shell=shell
                            )
                        else:
                            # Non-interactive commands can capture output
                            process = subprocess.run(
                                scaffold_command,
                                cwd=working_dir,
                                capture_output=True,
                                text=True,
                                shell=shell
                            )
                    else:
                        # Split the command properly using shlex for Unix-like systems
                        command_args = shlex.split(scaffold_command)
                        
                        # Check if this is an interactive command (Next.js, Vue, etc.)
                        requires_interaction = (
                            "create-next-app" in scaffold_command and "--typescript" not in scaffold_command or
                            "vue@latest" in scaffold_command and "--typescript" not in scaffold_command or
                            "ng new" in scaffold_command and "--routing" not in scaffold_command
                        )
                        
                        if requires_interaction:
                            console.print("[yellow]Running interactive command. Please respond to prompts...[/yellow]")
                            # For interactive commands, don't capture output so user can interact directly
                            process = subprocess.run(
                                command_args,
                                cwd=working_dir,
                                shell=shell
                            )
                        else:
                            # Non-interactive commands can capture output
                            process = subprocess.run(
                                command_args,
                                cwd=working_dir,
                                capture_output=True,
                                text=True,
                                shell=shell
                            )
                    
                    if process.returncode == 0:
                        if hasattr(process, 'stdout') and process.stdout:
                            console.print(f"[bold green]Scaffolding completed successfully![/bold green]")
                            console.print(process.stdout)
                        else:
                            console.print(f"[bold green]Scaffolding completed successfully![/bold green]")
                    else:
                        if hasattr(process, 'stderr') and process.stderr:
                            console.print(f"[bold red]Scaffolding command failed with code {process.returncode}[/bold red]")
                            console.print(f"Error: {process.stderr}")
                        else:
                            console.print(f"[bold red]Scaffolding command failed with code {process.returncode}[/bold red]")
                        
                        # Ask if user wants to continue with file generation even though scaffolding failed
                        if not typer.confirm("Continue with file generation anyway?", default=False):
                            typer.echo("Project initialization cancelled.")
                            raise typer.Exit()
                except Exception as e:
                    console.print(f"[bold red]Error executing scaffolding command: {str(e)}[/bold red]")
                    
                    # Ask if user wants to continue with file generation despite the error
                    if not typer.confirm("Continue with file generation anyway?", default=False):
                        typer.echo("Project initialization cancelled.")
                        raise typer.Exit()
        # Improved file generation prompt with more context - now considers scaffolded files
        file_generation_prompt = load_prompt("file_generation").format(
            prompt=prompt,
            project_type=project_type,
            scaffold_command=scaffold_command
        )
        # Generate file contents
        with console.status("[bold green]Generating additional project files...", spinner="dots") as status:
            files_response = generate_with_context(file_generation_prompt, context)
            status.stop()
            
        # Parse the response to extract file paths and contents
        file_matches = re.findall(r"FILE: (.+?)\n```(?:\w+)?\n(.+?)```", files_response, re.DOTALL)
        
        if not file_matches:
            typer.echo("Error: Could not parse file generation response", err=True)
            console.print(files_response)
            raise typer.Exit(1)
        
        # Create the files with improved error handling and reporting
        console.print(Panel.fit(f"Creating {len(file_matches)} additional files...", title="File Creation"))
        
        created_files = []
        failed_files = []
        skipped_files = []
        
        # Extract dependency imports from React files to add to package.json later
        import_patterns = [
            r'import\s+.*?\s+from\s+[\'"]([^.][^\'"]*)[\'"]\s*;?',  # ES6 imports
            r'require\s*\(\s*[\'"]([^.][^\'"]*)[\'"]\s*\)',  # CommonJS imports
            r'@import\s+[\'"]([^.][^\'"]*)[\'"]\s*;?',      # CSS imports
        ]
        
        detected_dependencies = set()
        
        for file_path, content in file_matches:
            full_path = project_dir / file_path.strip()
            
            # Check if this is a JS/JSX/TS/TSX file to scan for imports
            if file_path.endswith(('.js', '.jsx', '.ts', '.tsx')):
                for pattern in import_patterns:
                    imports = re.findall(pattern, content)
                    for imported in imports:
                        # Filter out relative imports and standard node modules
                        if (not imported.startswith('.') and 
                            not imported.startswith('node:') and 
                            imported != 'react' and
                            imported != 'react-dom' and
                            not imported.startswith('fs') and
                            not imported.startswith('path')):
                            
                            # Handle scope packages and extract base package name
                            if '/' in imported:
                                parts = imported.split('/')
                                if parts[0].startswith('@'):
                                    # It's a scoped package like @mui/material
                                    base_package = f"{parts[0]}/{parts[1]}"
                                else:
                                    # It's a submodule like react-router/dom
                                    base_package = parts[0]
                            else:
                                base_package = imported
                            
                            detected_dependencies.add(base_package)
            
            # Check if file already exists (might have been created by scaffolding)
            if full_path.exists():
                # Ask if user wants to overwrite existing files
                if typer.confirm(f"File {file_path} already exists. Overwrite?", default=False):
                    try:
                        with open(full_path, "w") as f:
                            f.write(content)
                        created_files.append(str(full_path))
                        console.print(f"Overwritten: [blue]{file_path}[/blue]")
                    except Exception as e:
                        failed_files.append((file_path, str(e)))
                        console.print(f"Error overwriting {file_path}: {str(e)}", style="bold red")
                else:
                    console.print(f"Skipped (already exists): [yellow]{file_path}[/yellow]")
                    skipped_files.append(str(full_path))
                continue
                  
            # Create directories if they don't exist
            try:
                full_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write the file
                with open(full_path, "w") as f:
                    f.write(content)
                created_files.append(str(full_path))
                console.print(f"Created: [green]{file_path}[/green]")
            except Exception as e:
                failed_files.append((file_path, str(e)))
                console.print(f"Error creating {file_path}: {str(e)}", style="bold red")
        
        # After creating files but before running setup commands, check for important files
        try:
            # Check for important files based on project type
            missing_files = []
            critical_file_patterns = {
                "react": ["package.json", "src/App.*", "public/index.html"],
                "vue": ["package.json", "src/App.vue", "src/main.js"],
                "angular": ["package.json", "angular.json", "src/app"],
                "next.js": ["package.json", "next.config.js"],
                "express": ["package.json", "app.js"],
                "django": ["manage.py", "*/settings.py"],
                "flask": ["app.py", "requirements.txt"],
                "spring": ["pom.xml", "src/main/java"],
                "laravel": ["composer.json", "artisan"],
                ".net": ["*.csproj", "Program.cs"],
                "flutter": ["pubspec.yaml", "lib/main.dart"]
            }
            
            # Determine project type based on keywords in project_type
            detected_types = []
            project_type_lower = project_type.lower()
            
            for framework in critical_file_patterns.keys():
                if framework.lower() in project_type_lower:
                    detected_types.append(framework)
            
            # Determine if this is a Node.js or other type of project
            is_node_project = (project_dir / "package.json").exists()
            is_python_project = (project_dir / "requirements.txt").exists() or (project_dir / "setup.py").exists() or list(project_dir.glob("*.py"))
            
            # If no specific type detected but we have additional clues
            if not detected_types:
                if is_node_project and any("react" in file for file in created_files):
                    detected_types.append("react")
                elif is_node_project and any("vue" in file for file in created_files):
                    detected_types.append("vue")
                elif is_node_project and any("angular" in file for file in created_files):
                    detected_types.append("angular")
                elif is_node_project and any("next" in file for file in created_files):
                    detected_types.append("next.js")
                elif is_node_project and any("express" in file for file in created_files):
                    detected_types.append("express")
                elif is_python_project and any("django" in file for file in created_files):
                    detected_types.append("django")
                elif is_python_project and any("flask" in file for file in created_files):
                    detected_types.append("flask")
            
            # Check for missing critical files for each detected type
            for detected_type in detected_types:
                patterns = critical_file_patterns.get(detected_type, [])
                for pattern in patterns:
                    # Handle wildcards in patterns
                    found = False
                    if "*" in pattern:
                        matching_files = list(project_dir.glob(pattern))
                        found = len(matching_files) > 0
                    else:
                        found = (project_dir / pattern).exists()
                    
                    if not found:
                        missing_files.append((detected_type, pattern))
            
            # Notify user of missing files
            if missing_files:
                console.print("\n[bold yellow]Warning: Some expected files are missing:[/bold yellow]")
                for framework, file_pattern in missing_files:
                    console.print(f" - Missing [{framework}]: {file_pattern}")
                console.print("This may indicate incomplete project scaffolding. Consider checking the files manually.")
        except Exception as e:
            console.print(f"\n[bold yellow]Warning: Error checking for critical files: {str(e)}[/bold yellow]")
        
        # Merge detected dependencies with those from the plan
        if detected_dependencies:
            console.print(f"\n[bold cyan]Detected additional dependencies from imports:[/bold cyan]")
            for dep in sorted(detected_dependencies):
                console.print(f" - {dep}")
                if dep not in extracted_dependencies:
                    extracted_dependencies.append(dep)
        
        # Update package.json with detected dependencies if needed
        if is_node_project and detected_dependencies:
            package_json_path = project_dir / "package.json"
            if package_json_path.exists():
                try:
                    with open(package_json_path, "r") as f:
                        package_data = json.load(f)
                    
                    # Check if dependencies section exists
                    if "dependencies" not in package_data:
                        package_data["dependencies"] = {}
                    
                    # Add missing dependencies with default version
                    dependencies_modified = False
                    for dep in detected_dependencies:
                        if dep not in package_data["dependencies"]:
                            package_data["dependencies"][dep] = "latest"
                            dependencies_modified = True
                    
                    # Save updated package.json
                    if dependencies_modified:
                        with open(package_json_path, "w") as f:
                            json.dump(package_data, f, indent=2)
                        console.print(f"[bold green]Updated package.json with detected dependencies[/bold green]")
                except Exception as e:
                    console.print(f"[bold yellow]Could not update package.json: {str(e)}[/bold yellow]")
        
        # Provide a summary of file creation
        console.print("\n[bold cyan]Project Creation Summary:[/bold cyan]")
        console.print(f"Created {len(created_files)} files")
        if skipped_files:
            console.print(f"Skipped {len(skipped_files)} existing files")
        if failed_files:
            console.print(f"[bold red]Failed to create {len(failed_files)} files[/bold red]")
            for file_path, error in failed_files:
                console.print(f" - {file_path}: {error}")
        
        if install:
            package_managers = {
                "npm": ("package.json", "npm install"),
                "yarn": ("package.json", "yarn"),
                "pip": ("requirements.txt", "pip install -r requirements.txt"),
                "pipenv": ("Pipfile", "pipenv install"),
                "maven": ("pom.xml", "mvn install"),
                "gradle": ("build.gradle", "gradle build"),
                "composer": ("composer.json", "composer install"),
                "nuget": (["*.csproj", "*.fsproj"], "dotnet restore"),
                "pub": ("pubspec.yaml", "flutter pub get")
            }
            
            # Detect available package managers based on files
            available_package_managers = []
            for pm, (file_indicator, install_cmd) in package_managers.items():
                if isinstance(file_indicator, list):
                    if any(len(list(project_dir.glob(pattern))) > 0 for pattern in file_indicator):
                        available_package_managers.append((pm, install_cmd))
                elif (project_dir / file_indicator).exists():
                    available_package_managers.append((pm, install_cmd))
            
            if available_package_managers:
                console.print("\n[bold cyan]Available Package Managers:[/bold cyan]")
                for i, (pm, cmd) in enumerate(available_package_managers):
                    console.print(f"{i+1}. {pm} ({cmd})")
                
                if len(available_package_managers) == 1:
                    pm_choice = 0
                else:
                    pm_choice = typer.prompt(
                        "Choose package manager to install dependencies",
                        type=int,
                        default=1
                    ) - 1
                
                if 0 <= pm_choice < len(available_package_managers):
                    pm, install_cmd = available_package_managers[pm_choice]
                    console.print(f"\n[bold green]Installing dependencies with {pm}...[/bold green]")
                    
                    try:
                        # For npm/yarn, check if we have additional detected dependencies
                        if pm in ["npm", "yarn"] and extracted_dependencies:
                            # Ask if user wants to install detected dependencies
                            if typer.confirm(f"Install {len(extracted_dependencies)} detected dependencies?", default=True):
                                dep_command = f"npm install --save {' '.join(extracted_dependencies)}" if pm == "npm" else f"yarn add {' '.join(extracted_dependencies)}"
                                console.print(f"[bold green]Executing: {dep_command}[/bold green]")
                                
                                process = subprocess.run(
                                    dep_command,
                                    cwd=project_dir,
                                    shell=True,
                                    capture_output=True,
                                    text=True
                                )
                                
                                if process.returncode == 0:
                                    console.print("[green]Dependencies installed successfully[/green]")
                                else:
                                    console.print(f"[bold red]Failed to install dependencies: {process.stderr}[/bold red]")
                        
                        # Run the main install command
                        process = subprocess.run(
                            install_cmd,
                            cwd=project_dir,
                            shell=True,
                            capture_output=True,
                            text=True
                        )
                        
                        if process.returncode == 0:
                            console.print("[green]Dependencies installed successfully[/green]")
                        else:
                            console.print(f"[bold red]Failed to install dependencies: {process.stderr}[/bold red]")
                    except Exception as e:
                        console.print(f"[bold red]Error installing dependencies: {str(e)}[/bold red]")
            else:
                console.print("\n[yellow]No package manager detected for this project type[/yellow]")
        
        if run:
            run_commands = {
                "npm": "npm start",
                "react": "npm start",
                "vue": "npm run dev",
                "angular": "ng serve",
                "next.js": "npm run dev",
                "express": "node app.js",
                "django": "python manage.py runserver",
                "flask": "flask run",
                "spring": "mvn spring-boot:run",
                "laravel": "php artisan serve",
                ".net": "dotnet run",
                "flutter": "flutter run"
            }
            
            # Determine run command based on project type
            run_command = None
            
            # Check if package.json has start script
            package_json_path = project_dir / "package.json"
            if package_json_path.exists():
                try:
                    with open(package_json_path, "r") as f:
                        package_data = json.load(f)
                    
                    if "scripts" in package_data and "start" in package_data["scripts"]:
                        run_command = "npm start"
                    elif "scripts" in package_data and "dev" in package_data["scripts"]:
                        run_command = "npm run dev"
                except Exception:
                    pass
            
            # If no run command found from package.json, try project type
            if not run_command:
                for detected_type in detected_types:
                    if detected_type in run_commands:
                        run_command = run_commands[detected_type]
                        break
            
            # Common file-based detection as fallback
            if not run_command:
                if (project_dir / "manage.py").exists():
                    run_command = "python manage.py runserver"
                elif (project_dir / "app.py").exists():
                    run_command = "flask run"
                elif list(project_dir.glob("*.csproj")):
                    run_command = "dotnet run"
                elif (project_dir / "app.js").exists() or (project_dir / "server.js").exists():
                    run_command = "node app.js" if (project_dir / "app.js").exists() else "node server.js"
            
            if run_command:
                console.print(f"\n[bold cyan]Run Command Detected: {run_command}[/bold cyan]")
                
                if typer.confirm("Run the application?", default=True):
                    console.print(f"\n[bold green]Executing: {run_command}[/bold green]")
                    try:
                        subprocess.run(
                            run_command,
                            cwd=project_dir,
                            shell=True
                        )
                    except KeyboardInterrupt:
                        console.print("\n[yellow]Application stopped by user[/yellow]")
                    except Exception as e:
                        console.print(f"\n[bold red]Error running application: {str(e)}[/bold red]")
            else:
                console.print("\n[yellow]No run command detected for this project type[/yellow]")
        
        # Successful completion message with project path
        console.print(Panel.fit(
            f"Project successfully created at:\n[bold green]{project_dir}[/bold green]",
            title="Success",
            border_style="green"
        ))

if __name__ == "__main__":
    app()
