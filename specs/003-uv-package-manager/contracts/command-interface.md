# Command Interface Contract: UV Package Manager

**Feature**: Modern Python Package Management
**Date**: 2025-10-19
**Type**: Command Interface Specification

## Purpose

This contract defines the UV command interface that developers will use for package management tasks. All commands must behave consistently across platforms (Windows, macOS, Linux) and provide clear, actionable output.

## Core Commands

### C-001: Environment Setup

**Command**: `uv venv [path]`

**Purpose**: Create a new virtual environment

**Usage**:
```bash
uv venv              # Create .venv in current directory
uv venv /path/to/env # Create at specific path
```

**Expected Behavior**:
- Creates virtual environment directory
- Uses Python >=3.12 (from `requires-python` in pyproject.toml)
- Directory structure matches platform (bin/ on Unix, Scripts/ on Windows)
- pyvenv.cfg created with correct metadata

**Success Output**:
```
Using Python 3.12.0
Creating virtual environment at .venv
```

**Error Cases**:
- Python version not found → "Error: Python 3.12+ not found"
- Permission denied → "Error: Cannot create directory .venv: Permission denied"
- Already exists → Overwrites by default (add --clear flag for explicit)

### C-002: Dependency Installation

**Command**: `uv sync [options]`

**Purpose**: Install dependencies from lock file

**Options**:
- `--frozen`: Enforce exact lock file versions, fail if out of sync
- `--offline`: Use cache only, fail if network needed
- `--no-dev`: Skip development dependencies
- `--only-dev`: Install only development dependencies

**Usage**:
```bash
uv sync                # Install all dependencies (production + dev)
uv sync --frozen       # Install exact versions, fail if lock outdated
uv sync --offline      # Install from cache only
uv sync --no-dev       # Install production dependencies only
```

**Expected Behavior**:
- Reads uv.lock and pyproject.toml
- Creates .venv if missing
- Installs exact versions from lock file
- Verifies checksums during installation
- Uses cache when available

**Success Output**:
```
Resolved 42 packages in 123ms
Downloaded 5 packages in 456ms
Installed 42 packages in 789ms
```

**Error Cases**:
- Missing lock file → "Error: uv.lock not found. Run 'uv lock' first"
- Lock file outdated (--frozen) → "Error: uv.lock is out of sync. Run 'uv lock' to update"
- Network required (--offline) → "Error: Package not in cache and --offline specified"
- Checksum mismatch → "Error: Checksum mismatch for package X (corrupted download)"

### C-003: Lock File Generation

**Command**: `uv lock [options]`

**Purpose**: Generate or update lock file from pyproject.toml

**Options**:
- `--upgrade`: Upgrade all packages to latest compatible versions
- `--upgrade-package <pkg>`: Upgrade specific package only
- `--check`: Check if lock file is up-to-date (exit 0/1)
- `--dry-run`: Show what would change without modifying lock file

**Usage**:
```bash
uv lock                             # Generate/update lock file
uv lock --upgrade                   # Upgrade all packages
uv lock --upgrade-package pytest    # Upgrade pytest only
uv lock --check                     # Validate lock is current
```

**Expected Behavior**:
- Resolves all dependencies from pyproject.toml
- Generates uv.lock with exact versions and hashes
- Minimizes changes to existing lock file (stability)
- Reports conflicts if dependency resolution fails

**Success Output**:
```
Resolved 42 packages in 1.2s
Updated uv.lock
```

**Error Cases**:
- Dependency conflict → "Error: Cannot resolve dependencies: package X requires Y<2.0, but Z requires Y>=2.0"
- Invalid pyproject.toml → "Error: Invalid pyproject.toml: missing [project] section"
- Package not found → "Error: Package 'invalid-package' not found on PyPI"

### C-004: Add Dependency

**Command**: `uv add <package> [options]`

**Purpose**: Add a new dependency to project

**Options**:
- `--dev`: Add as development dependency
- `--optional <group>`: Add to optional dependency group
- `<package>==<version>`: Specify exact version
- `<package>>=<version>`: Specify minimum version

**Usage**:
```bash
uv add requests                # Add latest requests
uv add "requests>=2.31.0"      # Add with version constraint
uv add --dev black             # Add as dev dependency
uv add --optional docs mkdocs  # Add to optional group
```

**Expected Behavior**:
- Updates pyproject.toml with new dependency
- Updates uv.lock with resolved version
- Installs package if in active venv
- Preserves existing dependency ordering

**Success Output**:
```
Resolved 45 packages in 567ms
Added requests==2.31.0
Updated uv.lock
Installed requests
```

**Error Cases**:
- Package not found → "Error: Package 'invalid-pkg' not found"
- Conflict with existing → "Error: Adding X would conflict with Y<2.0 constraint"
- Already exists → "Warning: requests already in dependencies (updated to X)"

### C-005: Remove Dependency

**Command**: `uv remove <package> [options]`

**Purpose**: Remove a dependency from project

**Options**:
- `--dev`: Remove from development dependencies
- `--optional <group>`: Remove from optional group

**Usage**:
```bash
uv remove requests          # Remove requests
uv remove --dev black       # Remove dev dependency
```

**Expected Behavior**:
- Removes dependency from pyproject.toml
- Updates uv.lock (removes if no longer needed transitively)
- Uninstalls from active venv if present
- Reports orphaned packages (can be removed)

**Success Output**:
```
Removed requests from dependencies
Updated uv.lock
Uninstalled requests

Orphaned packages (can be removed):
  - certifi (depended on by requests only)
  - urllib3 (depended on by requests only)
Run 'uv sync' to remove orphaned packages
```

**Error Cases**:
- Not found → "Error: requests not found in dependencies"
- Required by other → "Warning: Package X is still required by Y"

### C-006: Run Command in Environment

**Command**: `uv run <command>`

**Purpose**: Execute command in the managed virtual environment

**Usage**:
```bash
uv run pytest                    # Run pytest in venv
uv run python script.py          # Run Python script in venv
uv run miminions --help          # Run CLI entry point
```

**Expected Behavior**:
- Activates virtual environment automatically
- Runs command with venv Python and packages
- Streams output to stdout/stderr
- Preserves exit codes

**Success Output**:
```
[Command output streams through]
```

**Error Cases**:
- Venv not found → Automatically runs `uv sync` first
- Command not found → "Error: Command 'invalid' not found in venv"
- Command fails → Preserves original exit code and error output

### C-007: List Installed Packages

**Command**: `uv pip list` or `uv pip freeze`

**Purpose**: Show installed packages

**Usage**:
```bash
uv pip list      # Show all packages with versions
uv pip freeze    # Show in requirements.txt format
```

**Expected Behavior**:
- Lists all packages in active venv
- Shows exact versions
- Sorted alphabetically

**Success Output** (list):
```
Package         Version
fastmcp         2.12.4
openai-agents   0.3.3
pydantic        2.12.0
...
```

**Success Output** (freeze):
```
fastmcp==2.12.4
openai-agents==0.3.3
pydantic==2.12.0
...
```

### C-008: Cache Management

**Command**: `uv cache <subcommand>`

**Purpose**: Manage package cache

**Subcommands**:
- `dir`: Show cache directory path
- `clean`: Remove all cached packages
- `prune`: Remove unused cached packages

**Usage**:
```bash
uv cache dir      # /home/user/.cache/uv
uv cache prune    # Remove unused packages
uv cache clean    # Remove all cached packages
```

**Expected Behavior**:
- `dir`: Prints cache path and exits
- `prune`: Removes packages not in any lock file
- `clean`: Removes all cached files (prompts for confirmation)

**Success Output** (prune):
```
Pruned 15 packages (1.2 GB freed)
```

**Success Output** (clean):
```
Are you sure you want to remove all cached packages? [y/N] y
Removed 42 packages (5.3 GB freed)
```

## Command Conventions

### Exit Codes

| Code | Meaning |
|------|---------|
| 0    | Success |
| 1    | General error (invalid args, file not found) |
| 2    | Dependency resolution error |
| 101  | Network error (offline mode) |
| 102  | Checksum verification failure |

### Output Format

All commands follow these conventions:
- **Info messages**: Plain text, stderr
- **Success messages**: Green text (if TTY), stderr
- **Error messages**: Red text (if TTY), "Error: " prefix, stderr
- **Progress indicators**: Spinners/bars for long operations
- **JSON output**: Add `--json` flag for machine-readable output (future)

### Platform Differences

| Aspect | Windows | macOS/Linux |
|--------|---------|-------------|
| Venv activation | `.venv\Scripts\activate.ps1` | `source .venv/bin/activate` |
| Venv executables | `.venv\Scripts\python.exe` | `.venv/bin/python` |
| Cache location | `%LOCALAPPDATA%\uv\cache` | `~/.cache/uv` |
| Path separator | `;` | `:` |

## Developer Workflow Contracts

### DW-001: First-Time Setup

**Contract**: New contributor can set up environment in <2 steps

**Commands**:
```bash
# Step 1: Clone repository
git clone https://github.com/org/miminions.git
cd miminions

# Step 2: Install dependencies
uv sync
```

**Expected Result**: Fully working development environment

### DW-002: Daily Development

**Contract**: Add dependency, run tests, repeat

**Commands**:
```bash
# Add new dependency
uv add <package>

# Run tests
uv run pytest

# Commit changes
git add pyproject.toml uv.lock
git commit -m "feat: add dependency X"
```

### DW-003: Update Dependencies

**Contract**: Security updates done with single command

**Commands**:
```bash
# Upgrade specific vulnerable package
uv lock --upgrade-package <pkg>

# Or upgrade all packages
uv lock --upgrade

# Install updated versions
uv sync
```

### DW-004: CI/CD Pipeline

**Contract**: CI installs dependencies from lock file deterministically

**Commands**:
```yaml
- run: uv sync --frozen  # Fail if lock out of sync
- run: uv run pytest     # Run tests
```

**Expected Result**: Identical environments across all CI runs

## Error Messages Contract

All error messages must:
1. **Be actionable**: Suggest next steps
2. **Be specific**: Include relevant context (file, line, package)
3. **Be consistent**: Use same terminology across commands

**Examples**:

❌ Bad:
```
Error: failed
```

✅ Good:
```
Error: Failed to install fastmcp==2.12.4
  Cause: Checksum mismatch
  Expected: sha256:abc123...
  Got:      sha256:def456...

  This may indicate a corrupted download or network interference.

  Suggested fix:
    1. Run 'uv cache clean' to clear corrupted cache
    2. Re-run 'uv sync'
    3. If issue persists, check your network connection
```

## Compatibility Contract

UV commands must:
- Work identically on Windows, macOS, Linux
- Support Python 3.12, 3.13 (as specified in requires-python)
- Be backwards compatible with pip workflows during transition
- Not require sudo/admin privileges for normal operations
- Respect proxy settings (HTTP_PROXY, HTTPS_PROXY env vars)

## Documentation References

Each command must have:
- `--help` text with examples
- Entry in CONTRIBUTING.md
- Entry in developer quickstart guide
- Error message links to docs (when applicable)

## Testing Contract

All commands must have:
- Unit tests for core logic
- Integration tests for end-to-end workflows
- Platform-specific tests (Windows/macOS/Linux)
- Error case tests (network failures, permission issues)
- Performance tests (installation speed benchmarks)

Test coverage: 80% minimum for command interface modules
