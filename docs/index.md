# Zor: An Open-Source Claude Code-like Tool

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/github/issues-pr/admincodes7/zor)](CONTRIBUTING.md)
[![Build Status](https://github.com/admincodes7/zor/actions/workflows/python-package.yml/badge.svg)](https://github.com/admincodes7/zor/actions)
[![PyPI Downloads](https://img.shields.io/pepy/dt/zor?cacheSeconds=3600)](https://pypi.org/project/zor)
[![Stable Version](https://img.shields.io/pypi/v/zor?color=blue)](https://pypi.org/project/zor/)


<div align="center">
  <img src="https://raw.githubusercontent.com/admincodes7/zor/refs/heads/master/assets/card.jpg" alt="Zor Logo" width="150" height="75"/>
  <p><i>Powerful AI assistance for your codebase</i></p>
</div>

## What is Zor?

Zor is an open-source command-line tool that brings AI-powered code assistance directly to your terminal. Inspired by tools like Claude Code, Zor helps developers understand, modify, and improve their codebases through natural language interactions.

### Key Features

- **Contextual Code Understanding**: Zor analyzes your entire codebase to provide relevant answers and suggestions
- **Interactive Mode**: Have ongoing conversations about your code
- **File Editing**: Edit files using natural language instructions
- **Test Generation**: Automatically create unit tests for your code
- **Refactoring**: Implement complex refactoring across multiple files
- **Git Integration**: Commit changes directly through Zor

## Quick Demo

[![Demo Video](https://raw.githubusercontent.com/admincodes7/zor/refs/heads/master/assets/coverpage.png)](https://youtu.be/mS0ONPNhMmU?si=efayT3KuuiqZtksH)

## Tech Stack

- **Python**: Core language (3.9+)
- **Gemini API**: Powers AI code understanding and generation
- **Typer**: Command-line interface framework
- **Rich**: Beautiful terminal output formatting
- **Google GenerativeAI**: Client library for Gemini models

## Getting Started

### Installation

```bash
pip install zor
```

Or install from source:

```bash
git clone https://github.com/admincodes7/zor.git
cd zor
pip install -e .
```

### Setup Guide

1. **Get a Gemini API Key**:
   - Visit [Google AI Studio](https://ai.google.dev/)
   - Create an account and generate an API key

2. **Configure Zor**:
   ```bash
   zor setup
   ```
   - Enter your Gemini API key when prompted

3. **Verify Installation**:
   ```bash
   zor help
   ```

## Available Commands

| Command | Description |
|---------|-------------|
| `zor ask` | Ask about your codebase |
| `zor init` | Create a new project with Zor |
| `zor edit` | Edit a file with natural language |
| `zor commit` | Create a git commit |
| `zor interactive` | Start an interactive session |
| `zor history` | View conversation history |
| `zor generate_test` | Generate tests for a file |
| `zor refactor` | Refactor code across multiple files |
| `zor config` | View or update configuration |
| `zor setup` | Configure your Gemini API key |
| `zor help` | Show available commands |

## Detailed Usage

### Asking About Your Code

```bash
zor ask "How does the rate limiting work in this codebase?"
```

### Editing Files

```bash
zor edit path/to/file.py "Add error handling for network failures"
```

### Interactive Mode

```bash
zor interactive
```
### Create or Initialize new project

```bash
zor init "create a modern React portfolio app for a software engineer with dark theme"
```

### To know more about a command

```bash
zor <command> --help
```

## Contributing

We welcome contributions of all kinds! See our [Contributing Guide](CONTRIBUTING.md) for more details.

## License

Zor is licensed under the [MIT License](LICENSE).

## Contact & Support

- **GitHub Issues**: For bug reports and feature requests
- **Email**: arjunbanur27@gmail.com
