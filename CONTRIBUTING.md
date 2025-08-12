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

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/MiMinions.git
   cd MiMinions
   ```
3. **Set up the development environment** (see below)
4. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Environment

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Git

### Setup

1. **Install development dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

2. **Install optional dependencies** for full functionality:
   ```bash
   pip install -e ".[full]"
   ```

3. **Verify the installation**:
   ```bash
   python -c "import miminions; print('MiMinions installed successfully')"
   ```

### Database Setup (Optional)

For testing database features:

1. **Install PostgreSQL** with pgvector extension
2. **Set up a test database**:
   ```bash
   createdb miminions_test
   ```
3. **Set environment variables**:
   ```bash
   export MIMINIONS_TEST_DB="postgresql://user:password@localhost/miminions_test"
   ```

## How to Contribute

### Types of Contributions

We welcome various types of contributions:

- **Bug fixes**: Fix issues and improve stability
- **New features**: Add new functionality to the framework
- **Documentation**: Improve or add documentation
- **Tests**: Add or improve test coverage
- **Performance**: Optimize code performance
- **Examples**: Add usage examples and tutorials

### Contribution Process

1. **Check existing issues** to see if your idea is already being worked on
2. **Open an issue** to discuss your proposed changes (for large features)
3. **Fork and create a branch** for your work
4. **Make your changes** following our guidelines
5. **Test your changes** thoroughly
6. **Submit a pull request** with a clear description

## Submitting Issues

Before submitting an issue:

1. **Search existing issues** to avoid duplicates
2. **Use our issue templates** for bug reports, feature requests, or questions
3. **Provide detailed information** including:
   - Python version
   - Operating system
   - MiMinions version
   - Steps to reproduce (for bugs)
   - Clear description of expected vs actual behavior

### Bug Reports

Use the bug report template and include:

- Clear, descriptive title
- Steps to reproduce the issue
- Expected behavior
- Actual behavior
- Error messages or stack traces
- System information

### Feature Requests

Use the feature request template and include:

- Clear description of the feature
- Use case and motivation
- Proposed implementation (if you have ideas)
- Alternative solutions considered

## Submitting Pull Requests

### Before You Submit

1. **Ensure your code follows our coding standards**
2. **Run the test suite** and ensure all tests pass
3. **Add tests** for new functionality
4. **Update documentation** as needed
5. **Check that your changes don't break existing functionality**

### Pull Request Guidelines

1. **Use our PR template** and fill out all relevant sections
2. **Keep changes focused** - one feature or fix per PR
3. **Write clear commit messages** following conventional commit format
4. **Include tests** for new functionality
5. **Update documentation** for user-facing changes
6. **Link related issues** in the PR description

### Commit Message Format

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(agents): add support for custom tool validation
fix(database): resolve connection timeout issue
docs(readme): update installation instructions
```

## Coding Standards

### Python Style

We follow [PEP 8](https://pep8.org/) with some modifications:

- **Line length**: 88 characters (Black formatter default)
- **Import organization**: Use `isort` for consistent import ordering
- **Type hints**: Use type hints for public APIs
- **Docstrings**: Use Google-style docstrings

### Code Quality Tools

We use several tools to maintain code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking
- **pytest**: Testing

Run these tools before submitting:

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type check
mypy src/

# Run tests
pytest tests/
```

### Best Practices

- **Write clear, readable code** with meaningful variable names
- **Add docstrings** to all public functions and classes
- **Use type hints** for function parameters and return values
- **Handle exceptions** appropriately
- **Write defensive code** with proper validation
- **Follow the existing code patterns** in the project

## Testing Guidelines

### Test Structure

- Tests are located in the `tests/` directory
- Mirror the source structure in test organization
- Use descriptive test names that explain what is being tested

### Writing Tests

1. **Unit tests**: Test individual functions and classes
2. **Integration tests**: Test component interactions
3. **End-to-end tests**: Test complete workflows

### Test Requirements

- **All new features** must include tests
- **Bug fixes** should include regression tests
- **Tests should be isolated** and not depend on external services
- **Use mocking** for external dependencies
- **Aim for high test coverage** (target: 80%+)

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_agents.py

# Run with coverage
pytest --cov=miminions tests/

# Run tests in parallel
pytest -n auto tests/
```

## Documentation

### Types of Documentation

1. **Code documentation**: Docstrings and inline comments
2. **API documentation**: Generated from docstrings
3. **User guides**: README and tutorials
4. **Examples**: Working code examples

### Documentation Standards

- **Use clear, concise language**
- **Include code examples** where helpful
- **Keep documentation up-to-date** with code changes
- **Use proper Markdown formatting**

### Building Documentation

```bash
# Generate API documentation (if applicable)
sphinx-build -b html docs/ docs/_build/html/
```

## Community and Support

### Getting Help

- **GitHub Discussions**: For questions and community discussion
- **Issues**: For bug reports and feature requests
- **Documentation**: Check README and docstrings first

### Communication Guidelines

- **Be respectful** and inclusive
- **Be patient** with responses
- **Provide context** when asking questions
- **Help others** when you can

### Recognition

We recognize contributors in several ways:

- **Contributors list** in README
- **Release notes** mentioning significant contributions
- **GitHub contributor graph**

## Release Process

### Versioning

We follow [Semantic Versioning](https://semver.org/):

- **Major** (X.0.0): Breaking changes
- **Minor** (x.Y.0): New features, backwards compatible
- **Patch** (x.y.Z): Bug fixes, backwards compatible

### Release Cycle

- **Patch releases**: As needed for critical bugs
- **Minor releases**: Monthly or bi-monthly
- **Major releases**: When breaking changes are needed

## License

By contributing to MiMinions, you agree that your contributions will be licensed under the same license as the project (MIT License).

## Questions?

If you have questions about contributing, please:

1. Check this document and the README
2. Search existing issues and discussions
3. Open a new discussion or issue
4. Reach out to the maintainers

Thank you for contributing to MiMinions! 🎉