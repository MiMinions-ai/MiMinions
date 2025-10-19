# Research: Modern Python Package Management with UV

**Feature**: Modern Python Package Management
**Date**: 2025-10-19
**Status**: Complete

## Executive Summary

UV is a modern Python package manager written in Rust that provides 10-100x faster package resolution and installation compared to pip. This research validates the technical feasibility of migrating MiMinions from pip to UV while maintaining compatibility with existing workflows and meeting all constitution requirements.

## Research Areas

### 1. UV Package Manager Capabilities

**Decision**: Adopt UV as the primary development package manager

**Rationale**:
- **Performance**: 10-100x faster than pip for package resolution and installation (meets SC-002: 2x faster requirement)
- **Compatibility**: Full support for PEP 621 (pyproject.toml), PEP 517/518 (build system)
- **Lock Files**: Built-in lock file generation (uv.lock) ensures reproducible installations
- **Cross-Platform**: Native support for Windows, macOS, Linux without platform-specific workarounds
- **Python Version Management**: Can manage Python versions itself (optional feature)
- **Virtual Environments**: Built-in venv creation and management
- **Offline Support**: Cached packages enable full offline development

**Alternatives Considered**:
- **Poetry**: Feature-rich but slower than UV, different lock file format, heavier weight
- **PDM**: Modern but smaller community, less mature caching
- **pip-tools**: Lighter weight but lacks integrated venv management, still uses pip underneath
- **Rye**: UV-based but adds opinionated project structure that may conflict with existing layout

**Why UV Wins**: Performance, standards compliance, minimal migration effort, active development by Astral (same team as ruff)

### 2. Migration Strategy from pip to UV

**Decision**: Phased migration with backwards compatibility

**Approach**:
1. **Phase 1**: Add UV support while maintaining pip compatibility
   - Install UV as development tool
   - Generate uv.lock from existing pyproject.toml
   - Update CONTRIBUTING.md with UV instructions
   - Keep both workflows functional

2. **Phase 2**: Update CI/CD to use UV
   - Modify GitHub Actions workflows
   - Enable UV cache in CI
   - Validate performance improvements

3. **Phase 3**: Deprecate pip instructions (documentation only)
   - Update README to recommend UV
   - Mark pip instructions as legacy
   - No breaking changes to pyproject.toml

**Rollback Plan**: UV reads standard pyproject.toml; reverting to pip requires only removing uv.lock

**Migration Validation**:
- Lock file generation succeeds with all existing dependencies
- Virtual environment activation works identically
- All tests pass with UV-installed dependencies
- No changes to end-user installation (pip install miminions still works)

### 3. Lock File Format and Reproducibility

**Decision**: Use UV's native uv.lock format

**Lock File Structure**:
```toml
# uv.lock format (simplified example)
[[package]]
name = "fastmcp"
version = "2.12.4"
source = { registry = "https://pypi.org/simple" }
dependencies = [...]
wheels = [
  { url = "...", hash = "sha256:..." },
]
```

**Reproducibility Guarantees**:
- **Exact Versions**: Locks all transitive dependencies to specific versions
- **Hash Verification**: SHA-256 hashes for all downloaded packages
- **Platform Markers**: Separate lock entries for platform-specific packages
- **Source Tracking**: Records package source (PyPI, git, local)
- **Deterministic Resolution**: Same lock file from same pyproject.toml inputs

**Lock File Workflow**:
- `uv lock` - Generate/update uv.lock from pyproject.toml
- `uv sync` - Install exact versions from uv.lock
- `uv add <package>` - Add dependency and update lock file
- `uv remove <package>` - Remove dependency and update lock file

**Best Practices**:
- Commit uv.lock to version control
- Run `uv lock --upgrade` periodically for security updates
- Use `uv sync --frozen` in CI to enforce lock file usage
- Validate lock file in code review for dependency changes

### 4. CI/CD Integration Patterns

**Decision**: Use official UV GitHub Action with caching

**GitHub Actions Integration**:
```yaml
# .github/workflows/test.yml (example)
- name: Set up UV
  uses: astral-sh/setup-uv@v1
  with:
    version: "latest"
    enable-cache: true

- name: Install dependencies
  run: uv sync --frozen

- name: Run tests
  run: uv run pytest
```

**Caching Strategy**:
- UV automatically caches in `~/.cache/uv` (Linux/macOS) or `%LOCALAPPDATA%\uv\cache` (Windows)
- GitHub Actions cache restores UV cache between runs
- Cache key based on lock file hash ensures fresh installs on dependency changes

**Performance Expectations**:
- **First run** (cold cache): 30-60 seconds (faster than pip)
- **Subsequent runs** (warm cache, no changes): 5-15 seconds (SC-004: <1 minute ✓)
- **Changed dependencies**: 10-30 seconds (only downloads changed packages)

**CI/CD Best Practices**:
- Use `uv sync --frozen` to prevent lock file modifications in CI
- Enable cache with appropriate cache key (lock file hash)
- Run `uv lock --check` to validate lock file is up-to-date
- Set UV_SYSTEM_PYTHON=1 if running in Docker without venv

### 5. Dependency Group Management

**Decision**: Use UV's native support for dependency groups (PEP 735)

**Current Structure** (already compatible):
```toml
[dependency-groups]
dev = [
    "pytest>=8.4.2",
    "pytest-asyncio>=1.2.0",
    "pytest-cov>=7.0.0",
]
```

**UV Commands for Dependency Groups**:
- `uv sync` - Install all dependencies including dev group
- `uv sync --only-dev` - Install only dev dependencies
- `uv sync --no-dev` - Install only production dependencies
- `uv add --dev <package>` - Add development dependency

**Future Groups** (examples for MiMinions roadmap):
```toml
[dependency-groups]
dev = ["pytest>=8.4.2", ...]
docs = ["mkdocs>=1.5.0", "mkdocs-material>=9.0.0"]
cli = ["rich>=13.0.0", "typer>=0.9.0"]  # Phase 3 CLI feature
multi-agent = ["ray>=2.0.0"]  # Phase 2 runtime feature (if needed)
```

### 6. Platform-Specific Considerations

**Decision**: Rely on UV's built-in platform handling

**Windows Considerations**:
- UV supports both PowerShell and Command Prompt
- Path handling uses platform-agnostic resolution
- Virtual environment activation: `. .venv\Scripts\activate` (PowerShell) or `.venv\Scripts\activate.bat` (CMD)

**macOS/Linux Considerations**:
- Standard Unix shell activation: `source .venv/bin/activate`
- UV respects XDG Base Directory specification

**Cross-Platform Testing**:
- Lock file works identically across platforms
- Platform markers in dependencies resolve correctly
- CI matrix testing on Windows/macOS/Linux validates compatibility

### 7. Offline Development Support

**Decision**: UV cache enables full offline development after initial setup

**Offline Capabilities**:
- First sync downloads and caches all packages
- Subsequent syncs use cache even without network
- `uv sync --offline` - Fail if network required (validation mode)
- `uv cache prune` - Clean unused cached packages

**Cache Management**:
- Cache location: `~/.cache/uv` (configurable via UV_CACHE_DIR)
- Cache size: Typically 100-500MB for moderate projects
- Cache persistence: Survives across virtual environment deletions

**Offline Workflow**:
1. Initial setup (online): `uv sync` - Downloads all packages
2. Development (offline): Create new venv, `uv sync` uses cache
3. Add dependency (offline): Fails gracefully with clear message
4. Periodic refresh (online): `uv lock --upgrade` for security updates

### 8. Testing and Validation Strategy

**Decision**: Multi-layered testing approach before full migration

**Test Categories**:

1. **Migration Validation Tests**:
   - Verify uv.lock can be generated from existing pyproject.toml
   - Confirm all dependencies resolve without conflicts
   - Validate checksums match for reproducibility

2. **Installation Performance Tests**:
   - Benchmark: Fresh install time (cold cache)
   - Benchmark: Cached install time (warm cache)
   - Target: 2x faster than pip baseline (SC-002)

3. **Reproducibility Tests**:
   - Install from lock file on 3 different machines (Windows/macOS/Linux)
   - Verify byte-for-byte identical package versions
   - Test: Lock file from same pyproject.toml is deterministic

4. **Integration Tests**:
   - All existing test suite passes with UV-installed dependencies
   - CLI commands work identically
   - MCP tools load correctly
   - Agent systems function as expected

5. **CI/CD Pipeline Tests**:
   - GitHub Actions workflow with UV completes successfully
   - Cached runs meet <1 minute target (SC-004)
   - No flaky tests due to dependency installation

**Test Implementation Plan**:
```
tests/migration/
├── test_uv_lock_generation.py      # Lock file creation and validation
├── test_installation_performance.py # Benchmark against targets
├── test_reproducibility.py          # Cross-platform consistency
└── test_offline_mode.py             # Cache and offline capabilities
```

## Research Conclusions

### Key Findings

1. **UV is production-ready** for MiMinions migration
2. **Zero breaking changes** to existing pyproject.toml required
3. **Performance targets are conservative** - UV typically exceeds 2x improvement
4. **Constitution compliance** validated across all principles
5. **Migration risk is low** with clear rollback path

### Open Questions Resolved

- ✅ **Can UV handle existing dependency-groups syntax?** Yes, full PEP 735 support
- ✅ **Will lock file work across Windows/macOS/Linux?** Yes, platform markers handled automatically
- ✅ **Can contributors still use pip?** Yes during transition, pyproject.toml remains standard
- ✅ **How does UV handle private packages?** Supports custom indexes, git sources, local paths
- ✅ **What's the rollback plan?** Remove uv.lock, revert CI changes - no pyproject.toml changes needed

### Recommended Next Steps

1. ✅ **Research Complete** - No blockers identified
2. → **Phase 1: Design** - Create data-model.md and migration contracts
3. → **Phase 2: Implementation** - Generate tasks.md for execution

## References

- UV Documentation: https://github.com/astral-sh/uv
- PEP 621 (pyproject.toml): https://peps.python.org/pep-0621/
- PEP 735 (Dependency Groups): https://peps.python.org/pep-0735/
- UV GitHub Action: https://github.com/astral-sh/setup-uv
- Astral Blog: UV performance benchmarks
