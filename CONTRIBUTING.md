# Contributing to Zor

Thank you for your interest in contributing to Zor! This document provides guidelines and instructions for contributing to this project.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

## How Can I Contribute?

### Reporting Bugs

Before submitting a bug report:
- Check if the issue has already been reported
- Verify it's not an issue with your local configuration

When submitting a bug report, please include:
- A clear and descriptive title
- Exact steps to reproduce the issue
- Expected vs. actual behavior
- Your environment details (OS, Python version, etc.)
- Any relevant error messages or logs

### Suggesting Features

When suggesting a feature:
- Provide a clear description of the feature
- Explain how it would benefit users
- Suggest implementation ideas if possible

### Pull Requests

1. Fork the repository
2. Create a new branch from `main`
3. Make your changes
4. Add or update tests as needed
5. Run the test suite to ensure all tests pass
6. Update documentation if necessary
7. Submit your pull request

#### Pull Request Guidelines

- Keep changes focused on a single issue/feature
- Follow the existing code style
- Add unit tests for new functionality
- Update documentation for any changed features
- Validate that all tests pass before submitting

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/admincodes7/zor.git
   cd zor
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

4. Run tests:
   ```bash
   pytest
   ```

## Project Structure

```
zor/
├── docs/            # Documentation files
├── tests/           # Test files 
├── zor/             # Main source code
│   ├── __init__.py
│   ├── api.py       # API interaction
│   ├── config.py    # Configuration management
│   ├── context.py   # Code context handling
│   ├── file_ops.py  # File operations
│   ├── git_utils.py # Git integration
│   ├── history.py   # Conversation history
│   ├── main.py      # CLI entrypoint
│   └── safety.py    # Safety confirmations
├── .env             # Local environment variables (not committed)
├── LICENSE          # MIT License
├── README.md        # Project overview
└── pyproject.toml   # Project metadata and dependencies
```

## Testing

All new features and bug fixes should include tests. We use `pytest` for testing.

To run the test suite:

```bash
pytest
```

## Documentation

- Update documentation for any feature changes
- Follow the existing documentation style
- Test any code examples you provide

## Versioning

We follow [Semantic Versioning](https://semver.org/). In short:
- MAJOR version for incompatible API changes
- MINOR version for backwards-compatible functionality
- PATCH version for backwards-compatible bug fixes

## Release Process

1. Update version number in `pyproject.toml`
2. Update CHANGELOG.md with all notable changes
3. Create a new release on GitHub
4. Publish to PyPI

## Questions?

If you have any questions about contributing, please open an issue in the repository.

Thank you for contributing to Zor!
