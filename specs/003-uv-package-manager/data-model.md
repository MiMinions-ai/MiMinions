# Data Model: Modern Python Package Management

**Feature**: Modern Python Package Management
**Date**: 2025-10-19

## Overview

This document describes the configuration structures, file formats, and data relationships involved in the UV package management migration. Unlike traditional data models with database entities, this feature deals with configuration files, lock files, cache structures, and their relationships.

## Configuration Entities

### 1. Project Configuration (pyproject.toml)

**Purpose**: Defines project metadata, dependencies, and build configuration

**Structure**:
```toml
[project]
name = "miminions"
version = "0.2.0"  # MINOR bump for UV migration
description = "..."
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    # Production dependencies
    "fastmcp>=2.12.4",
    "openai-agents>=0.3.3",
    "pydantic>=2.12.0",
    "tiktoken>=0.12.0",
]

[dependency-groups]
dev = [
    # Development dependencies
    "pytest>=8.4.2",
    "pytest-asyncio>=1.2.0",
    "pytest-cov>=7.0.0",
]

[project.scripts]
miminions = "miminions.cli:main"

[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"

# UV-specific configuration (optional)
[tool.uv]
dev-dependencies = []  # Can mirror dependency-groups.dev
index-url = "https://pypi.org/simple"

[[tool.uv.index]]
name = "testpypi"
url = "https://test.pypi.org/simple"
publish = "https://test.pypi.org/legacy/"
explicit = true
```

**Fields**:
- `name`: Package name (immutable)
- `version`: Semver version (increment to 0.2.0 for UV migration)
- `requires-python`: Python version constraint
- `dependencies`: Production dependencies with version specs
- `dependency-groups`: Grouped optional dependencies (PEP 735)
- `project.scripts`: CLI entry points
- `build-system`: Build backend configuration (unchanged)
- `tool.uv`: UV-specific settings (optional)

**Validation Rules**:
- `requires-python` must be ">=3.12" (existing constraint)
- All dependencies must specify minimum version (>=)
- No duplicate dependencies across groups
- Entry points must match existing CLI structure

**Relationships**:
- Generates → Lock File (uv.lock)
- Referenced by → CI/CD workflows
- Consumed by → Build tools (setuptools)

### 2. Lock File (uv.lock)

**Purpose**: Records exact resolved dependency versions for reproducible installations

**Structure** (TOML format):
```toml
version = 1

[[package]]
name = "fastmcp"
version = "2.12.4"
source = { registry = "https://pypi.org/simple" }
dependencies = [
    { name = "pydantic", specifier = ">=2.0.0" },
]
sdist = { url = "https://...", hash = "sha256:..." }
wheels = [
    { url = "https://.../fastmcp-2.12.4-py3-none-any.whl", hash = "sha256:..." },
]

[[package]]
name = "pydantic"
version = "2.12.0"
source = { registry = "https://pypi.org/simple" }
dependencies = []
wheels = [
    { url = "...", hash = "sha256:...", size = 12345 },
]

# ... more packages
```

**Fields**:
- `version`: Lock file format version
- `package`: Array of locked packages
  - `name`: Package name
  - `version`: Exact resolved version (no ranges)
  - `source`: Where package was obtained
  - `dependencies`: Transitive dependencies with their specs
  - `sdist`: Source distribution metadata (optional)
  - `wheels`: Pre-built wheel metadata with hashes
    - `url`: Download URL
    - `hash`: SHA-256 checksum
    - `size`: File size in bytes (optional)

**Validation Rules**:
- All packages must have exact versions (no >=, ~=, etc.)
- All wheels must include SHA-256 hashes
- Dependency graph must be complete (no missing transitive deps)
- Platform markers resolve consistently across platforms

**Relationships**:
- Generated from → Project Configuration (pyproject.toml)
- Consumed by → uv sync command
- Updated by → uv add, uv remove, uv lock --upgrade
- Committed to → Git repository

**State Transitions**:
```
Initial State: No uv.lock exists
├─> uv lock → Lock file generated
├─> uv add <pkg> → Lock file updated with new dependency
├─> uv remove <pkg> → Lock file updated, package removed
├─> uv lock --upgrade → All packages upgraded to latest compatible versions
└─> uv lock --upgrade-package <pkg> → Single package upgraded
```

### 3. Virtual Environment (.venv/)

**Purpose**: Isolated Python environment with installed packages

**Structure**:
```
.venv/
├── bin/              # Unix: executables
│   ├── python -> python3.12
│   ├── activate
│   └── miminions    # CLI entry point
├── Scripts/          # Windows: executables
│   ├── python.exe
│   ├── activate.ps1
│   └── miminions.exe
├── lib/
│   └── python3.12/
│       └── site-packages/  # Installed packages
│           ├── fastmcp/
│           ├── pydantic/
│           └── ...
└── pyvenv.cfg        # Environment metadata
```

**Metadata (pyvenv.cfg)**:
```ini
home = /usr/bin
include-system-site-packages = false
version = 3.12.0
executable = /usr/bin/python3.12
```

**Validation Rules**:
- Must use Python >=3.12
- Must not include system site-packages (isolated)
- Entry points must be executable and point to correct modules

**Relationships**:
- Created by → uv venv or uv sync
- Populated from → Lock File via uv sync
- Activated by → shell scripts (activate, activate.ps1)
- Gitignored → Not committed to repository

**Lifecycle**:
```
Create: uv venv .venv
Activate: source .venv/bin/activate (Unix) | .venv\Scripts\activate.ps1 (Windows)
Install: uv sync --frozen
Update: uv sync (after lock file changes)
Recreate: rm -rf .venv && uv sync
```

### 4. Package Cache (~/.cache/uv/)

**Purpose**: Local storage of downloaded packages for reuse across projects

**Structure**:
```
~/.cache/uv/
├── built-wheels/      # Cached built wheels
│   ├── pypi/
│   │   └── fastmcp/
│   │       └── 2.12.4/
│   │           └── fastmcp-2.12.4-py3-none-any.whl
│   └── git/
├── wheels/            # Downloaded wheels
│   └── pypi/
│       └── fastmcp-2.12.4-py3-none-any.whl
├── sdists/            # Source distributions
│   └── pypi/
│       └── fastmcp-2.12.4.tar.gz
└── archive-v0/        # Archive format cache
```

**Characteristics**:
- **Global**: Shared across all projects
- **Persistent**: Survives virtual environment deletions
- **Offline-capable**: Enables installation without network
- **Keyed by hash**: Package contents verified by SHA-256

**Validation Rules**:
- Downloaded files must match lock file hashes
- Cache must be readable/writable by user
- No executable content outside virtual environments

**Relationships**:
- Populated by → uv sync, uv add commands
- Consumed by → Subsequent uv sync operations
- Managed by → uv cache prune, uv cache clean

**Management Commands**:
```bash
uv cache dir        # Show cache location
uv cache prune      # Remove unused cached packages
uv cache clean      # Clear entire cache
```

### 5. CI/CD Configuration (.github/workflows/*.yml)

**Purpose**: Automated testing and build pipeline configuration

**Structure** (example):
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ['3.12', '3.13']

    steps:
      - uses: actions/checkout@v4

      - name: Set up UV
        uses: astral-sh/setup-uv@v1
        with:
          version: "latest"
          enable-cache: true
          cache-dependency-glob: "uv.lock"

      - name: Set up Python
        run: uv python install ${{ matrix.python-version }}

      - name: Install dependencies
        run: uv sync --frozen

      - name: Run tests
        run: uv run pytest --cov=miminions

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

**Fields**:
- `matrix.os`: Test on Windows, macOS, Linux
- `matrix.python-version`: Test on Python 3.12, 3.13
- `setup-uv.enable-cache`: Enable GitHub Actions cache
- `setup-uv.cache-dependency-glob`: Cache key based on uv.lock
- `uv sync --frozen`: Install exact lock file versions (no modifications)

**Validation Rules**:
- Must test all supported platforms
- Must use --frozen flag to enforce lock file
- Must validate lock file is up-to-date
- Must cache UV cache directory for performance

**Relationships**:
- Depends on → Lock File (uv.lock)
- Uses → UV cache for performance
- Validates → All test suites pass

## Data Relationships Diagram

```
┌─────────────────────┐
│  pyproject.toml     │
│  (Source of Truth)  │
└──────────┬──────────┘
           │
           │ uv lock
           ▼
┌─────────────────────┐         ┌──────────────────┐
│     uv.lock         │────────>│  .venv/          │
│  (Exact Versions)   │ uv sync │  (Installed)     │
└──────────┬──────────┘         └──────────────────┘
           │                              │
           │                              │ Activates
           │                              ▼
           │                    ┌──────────────────┐
           │                    │  Shell Environment│
           │                    │  (Development)    │
           │                    └──────────────────┘
           │
           │ Downloads
           ▼
┌─────────────────────┐         ┌──────────────────┐
│  ~/.cache/uv/       │<────────│  PyPI Registry   │
│  (Package Cache)    │ Fetch   │  (Packages)      │
└─────────────────────┘         └──────────────────┘
           │
           │ Reuses
           ▼
┌─────────────────────┐
│  CI/CD (.github/)   │
│  (Automated Tests)  │
└─────────────────────┘
```

## File Ownership and Lifecycle

| File/Directory | Version Control | Created By | Updated By | Lifecycle |
|----------------|----------------|------------|------------|-----------|
| pyproject.toml | ✅ Committed | Manual/init | Manual | Long-lived (project) |
| uv.lock | ✅ Committed | uv lock | uv add/remove/lock | Long-lived (regenerated on dep changes) |
| .venv/ | ❌ Gitignored | uv venv/sync | uv sync | Ephemeral (recreatable from lock) |
| ~/.cache/uv/ | ❌ Local only | uv sync | uv sync | Persistent (shared across projects) |
| .github/workflows/ | ✅ Committed | Manual | Manual | Long-lived (CI config) |

## Migration Impact

### Before Migration (pip)

```
pyproject.toml (dependencies)
     │
     │ pip install -e .
     ▼
.venv/ (installed packages)
     │
     │ pip freeze
     ▼
requirements.txt (approximate versions)
```

**Issues**:
- No lock file → Non-reproducible builds
- Slow installation → 2-5 minutes cold
- No cache → Every install re-downloads

### After Migration (UV)

```
pyproject.toml (dependencies)
     │
     │ uv lock
     ▼
uv.lock (exact versions + hashes)
     │
     │ uv sync
     ▼
.venv/ (installed packages) + ~/.cache/uv/
```

**Improvements**:
- Lock file → 100% reproducible builds
- Fast installation → <1 minute cold, <15s warm
- Global cache → Reuse across projects

## Validation and Integrity

### Hash Verification

Every package in uv.lock includes SHA-256 hash:
```toml
wheels = [
  { url = "https://...", hash = "sha256:abc123..." }
]
```

UV verifies hash before installation:
1. Download package from URL
2. Compute SHA-256 of downloaded file
3. Compare with lock file hash
4. Install only if match (fail otherwise)

### Lock File Consistency

Check lock file is current:
```bash
uv lock --check  # Exit 0 if up-to-date, 1 if outdated
```

CI pipeline validation:
```yaml
- name: Validate lock file
  run: uv lock --check
```

### Cross-Platform Reproducibility

Lock file includes platform-specific wheels:
```toml
[[package]]
name = "tiktoken"
wheels = [
  { url = "...-cp312-cp312-win_amd64.whl", hash = "sha256:..." },
  { url = "...-cp312-cp312-macosx_11_0_arm64.whl", hash = "sha256:..." },
  { url = "...-cp312-cp312-manylinux_2_17_x86_64.whl", hash = "sha256:..." },
]
```

UV selects appropriate wheel for current platform automatically.

## Summary

The UV migration introduces structured, versioned configuration with strong reproducibility guarantees through:

1. **pyproject.toml**: Human-edited dependency specifications (unchanged format)
2. **uv.lock**: Machine-generated exact versions with cryptographic hashes
3. **.venv/**: Ephemeral installation directory (recreatable from lock)
4. **~/.cache/uv/**: Persistent global cache for offline and fast installations
5. **CI/CD**: Automated validation ensuring lock file integrity

All files follow established Python standards (PEP 621, 735) with UV providing superior tooling for lock file generation and installation performance.
