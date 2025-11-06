# Zor User Guide

This guide provides detailed instructions for using Zor effectively in your development workflow.

## Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [Basic Usage](#basic-usage)
- [Advanced Features](#advanced-features)
- [Customization](#customization)
- [Troubleshooting](#troubleshooting)

## Installation

### Prerequisites

- Python 3.9 or higher
- A Gemini API key from [Google AI Studio](https://ai.google.dev/)

### Install from PyPI

```bash
pip install zor
```

### Install from Source

```bash
git clone https://github.com/admincodes7/zor.git
cd zor
pip install -e .
```

## Configuration

### Initial Setup

```bash
zor setup
```

Enter your Gemini API key when prompted. This will:
1. Validate your API key
2. Save it in your global configuration
3. Add it to your local `.env` file

### Configuration Options

You can view and modify configuration settings using:

```bash
zor config
```

Key configuration options:

- `model`: The Gemini model to use (default: gemini-2.0-flash)
- `temperature`: Response creativity (0.0-1.0, lower is more focused)
- `max_tokens`: Maximum output length
- `exclude_dirs`: Directories to ignore when scanning codebase
- `exclude_files`: File patterns to ignore
- `backup_files`: Whether to create backups before editing files

Example configuration update:
```bash
zor config temperature 0.7
```

## Basic Usage

### Asking Questions

```bash
zor ask "Explain how the context scanning works in this project"
```

Zor will analyze your codebase and provide a contextually aware answer.

### Interactive Mode

```bash
zor interactive
```

This mode allows ongoing conversation with Zor about your codebase. Type `exit` to quit.

### Editing Files

```bash
zor edit path/to/file.py "Add parameter validation to the main function"
```

Zor will:
1. Show a diff preview of changes
2. Ask for confirmation
3. Apply the changes (creating a backup if configured)


### Creating New Project with Zor

```bash
zor init "create a modern React portfolio app for a software engineer with dark theme"
```
Zor will:
1. Create entire project structures with just a description
2. Analyzes your requirements and determines the appropriate project type, technologies, and architecture
3. Creates all necessary files with functional code and appropriate documentation
4. Extracts relevant project names from your description (or lets you specify one)
5. Warns before overwriting existing directories

## Advanced Features

### Generating Tests

```bash
zor generate_test zor/api.py
```

Zor will analyze the file and create appropriate unit tests. You can specify the testing framework:

```bash
zor generate_test zor/api.py --test-framework unittest
```

### Code Refactoring

```bash
zor refactor "Convert all print statements to logging calls"
```

This powerful command will:
1. Identify files that need changes
2. Show a summary of planned modifications
3. Display detailed diffs for each file
4. Apply changes after confirmation
5. Optionally create a git commit

### Git Integration

After making changes, commit directly:

```bash
zor commit "Improve error handling in API module"
```

## Customization

### Project-Specific Configuration

Create a `.zor_config.json` file in your project root to override global settings:

```json
{
  "model": "gemini-2.0-pro",
  "temperature": 0.4,
  "exclude_dirs": ["node_modules", ".venv", "venv", ".git", "dist", "build"],
  "exclude_files": [".env", "*.pyc", "*.jpg", "*.png", "*.pdf"]
}
```

### Context Filtering

Customize which files are included in the context by modifying the `exclude_dirs` and `exclude_files` settings.

## Troubleshooting

### API Key Issues

If you receive authentication errors:
1. Check that your API key is valid
2. Run `zor setup` to reconfigure your key
3. Verify the key is properly saved in your `.env` file

### Rate Limiting

If you encounter rate limit errors:
1. Wait a few moments before trying again
2. Consider using a different Gemini model
3. Adjust the `rate_limit_retries` configuration 

### Command Failures

For unexpected errors:
1. Check your Python version (requires 3.9+)
2. Verify all dependencies are installed
3. Check for conflicting global configurations

For persistent issues, please open an issue on GitHub.

## Tips and Best Practices

1. **Be specific** in your prompts for better results
2. **Use interactive mode** for complex tasks that require multiple steps
3. **Review all changes** before applying them
4. **Create backups** of important files when making significant changes
5. **Start small** when using refactoring features
