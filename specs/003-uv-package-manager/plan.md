# Implementation Plan: Modern Python Package Management

**Branch**: `003-uv-package-manager` | **Date**: 2025-10-19 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-uv-package-manager/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Transition MiMinions to use UV as the primary package management tool to achieve faster dependency installation (2x improvement), reproducible builds across environments, and streamlined developer onboarding. The migration will maintain compatibility with existing Python packaging standards while improving CI/CD performance and developer experience.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: UV package manager, pyproject.toml (PEP 621), setuptools build backend
**Storage**: Local file system for package cache, lock files, and virtual environments
**Testing**: pytest, pytest-asyncio, pytest-cov
**Target Platform**: Cross-platform (Windows, macOS, Linux) for local development and CI/CD
**Project Type**: Single project (Python package with CLI)
**Performance Goals**:
  - Dependency installation 2x faster than current pip-based approach
  - Environment setup in under 2 minutes with caching
  - CI/CD dependency installation in under 1 minute for unchanged dependencies
**Constraints**:
  - Must maintain compatibility with existing pyproject.toml structure
  - Must support offline development after initial setup
  - Must work across Windows, macOS, and Linux without platform-specific workarounds
  - Lock files must ensure 100% reproducible builds
**Scale/Scope**:
  - Migration of existing ~10 direct dependencies
  - Support for development, testing, and optional dependency groups
  - Documentation and migration guides for contributors
  - CI/CD pipeline updates for GitHub Actions

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md`:

- [x] **Local-First Architecture**: Package management runs entirely locally; cached packages enable offline development after initial setup
- [x] **Framework Agnostic**: N/A - This is infrastructure tooling, not framework-specific functionality
- [x] **Optional Dependencies**: UV itself becomes a development dependency; existing pip workflows remain functional during transition
- [x] **TDD (NON-NEGOTIABLE)**: Test plan includes migration validation tests, lock file verification, and installation performance benchmarks
- [x] **Documentation Excellence**: Migration guide, quickstart for new contributors, UV command reference
- [x] **Open Governance**: Package management change affects all contributors; will create GitHub Discussion for feedback before merge
- [x] **Semantic Versioning**: MINOR version bump (0.1.0 → 0.2.0) - New development workflow, backwards compatible for end users
- [x] **Simplicity & YAGNI**: Justified by measurable pain points - slow pip installations, reproducibility issues, contributor friction

*Note: If any gates are violated, document justification in Complexity Tracking table below.*

## Project Structure

### Documentation (this feature)

```
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
src/miminions/
├── agent/           # Agent implementations
├── core/            # Core workspace and reasoning
├── data/            # Data management
├── interface/cli/   # CLI commands
├── memory/          # Memory management
├── tools/           # Tool adapters (MCP)
├── user/            # User management
└── utility/         # Utility functions

tests/
├── cases/           # Test cases
├── cli/             # CLI tests
├── data/            # Data layer tests
└── conftest.py      # Pytest configuration

# Configuration files affected by UV migration
pyproject.toml       # Project metadata and dependencies
uv.lock              # Lock file (to be generated)
.github/workflows/   # CI/CD pipeline updates
```

**Structure Decision**: Single Python package structure. The UV migration will primarily affect:
1. Root-level configuration files (pyproject.toml, new uv.lock)
2. CI/CD workflows (.github/workflows/*.yml)
3. Developer documentation (CONTRIBUTING.md, README.md)
4. New migration tests (tests/migration/ or tests/integration/test_uv_migration.py)

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

**Status**: No violations - table remains empty

All constitution principles validated in initial check and confirmed post-design.

## Post-Design Constitution Re-check

*Re-evaluated after Phase 0 (Research) and Phase 1 (Design) completion*

- [x] **Local-First Architecture**: ✅ CONFIRMED - UV cache enables full offline development, no cloud dependencies
- [x] **Framework Agnostic**: ✅ CONFIRMED - Package management is infrastructure layer, no framework lock-in
- [x] **Optional Dependencies**: ✅ CONFIRMED - UV can be adopted incrementally, pip remains functional
- [x] **TDD (NON-NEGOTIABLE)**: ✅ CONFIRMED - Migration contract defines comprehensive test plan (tests/migration/)
- [x] **Documentation Excellence**: ✅ CONFIRMED - Quickstart guide, migration contract, command interface documented
- [x] **Open Governance**: ✅ CONFIRMED - GitHub Discussion created for community feedback before merge
- [x] **Semantic Versioning**: ✅ CONFIRMED - MINOR bump (0.1.0 → 0.2.0), no breaking changes for users
- [x] **Simplicity & YAGNI**: ✅ CONFIRMED - Research validates performance pain points, migration contracts ensure minimal complexity

**Design Artifacts Generated**:
- ✅ research.md - 8 research areas, UV validated as production-ready
- ✅ data-model.md - Configuration structures, lock file format, relationships
- ✅ contracts/migration-contract.md - Pre/during/post migration validation criteria
- ✅ contracts/command-interface.md - UV command specifications and error handling
- ✅ quickstart.md - Developer getting-started guide with examples
- ✅ CLAUDE.md - Agent context updated with UV-specific knowledge

**No violations identified**. Design complies with all constitution principles.

## Next Steps

**Phase 2: Task Generation** (Next Command)
- Run `/speckit.tasks` to generate dependency-ordered implementation tasks
- Will create tasks.md with specific work items based on this plan

**Phase 3: Implementation** (After Task Generation)
- Run `/speckit.implement` to execute tasks in order
- Automated testing and validation per migration contract

