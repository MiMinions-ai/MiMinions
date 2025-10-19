# Migration Contract: pip to UV

**Feature**: Modern Python Package Management
**Date**: 2025-10-19
**Type**: Migration Validation Contract

## Purpose

This contract defines the validation criteria that must be satisfied before, during, and after the migration from pip to UV. All criteria must pass to consider the migration successful.

## Pre-Migration Requirements

### PMR-001: Baseline Dependency Inventory
**Requirement**: Document all currently installed dependencies with exact versions

**Validation**:
```bash
# Generate baseline
pip freeze > baseline-deps.txt

# Must include at minimum:
# - fastmcp==2.12.4
# - openai-agents==0.3.3
# - pydantic==2.12.0
# - tiktoken==0.12.0
# + all transitive dependencies
```

**Success Criteria**: baseline-deps.txt generated successfully with >10 packages

### PMR-002: Test Suite Baseline
**Requirement**: All existing tests must pass with pip-installed dependencies

**Validation**:
```bash
pytest --cov=miminions --cov-report=term
```

**Success Criteria**:
- All tests pass (0 failures)
- Coverage >=80% (existing baseline)
- No warnings related to dependency issues

### PMR-003: pyproject.toml Validation
**Requirement**: pyproject.toml must be PEP 621 compliant

**Validation**:
```bash
# Check syntax
python -c "import tomllib; tomllib.load(open('pyproject.toml', 'rb'))"

# Validate schema
uv lock --dry-run  # Should succeed without errors
```

**Success Criteria**: No syntax errors, UV can resolve dependencies

## Migration Execution Requirements

### MER-001: UV Installation
**Requirement**: UV must be installed and accessible

**Validation**:
```bash
uv --version
# Expected: uv 0.5.0 or later
```

**Success Criteria**: UV executable available, version >=0.5.0

### MER-002: Lock File Generation
**Requirement**: uv.lock must be generated successfully from pyproject.toml

**Validation**:
```bash
uv lock
# Should create uv.lock with all dependencies resolved
```

**Success Criteria**:
- uv.lock file created
- Contains all dependencies from pyproject.toml
- Contains all transitive dependencies
- Includes SHA-256 hashes for all packages
- No unresolved conflicts

**Contract Format**:
```toml
version = 1  # Lock file format version

[[package]]
name = "..."
version = "..."  # Must be exact version (no ranges)
source = { ... }
wheels = [
  { url = "...", hash = "sha256:..." }  # Hash required
]
```

### MER-003: Virtual Environment Recreation
**Requirement**: New virtual environment must be created with UV

**Validation**:
```bash
rm -rf .venv
uv venv
source .venv/bin/activate  # Unix
# or
.venv\Scripts\activate.ps1  # Windows
```

**Success Criteria**:
- .venv/ directory created
- Python version >=3.12
- Environment activates successfully
- No packages installed yet (clean slate)

### MER-004: Dependency Installation from Lock
**Requirement**: Dependencies must install from uv.lock exactly as recorded

**Validation**:
```bash
uv sync --frozen
```

**Success Criteria**:
- All packages from uv.lock installed
- Exact versions match lock file
- Installation completes without errors
- Checksums verified for all packages

### MER-005: Dependency Parity
**Requirement**: UV-installed dependencies must match pip baseline

**Validation**:
```bash
# Generate new inventory
uv pip freeze > uv-deps.txt

# Compare package names (versions may differ slightly due to resolution)
comm -3 <(cut -d'=' -f1 baseline-deps.txt | sort) <(cut -d'=' -f1 uv-deps.txt | sort)
```

**Success Criteria**:
- All baseline packages present in UV installation
- No missing critical dependencies
- Acceptable: Different transitive dep versions if compatible

## Post-Migration Validation Requirements

### PVR-001: Test Suite Parity
**Requirement**: All tests must pass with UV-installed dependencies

**Validation**:
```bash
uv run pytest --cov=miminions --cov-report=term
```

**Success Criteria**:
- Same number of tests pass as pre-migration baseline
- Coverage >=80% (same as baseline)
- No new failures or errors
- No deprecation warnings from dependency changes

### PVR-002: Functional Parity
**Requirement**: All CLI commands and features must work identically

**Validation**:
```bash
# Test CLI entry point
uv run miminions --help

# Test agent functionality (from examples/)
uv run python examples/ai_studio.py
uv run python examples/argos_engine.py
uv run python examples/software_trio.py
```

**Success Criteria**:
- All commands execute without errors
- Example scripts run successfully
- Output matches expected behavior
- No import errors or module not found issues

### PVR-003: Performance Validation
**Requirement**: Installation must be >=2x faster than pip baseline

**Validation**:
```bash
# Measure pip installation time (clean cache)
time (rm -rf .venv && python -m venv .venv && source .venv/bin/activate && pip install -e .)

# Measure UV installation time (clean cache)
time (rm -rf .venv && uv cache clean && uv sync)
```

**Success Criteria**:
- UV installation time <50% of pip installation time
- Target: <1 minute for cold install, <15s for warm cache

### PVR-004: Reproducibility Validation
**Requirement**: Lock file must produce identical installations across environments

**Validation**:
```bash
# Platform 1 (e.g., Windows)
uv sync --frozen
uv pip freeze > install1.txt

# Platform 2 (e.g., macOS)
uv sync --frozen
uv pip freeze > install2.txt

# Platform 3 (e.g., Linux)
uv sync --frozen
uv pip freeze > install3.txt

# Compare
diff install1.txt install2.txt  # Should be identical or only platform-specific diffs
```

**Success Criteria**:
- Identical package versions across all platforms
- Platform-specific wheels selected appropriately
- No randomness in installation order or versions

### PVR-005: Offline Mode Validation
**Requirement**: Installation must work offline after initial cache population

**Validation**:
```bash
# Online: Populate cache
uv sync

# Simulate offline: Disable network
rm -rf .venv

# Offline: Reinstall from cache
uv sync --offline
```

**Success Criteria**:
- Installation succeeds without network access
- All packages installed from cache
- Identical to online installation

### PVR-006: CI/CD Pipeline Validation
**Requirement**: GitHub Actions workflow must complete successfully with UV

**Validation**:
```yaml
# .github/workflows/test.yml must pass on:
- Ubuntu Latest
- Windows Latest
- macOS Latest
```

**Success Criteria**:
- All CI jobs pass
- Test execution time <=previous baseline
- Dependency installation completes in <1 minute (cached)

## Rollback Criteria

If any of the following conditions occur, rollback to pip:

### RBC-001: Critical Test Failures
- More than 5% of tests fail with UV-installed dependencies
- Core functionality broken (e.g., agent system, MCP tools)

### RBC-002: Dependency Resolution Failures
- UV cannot resolve dependencies (conflicts)
- Lock file generation fails repeatedly
- Missing critical packages

### RBC-003: Platform Incompatibility
- UV fails on any supported platform (Windows/macOS/Linux)
- Platform-specific issues cannot be resolved within 2 weeks

### RBC-004: Performance Regression
- UV installation slower than pip (fails performance validation)
- Increased CI/CD pipeline time

## Rollback Procedure

```bash
# 1. Remove UV-specific files
rm uv.lock

# 2. Revert CI/CD changes
git checkout main -- .github/workflows/

# 3. Reinstall with pip
rm -rf .venv
python -m venv .venv
source .venv/bin/activate  # Unix
pip install -e .

# 4. Verify tests pass
pytest --cov=miminions

# 5. Document rollback reason in GitHub issue
```

## Success Metrics

Migration is considered successful when:

- ✅ All Pre-Migration Requirements (PMR-*) pass
- ✅ All Migration Execution Requirements (MER-*) pass
- ✅ All Post-Migration Validation Requirements (PVR-*) pass
- ✅ No Rollback Criteria (RBC-*) triggered
- ✅ Team approval via GitHub Discussion
- ✅ Documentation updated (CONTRIBUTING.md, README.md)

## Sign-off Checklist

- [ ] Pre-migration baseline captured
- [ ] All tests pass pre-migration
- [ ] UV installed and lock file generated
- [ ] Dependencies installed from lock successfully
- [ ] All tests pass post-migration
- [ ] Performance targets met (2x faster)
- [ ] Reproducibility validated across platforms
- [ ] Offline mode validated
- [ ] CI/CD pipeline passing
- [ ] Documentation updated
- [ ] Team review completed
- [ ] GitHub Discussion approval received

**Migration Lead**: [TBD]
**Review Date**: [TBD]
**Approval Date**: [TBD]
