# Quick Start: UV Package Management

**Feature**: Modern Python Package Management with UV
**Last Updated**: 2025-10-19
**Target Audience**: MiMinions contributors and developers

## TL;DR

```bash
# Install UV (one-time)
curl -LsSf https://astral.sh/uv/install.sh | sh    # macOS/Linux
# or
irm https://astral.sh/uv/install.ps1 | iex         # Windows

# Set up development environment
git clone https://github.com/org/miminions.git
cd miminions
uv sync                # Install all dependencies

# Start developing
uv run pytest          # Run tests
uv add <package>       # Add a dependency
uv run python script.py # Run any Python script
```

Done! Your development environment is ready in under 2 minutes.

## Prerequisites

- **Python 3.12+**: UV will use your system Python or can install it for you
- **Git**: For cloning the repository
- **Internet**: For initial package downloads (offline mode available after first sync)

## Installation

### Option 1: UV Installer (Recommended)

**macOS/Linux**:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows PowerShell**:
```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

**Verify installation**:
```bash
uv --version
# Expected: uv 0.5.0 or later
```

### Option 2: Package Managers

**Homebrew** (macOS/Linux):
```bash
brew install uv
```

**Cargo** (any platform with Rust):
```bash
cargo install uv
```

**pipx** (Python-based):
```bash
pipx install uv
```

## First-Time Setup

### 1. Clone the Repository

```bash
git clone https://github.com/org/miminions.git
cd miminions
```

### 2. Install Dependencies

```bash
uv sync
```

This command will:
- Create a virtual environment at `.venv/`
- Install all dependencies from `uv.lock`
- Verify package integrity with checksums
- Typically completes in 30-60 seconds

**What happened?**
- Virtual environment: `.venv/` (gitignored)
- Lock file: `uv.lock` (committed to git)
- Package cache: `~/.cache/uv/` (shared across projects)

### 3. Verify Setup

```bash
# Activate virtual environment (optional - uv run handles this)
source .venv/bin/activate    # macOS/Linux
.venv\Scripts\activate.ps1   # Windows PowerShell

# Run tests to confirm everything works
uv run pytest

# Try the CLI
uv run miminions --help
```

✅ **Success!** You're ready to contribute.

## Common Tasks

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=miminions

# Run specific test file
uv run pytest tests/test_simple_agent.py

# Run with verbose output
uv run pytest -v
```

### Running Python Scripts

```bash
# Run any Python script in the venv
uv run python examples/ai_studio.py

# Run CLI commands
uv run miminions agent create --help
```

### Adding Dependencies

**Production dependency**:
```bash
uv add requests
```

**Development dependency**:
```bash
uv add --dev black
```

**Specific version**:
```bash
uv add "requests>=2.31.0,<3.0.0"
```

**What happens?**
1. `pyproject.toml` updated with new dependency
2. `uv.lock` regenerated with resolved versions
3. Package installed in current venv

**Don't forget to commit**:
```bash
git add pyproject.toml uv.lock
git commit -m "feat: add requests dependency"
```

### Removing Dependencies

```bash
# Remove production dependency
uv remove requests

# Remove dev dependency
uv remove --dev black
```

### Updating Dependencies

**Update specific package** (e.g., security fix):
```bash
uv lock --upgrade-package pytest
uv sync
```

**Update all packages**:
```bash
uv lock --upgrade
uv sync
```

**Check for outdated packages** (coming soon):
```bash
uv pip list --outdated
```

### Listing Installed Packages

```bash
# Formatted list
uv pip list

# requirements.txt format
uv pip freeze

# Show dependency tree (coming soon)
uv tree
```

## Working Offline

After the first `uv sync`, UV caches all packages locally. You can work completely offline:

```bash
# Delete venv and recreate offline
rm -rf .venv
uv sync --offline  # Uses cache, no network required
```

UV cache location:
- **macOS/Linux**: `~/.cache/uv/`
- **Windows**: `%LOCALAPPDATA%\uv\cache`

## Troubleshooting

### "uv: command not found"

**Solution**: UV not in PATH. Restart your shell or manually add:

```bash
# Add to ~/.bashrc, ~/.zshrc, or equivalent
export PATH="$HOME/.local/bin:$PATH"
```

### "Lock file is out of sync"

**Problem**: `pyproject.toml` changed but `uv.lock` wasn't updated

**Solution**:
```bash
uv lock     # Regenerate lock file
uv sync     # Install updated dependencies
```

### "Package not found in cache (offline mode)"

**Problem**: Working offline but package not cached

**Solution**:
```bash
# Go online and sync to populate cache
uv sync

# Now offline mode will work
```

### "Checksum mismatch"

**Problem**: Downloaded package doesn't match expected hash (corrupted/tampered)

**Solution**:
```bash
uv cache clean  # Clear corrupted cache
uv sync         # Re-download with verification
```

### "Cannot resolve dependencies"

**Problem**: Conflicting version requirements

**Solution**:
```bash
# Check which packages conflict
uv lock --verbose

# May need to relax version constraints in pyproject.toml
# Or remove conflicting package
```

### Tests fail with "Module not found"

**Problem**: Venv missing a dependency

**Solution**:
```bash
uv sync  # Reinstall all dependencies from lock file
```

## Best Practices

### ✅ DO

- Commit `uv.lock` to version control
- Run `uv sync` after pulling changes
- Use `uv run` for running scripts (auto-activates venv)
- Add dependencies with `uv add` (updates both files)
- Update lock file regularly for security patches

### ❌ DON'T

- Don't manually edit `uv.lock` (regenerated automatically)
- Don't commit `.venv/` (gitignored)
- Don't use `pip install` (use `uv add` instead)
- Don't forget to commit `uv.lock` after adding dependencies

## Migrating from pip

If you previously used pip:

```bash
# Remove old venv
rm -rf .venv

# Create new with UV
uv sync

# Run tests to verify parity
uv run pytest
```

All your dependencies from `pyproject.toml` are installed automatically. No manual migration needed!

## CI/CD Integration

For continuous integration, use `--frozen` to enforce lock file:

```yaml
# .github/workflows/test.yml
- name: Install UV
  uses: astral-sh/setup-uv@v1

- name: Install dependencies
  run: uv sync --frozen  # Fails if lock file out of sync

- name: Run tests
  run: uv run pytest
```

## Comparison: pip vs UV

| Task | pip | UV |
|------|-----|-----|
| Install dependencies | `pip install -e .` (2-5 min) | `uv sync` (30-60s) |
| Add dependency | Edit pyproject.toml + `pip install` | `uv add <pkg>` |
| Lock dependencies | `pip freeze > requirements.txt` | `uv lock` (automatic) |
| Reproducible install | `pip install -r requirements.txt` | `uv sync --frozen` |
| Offline support | Manual cache management | Automatic cache |
| Checksum verification | Manual with --require-hashes | Automatic |

**Speed**: UV is 10-100x faster due to:
- Parallel downloads
- Efficient resolver (written in Rust)
- Smart caching

## Advanced Usage

### Use different Python version

```bash
# UV can install Python versions
uv python install 3.13
uv python pin 3.13  # Set for this project

# Or use specific Python
uv venv --python python3.13
```

### Custom cache location

```bash
export UV_CACHE_DIR=/custom/cache/path
uv sync
```

### Prune unused cache

```bash
# Remove packages not used by any project
uv cache prune

# Show cache size and location
uv cache dir
```

### Export to requirements.txt

```bash
# For tools that don't support uv.lock yet
uv pip freeze > requirements.txt
```

## Getting Help

### Command-line help

```bash
uv --help              # General help
uv sync --help         # Command-specific help
uv add --help          # Add dependency help
```

### Documentation

- UV Docs: https://github.com/astral-sh/uv
- MiMinions Contributing: [CONTRIBUTING.md](../../CONTRIBUTING.md)
- Issue Tracker: https://github.com/org/miminions/issues

### Common Questions

**Q: Can I still use pip?**
A: Yes during transition, but UV is recommended for faster, reproducible builds.

**Q: Does UV replace virtualenv/venv?**
A: Yes, UV has built-in virtual environment management (`uv venv`).

**Q: What if a package isn't on PyPI?**
A: UV supports git dependencies and custom indexes:
```bash
uv add git+https://github.com/user/repo.git
```

**Q: How do I share my cache across machines?**
A: Cache is local only for security. Each machine has its own cache.

**Q: Does UV support requirements.txt?**
A: Yes, `uv pip install -r requirements.txt` works, but `uv.lock` is preferred.

## Next Steps

- Read the full [Migration Contract](contracts/migration-contract.md) for validation criteria
- Review [Command Interface](contracts/command-interface.md) for all available commands
- Check [Data Model](data-model.md) to understand lock file structure
- Join the GitHub Discussion for UV migration feedback

---

**Welcome to faster, more reliable Python package management!** 🚀

If you encounter issues, please create an issue on GitHub or ask in Discussions.
