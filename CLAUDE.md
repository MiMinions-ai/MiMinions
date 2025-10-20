# MiMinions Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-19

## Active Technologies
- Python 3.12+ + UV package manager, pyproject.toml (PEP 621), setuptools build backend (003-uv-package-manager)
- Python 3.12+ (per project standards) (004-multi-agent-runtime)
- SQLite for local persistence (agent state, task queue, event logs) - aligns with local-first architecture (004-multi-agent-runtime)

## Project Structure
```
src/
tests/
```

## Commands
cd src; pytest; ruff check .

## Code Style
Python 3.12+: Follow standard conventions

## Recent Changes
- 004-multi-agent-runtime: Added Python 3.12+ (per project standards)
- 003-uv-package-manager: Added Python 3.12+ + UV package manager, pyproject.toml (PEP 621), setuptools build backend

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
