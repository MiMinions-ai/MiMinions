# Contributing to MiMinions

Thank you for your interest in contributing to MiMinions! We welcome contributions from the community and are grateful for your help in making this project better.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Environment](#development-environment)
- [How to Contribute](#how-to-contribute)
- [Submitting Issues](#submitting-issues)
- [Submitting Pull Requests](#submitting-pull-requests)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Community and Support](#community-and-support)

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please read it before contributing.

## Getting Started

Fork the repository on GitHub and clone your fork locally. Set up the development environment using the instructions below. Create a branch for your changes using `git checkout -b feature/your-feature-name`. Make sure to follow our coding standards and testing guidelines.

## Development Environment

### Prerequisites

You need Python 3.8 or higher, pip, and Git installed on your system.

### Setup

Install development dependencies with `pip install -e ".[dev]"` and optional dependencies with `pip install -e ".[full]"`. Verify the installation by running `python -c "import miminions; print('MiMinions installed successfully')"`. For database testing, install PostgreSQL with pgvector extension and set up a test database with the appropriate environment variables.

## How to Contribute

### Types of Contributions

We welcome bug fixes, new features, documentation improvements, tests, performance optimizations, and usage examples. Check existing issues first to see if your idea is already being worked on. For large features, open an issue to discuss your proposed changes before starting work.

### Contribution Process

Fork the repository and create a branch for your work. Make your changes following our guidelines and test them thoroughly. Submit a pull request with a clear description of your changes. Ensure your code follows our coding standards and includes appropriate tests.

## Submitting Issues

Before submitting an issue, search existing issues to avoid duplicates. Use our issue templates for bug reports, feature requests, or questions. Provide detailed information including Python version, operating system, MiMinions version, and steps to reproduce for bugs. Include clear descriptions of expected vs actual behavior.

### Bug Reports

Use the bug report template with a clear, descriptive title. Include steps to reproduce the issue, expected behavior, actual behavior, error messages or stack traces, and system information.

### Feature Requests

Use the feature request template with a clear description of the feature, use case and motivation, proposed implementation if you have ideas, and alternative solutions considered.

## Submitting Pull Requests

### Before You Submit

Ensure your code follows our coding standards and run the test suite to make sure all tests pass. Add tests for new functionality and update documentation as needed. Check that your changes don't break existing functionality.

### Pull Request Guidelines

Use our PR template and fill out all relevant sections. Keep changes focused with one feature or fix per PR. Write clear commit messages following conventional commit format and include tests for new functionality. Update documentation for user-facing changes and link related issues in the PR description.

### Commit Message Format

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification. Use types like `feat` for new features, `fix` for bug fixes, `docs` for documentation changes, `style` for code style changes, `refactor` for code refactoring, `test` for adding or updating tests, and `chore` for maintenance tasks.

## Coding Standards

### Python Style

We follow [PEP 8](https://pep8.org/) with a line length of 88 characters (Black formatter default). Use `isort` for consistent import ordering and type hints for public APIs. Use Google-style docstrings for documentation.

### Code Quality Tools

We use Black for code formatting, isort for import sorting, flake8 for linting, mypy for type checking, and pytest for testing. Run these tools before submitting: `black src/ tests/`, `isort src/ tests/`, `flake8 src/ tests/`, `mypy src/`, and `pytest tests/`.

### Best Practices

Write clear, readable code with meaningful variable names and add docstrings to all public functions and classes. Use type hints for function parameters and return values. Handle exceptions appropriately and write defensive code with proper validation. Follow the existing code patterns in the project.

## Testing Guidelines

### Test Structure

Tests are located in the `tests/` directory and should mirror the source structure in organization. Use descriptive test names that explain what is being tested.

### Writing Tests

Write unit tests for individual functions and classes, integration tests for component interactions, and end-to-end tests for complete workflows. All new features must include tests, and bug fixes should include regression tests. Tests should be isolated and not depend on external services, using mocking for external dependencies. Aim for high test coverage (target: 80%+).

### Running Tests

Run all tests with `pytest tests/`, specific test files with `pytest tests/test_agents.py`, tests with coverage using `pytest --cov=miminions tests/`, and tests in parallel with `pytest -n auto tests/`.

## Documentation

### Types of Documentation

Include code documentation with docstrings and inline comments, API documentation generated from docstrings, user guides in README and tutorials, and working code examples.

### Documentation Standards

Use clear, concise language and include code examples where helpful. Keep documentation up-to-date with code changes and use proper Markdown formatting.

### Building Documentation

Generate API documentation if applicable using `sphinx-build -b html docs/ docs/_build/html/`.

## Community and Support

### Getting Help

Use GitHub Discussions for questions and community discussion, Issues for bug reports and feature requests, and check documentation first. Be respectful and inclusive in communications, patient with responses, and provide context when asking questions.

### Recognition

We recognize contributors through the contributors list in README, release notes mentioning significant contributions, and the GitHub contributor graph.

## Release Process

### Versioning

We follow [Semantic Versioning](https://semver.org/) with major releases for breaking changes, minor releases for new features that are backwards compatible, and patch releases for bug fixes that are backwards compatible.

### Release Cycle

Patch releases are made as needed for critical bugs, minor releases monthly or bi-monthly, and major releases when breaking changes are needed.

## License

By contributing to MiMinions, you agree that your contributions will be licensed under the same license as the project (MIT License).

## Questions?

If you have questions about contributing, check this document and the README first, search existing issues and discussions, open a new discussion or issue, or reach out to the maintainers.

Thank you for contributing to MiMinions! 🎉