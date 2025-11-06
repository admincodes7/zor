# Zor

<div align="center">
  <img src="https://raw.githubusercontent.com/admincodes7/zor/refs/heads/master/assets/card.jpg" alt="Zor Logo" width="150" height="75" />
  <p><i>An Open-Source Claude Code-like Tool</i></p>
  
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
  [![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
  [![PRs Welcome](https://img.shields.io/github/issues-pr/admincodes7/zor)](CONTRIBUTING.md)
  [![Build Status](https://github.com/admincodes7/zor/actions/workflows/python-package.yml/badge.svg)](https://github.com/admincodes7/zor/actions)
  [![PyPI Downloads](https://img.shields.io/pepy/dt/zor?cacheSeconds=3600)](https://pypi.org/project/zor)
  [![Stable Version](https://img.shields.io/pypi/v/zor?color=blue)](https://pypi.org/project/zor/)
</div>

## Overview

Zor is a powerful command-line tool that brings AI-powered code assistance to your terminal. Using the Gemini API, Zor helps you understand, modify, and improve your codebase through natural language.

Think of it as an open-source alternative to tools like Claude Code - your AI pair programmer in the terminal.

## Features

- 🧠 **Contextual Understanding**: Zor analyzes your entire codebase for informed assistance
- 💬 **Interactive Mode**: Have conversations about your code
- ✏️ **Edit Files**: Make changes using natural language instructions
- 🧪 **Generate Tests**: Automatically create tests for your code
- 🔄 **Refactor Code**: Implement complex changes across multiple files
- 🔧 **Git Integration**: Commit changes directly from Zor
- 🧠 **Project Creation**: Create a new projects with description provided


## Quick Demo
[![Demo Video](https://raw.githubusercontent.com/admincodes7/zor/refs/heads/master/assets/coverpage.png)](https://youtu.be/mS0ONPNhMmU?si=efayT3KuuiqZtksH)

## Installation

```bash
pip install zor
```

## Quick Start

1. **Configure your API key**:
   ```bash
   zor setup
   ```

2. **Ask about your code**:
   ```bash
   zor ask "How does the file reading in context.py work?"
   ```

3. **Start an interactive session**:
   ```bash
   zor interactive
   ```
4. **Create new Project with Zor**:
   ```bash
   zor init "create a modern React portfolio app for a software engineer with dark theme"
   ```

## Documentation

For complete documentation, visit our [Documentation](docs/index.md).

## Example Usage

### Generate Tests

```bash
zor generate_test zor/context.py
```

### Edit a File

```bash
zor edit zor/main.py "Add better error handling to the setup command"
```

### Refactor Code

```bash
zor refactor "Improve error handling across the codebase by using custom exceptions"
```

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

Zor is licensed under the [MIT License](LICENSE).

## Acknowledgements

- Thanks to all contributors who have helped shape this project
- Inspired by tools like Claude Code and GitHub Copilot
