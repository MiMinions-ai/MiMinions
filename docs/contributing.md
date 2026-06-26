# Contributing

Thank you for contributing to MiMinions! Below is a quick-reference guide — see [CONTRIBUTING.md](https://github.com/MiMinions-ai/MiMinions/blob/main/CONTRIBUTING.md) in the repo for full details.

## Getting Started

1. Fork and clone the repository
2. Install dev dependencies: `pip install -e ".[dev]"`
3. Create a branch: `git checkout -b feature/your-feature-name`

## Branch Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Stable production releases |
| `development` | Integration branch for active work |
| `feature/*` | New features (branch from `development`) |
| `hotfix/*` | Urgent fixes (branch from `main`) |

## Submitting a Pull Request

- Target `development` (not `main`) for all feature work
- Include tests for new functionality
- Update documentation if applicable
- Fill in the PR template

## Coding Standards

- Follow PEP 8
- Use type annotations
- Keep functions short and focused
- Validate external input at boundaries; never silently swallow errors

## Testing

```bash
pytest tests/unit/        # unit tests
pytest tests/integration/ # integration tests
pytest tests/e2e/         # end-to-end tests
pytest tests/             # run everything
```

## Code of Conduct

All contributors must follow the [Code of Conduct](https://github.com/MiMinions-ai/MiMinions/blob/main/CODE_OF_CONDUCT.md).
