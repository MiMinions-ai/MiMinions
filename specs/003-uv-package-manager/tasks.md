# Tasks: Modern Python Package Management

**Input**: Design documents from `/specs/003-uv-package-manager/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/migration-contract.md, contracts/command-interface.md

**Tests**: TDD is mandatory per constitution. All test tasks MUST be written first and MUST fail before implementation begins.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: `src/`, `tests/` at repository root
- Repository root: `F:\10 MiMinions.ai\dev\MiMinions`
- Configuration files: `pyproject.toml`, `uv.lock`, `.gitignore`
- CI/CD: `.github/workflows/`
- Documentation: `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`
- Tests: `tests/migration/` (new directory for UV migration tests)

## Phase 1: Setup (Project Initialization)

**Purpose**: Prepare project structure for UV migration and establish baseline

- [ ] T001 Create migration test directory at tests/migration/
- [ ] T002 [P] Create __init__.py in tests/migration/
- [ ] T003 Capture baseline dependency inventory using pip freeze > baseline-deps.txt
- [ ] T004 Run baseline test suite and record pass rate using pytest --cov=miminions
- [ ] T005 Document baseline metrics in specs/003-uv-package-manager/baseline-metrics.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Generate lock file and update version - MUST be complete before user story work

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T006 Update version from 0.1.0 to 0.2.0 in pyproject.toml
- [ ] T007 Generate uv.lock from existing pyproject.toml using uv lock
- [ ] T008 Validate lock file contains all dependencies with SHA-256 hashes
- [ ] T009 Update .gitignore to ensure .venv/ is ignored and uv.lock is tracked

**Checkpoint**: Lock file generated and version updated - user story implementation can now begin

---

## Phase 3: User Story 1 - First-Time Development Environment Setup (Priority: P1) 🎯 MVP

**Goal**: New contributors can set up MiMinions development environment in under 2 minutes with simple commands

**Independent Test**: Clone repository on clean machine, run setup command, verify all dependencies install and tests pass

### Tests for User Story 1 (TDD - Write First)

**NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T010 [P] [US1] Create lock file generation test in tests/migration/test_uv_lock_generation.py
- [ ] T011 [P] [US1] Create environment setup test in tests/migration/test_environment_setup.py
- [ ] T012 [P] [US1] Create dependency parity test in tests/migration/test_dependency_parity.py
- [ ] T013 [US1] Run tests to verify they FAIL (expected - no UV implementation yet)

### Implementation for User Story 1

- [ ] T014 [P] [US1] Update README.md with UV installation instructions
- [ ] T015 [P] [US1] Update README.md with quickstart setup steps (uv sync)
- [ ] T016 [US1] Update CONTRIBUTING.md with UV development workflow
- [ ] T017 [US1] Add troubleshooting section to CONTRIBUTING.md for common UV issues
- [ ] T018 [US1] Verify quickstart.md documentation is accurate and complete
- [ ] T019 [US1] Test fresh environment setup on Windows (manual validation)
- [ ] T020 [US1] Test fresh environment setup on macOS (manual validation)
- [ ] T021 [US1] Test fresh environment setup on Linux (manual validation)
- [ ] T022 [US1] Validate all T010-T012 tests now PASS with UV implementation

**Checkpoint**: New contributors can clone repo and run `uv sync` to get working environment in <2 minutes

---

## Phase 4: User Story 2 - Dependency Management During Development (Priority: P2)

**Goal**: Developers can add, update, or remove dependencies in under 30 seconds with clear workflows

**Independent Test**: Add new dependency, verify it's in pyproject.toml and uv.lock, confirm it's installed in venv

### Tests for User Story 2 (TDD - Write First)

- [ ] T023 [P] [US2] Create dependency add test in tests/migration/test_dependency_management.py (test_add_dependency)
- [ ] T024 [P] [US2] Create dependency remove test in tests/migration/test_dependency_management.py (test_remove_dependency)
- [ ] T025 [P] [US2] Create dependency upgrade test in tests/migration/test_dependency_management.py (test_upgrade_dependency)
- [ ] T026 [US2] Run tests to verify they FAIL (expected - no documentation yet)

### Implementation for User Story 2

- [ ] T027 [US2] Document "uv add <package>" workflow in CONTRIBUTING.md
- [ ] T028 [US2] Document "uv remove <package>" workflow in CONTRIBUTING.md
- [ ] T029 [US2] Document "uv lock --upgrade-package <pkg>" workflow in CONTRIBUTING.md
- [ ] T030 [US2] Document "uv lock --upgrade" workflow for all packages in CONTRIBUTING.md
- [ ] T031 [US2] Add section on committing pyproject.toml and uv.lock changes to CONTRIBUTING.md
- [ ] T032 [US2] Test uv add command manually and verify workflow
- [ ] T033 [US2] Test uv remove command manually and verify workflow
- [ ] T034 [US2] Test uv lock --upgrade workflow manually
- [ ] T035 [US2] Validate all T023-T025 tests now PASS with documentation complete

**Checkpoint**: Developers have clear, tested workflows for all dependency management tasks

---

## Phase 5: User Story 3 - Reproducible Builds Across Environments (Priority: P3)

**Goal**: 100% reproducible builds - identical package versions across all machines and CI/CD

**Independent Test**: Install from lock file on two machines, verify byte-for-byte identical package versions

### Tests for User Story 3 (TDD - Write First)

- [ ] T036 [P] [US3] Create reproducibility test in tests/migration/test_reproducibility.py
- [ ] T037 [P] [US3] Create offline mode test in tests/migration/test_offline_mode.py
- [ ] T038 [P] [US3] Create hash verification test in tests/migration/test_hash_verification.py
- [ ] T039 [US3] Run tests to verify they FAIL (expected - validation not yet in place)

### Implementation for User Story 3

- [ ] T040 [US3] Test lock file reproducibility on Windows (clean install, capture versions)
- [ ] T041 [US3] Test lock file reproducibility on macOS (clean install, capture versions)
- [ ] T042 [US3] Test lock file reproducibility on Linux (clean install, capture versions)
- [ ] T043 [US3] Compare package versions across platforms and verify identical
- [ ] T044 [US3] Test offline development workflow (uv sync --offline after cache populated)
- [ ] T045 [US3] Validate hash verification prevents corrupted package installation
- [ ] T046 [US3] Document reproducibility guarantees in README.md
- [ ] T047 [US3] Document offline development workflow in CONTRIBUTING.md
- [ ] T048 [US3] Validate all T036-T038 tests now PASS with reproducibility confirmed

**Checkpoint**: Lock file provides 100% reproducible builds, offline development works

---

## Phase 6: User Story 4 - Fast CI/CD Dependency Installation (Priority: P4)

**Goal**: CI/CD pipeline installs dependencies in under 1 minute with caching

**Independent Test**: Run CI pipeline, measure dependency installation time, verify <1 minute with cache

### Tests for User Story 4 (TDD - Write First)

- [ ] T049 [P] [US4] Create CI performance benchmark test in tests/migration/test_ci_performance.py
- [ ] T050 [US4] Run test to verify it FAILS (expected - CI not yet updated)

### Implementation for User Story 4

- [ ] T051 [US4] Update .github/workflows/test.yml to use astral-sh/setup-uv@v1 action
- [ ] T052 [US4] Configure UV cache in .github/workflows/test.yml with enable-cache: true
- [ ] T053 [US4] Replace pip install with uv sync --frozen in .github/workflows/test.yml
- [ ] T054 [US4] Update test execution to use uv run pytest in .github/workflows/test.yml
- [ ] T055 [US4] Add uv lock --check validation step to .github/workflows/test.yml
- [ ] T056 [US4] Configure matrix testing for Python 3.12 and 3.13 in .github/workflows/test.yml
- [ ] T057 [US4] Trigger CI pipeline and verify it completes successfully
- [ ] T058 [US4] Benchmark cold cache installation time (first run)
- [ ] T059 [US4] Benchmark warm cache installation time (subsequent runs)
- [ ] T060 [US4] Verify warm cache installation completes in <1 minute (SC-004 target)
- [ ] T061 [US4] Validate T049 test now PASSES with CI configured

**Checkpoint**: CI/CD uses UV with caching, installation completes in <1 minute

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, documentation, and community engagement

- [ ] T062 [P] Create GitHub Discussion for UV migration feedback and community input
- [ ] T063 [P] Update CHANGELOG.md with UV migration details for version 0.2.0
- [ ] T064 [P] Create migration announcement document in specs/003-uv-package-manager/announcement.md
- [ ] T065 Run full migration contract validation (all PMR, MER, PVR requirements)
- [ ] T066 Validate all success criteria from spec.md are met
- [ ] T067 Validate all constitution principles remain satisfied
- [ ] T068 Final review of all documentation for accuracy and completeness
- [ ] T069 Sign off on migration contract in specs/003-uv-package-manager/contracts/migration-contract.md
- [ ] T070 Create PR with UV migration for team review

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User Story 1 (P1): Can start after Foundational - No dependencies on other stories
  - User Story 2 (P2): Can start after Foundational - No dependencies on other stories
  - User Story 3 (P3): Can start after Foundational - No dependencies on other stories
  - User Story 4 (P4): Depends on User Story 1 (README/docs) being complete for reference
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

```
Foundational (Phase 2)
  ├─> User Story 1 (P1) - Environment Setup [INDEPENDENT]
  ├─> User Story 2 (P2) - Dependency Management [INDEPENDENT]
  ├─> User Story 3 (P3) - Reproducibility [INDEPENDENT]
  └─> User Story 4 (P4) - CI/CD [depends on US1 for documentation reference]
```

### Within Each User Story

1. **Tests FIRST** - Write tests that FAIL
2. **Implementation** - Complete implementation tasks
3. **Validation** - Verify tests now PASS
4. **Checkpoint** - Story is independently functional

### Parallel Opportunities

**Phase 1 - Setup**: All tasks can run in parallel
- T002 [P] - Create __init__.py (independent)

**Phase 2 - Foundational**: Some parallelism
- T006-T007 can run sequentially (version update, then lock generation)
- T009 [P] can run independently after T007

**Phase 3 - User Story 1**: High parallelism
- T010, T011, T012 [P] - All test files can be created in parallel
- T014, T015 [P] - README sections can be written in parallel
- Manual testing (T019-T021) can run in parallel if multiple machines available

**Phase 4 - User Story 2**: High parallelism
- T023, T024, T025 [P] - All test methods can be written in parallel

**Phase 5 - User Story 3**: High parallelism
- T036, T037, T038 [P] - All test files can be created in parallel
- T040-T042 can run in parallel if multiple platforms available

**Phase 6 - User Story 4**: Some parallelism
- T049, T050 [P] - Test creation independent

**Phase 7 - Polish**: High parallelism
- T062, T063, T064 [P] - All documentation tasks can run in parallel

### Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Create lock file generation test in tests/migration/test_uv_lock_generation.py"
Task: "Create environment setup test in tests/migration/test_environment_setup.py"
Task: "Create dependency parity test in tests/migration/test_dependency_parity.py"

# Launch all documentation updates together:
Task: "Update README.md with UV installation instructions"
Task: "Update README.md with quickstart setup steps"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

This delivers immediate value - new contributors can set up environment quickly:

1. Complete **Phase 1**: Setup (T001-T005) → Baseline captured
2. Complete **Phase 2**: Foundational (T006-T009) → Lock file generated
3. Complete **Phase 3**: User Story 1 (T010-T022) → Environment setup documented and tested
4. **STOP and VALIDATE**: Test User Story 1 independently on 3 platforms
5. **Deploy**: Merge to develop branch, announce to team

**Value**: New contributors experience 2x faster setup, <2 minute environment ready time

### Incremental Delivery

Each user story adds independent value:

1. **Foundation** (Phases 1-2) → Lock file exists, version bumped
2. **+ User Story 1** → Environment setup streamlined → **Deploy MVP**
3. **+ User Story 2** → Dependency management documented → **Deploy v2**
4. **+ User Story 3** → Reproducibility validated → **Deploy v3**
5. **+ User Story 4** → CI/CD optimized → **Deploy v4** (Full migration complete)
6. **+ Polish** → Community engaged, docs polished → **Release 0.2.0**

### Parallel Team Strategy

With multiple developers (after Foundational phase):

- **Developer A**: User Story 1 (Environment Setup - documentation focus)
- **Developer B**: User Story 2 (Dependency Management - documentation focus)
- **Developer C**: User Story 3 (Reproducibility - testing focus)
- **Developer D**: User Story 4 (CI/CD - infrastructure focus)

Stories complete independently, then integrate smoothly.

### Recommended MVP Scope

**SHIP FIRST** (Minimum viable migration):
- Phase 1: Setup
- Phase 2: Foundational
- Phase 3: User Story 1 (Environment Setup)

**This delivers**:
- Lock file for reproducibility (foundational benefit)
- Fast environment setup for new contributors (user-facing benefit)
- Clear documentation for UV adoption (team benefit)
- ~22 tasks, ~2-3 days of work

**SHIP NEXT** (Incremental additions):
- User Story 2 (Dependency Management) - ~13 tasks, +1 day
- User Story 3 (Reproducibility) - ~13 tasks, +1 day
- User Story 4 (CI/CD) - ~13 tasks, +1 day
- Polish - ~9 tasks, +0.5 days

---

## Task Summary

| Phase | Story | Tasks | Parallelizable | Time Estimate |
|-------|-------|-------|----------------|---------------|
| Phase 1: Setup | N/A | 5 | 1 | 2 hours |
| Phase 2: Foundational | N/A | 4 | 1 | 1 hour |
| Phase 3: US1 Environment Setup | P1 | 13 | 6 | 1 day |
| Phase 4: US2 Dependency Mgmt | P2 | 13 | 3 | 1 day |
| Phase 5: US3 Reproducibility | P3 | 13 | 3 | 1 day |
| Phase 6: US4 CI/CD | P4 | 13 | 1 | 1 day |
| Phase 7: Polish | N/A | 9 | 3 | 4 hours |
| **Total** | **4 Stories** | **70** | **18** | **4-5 days** |

### Parallel Potential

- **18 tasks** marked [P] can run in parallel (26% of total)
- **4 user stories** can be developed in parallel after Foundational phase
- **MVP (US1 only)**: 22 tasks, ~2-3 days
- **Full migration**: 70 tasks, ~4-5 days (or 2 days with 4 parallel developers)

### Constitution Compliance

- ✅ **TDD (NON-NEGOTIABLE)**: 12 test tasks precede implementation
- ✅ **Documentation Excellence**: 15+ documentation tasks across README, CONTRIBUTING, quickstart
- ✅ **Simplicity & YAGNI**: Phased migration, each increment delivers value
- ✅ **Open Governance**: GitHub Discussion task (T062) for community feedback

---

## Notes

- **[P] tasks**: Different files, no dependencies, can run in parallel
- **[Story] label**: Maps task to specific user story for traceability
- **TDD mandate**: All test tasks MUST fail before implementation
- **Each user story**: Independently completable and testable
- **Checkpoints**: Stop after each phase to validate story works independently
- **File paths**: All paths are absolute or relative to repo root
- **Commit frequently**: After each task or logical group
- **Migration contract**: All tasks align with contracts/migration-contract.md validation criteria

---

## Next Steps

**To begin implementation**:
```bash
/speckit.implement
```

This will execute tasks in dependency order, running parallel tasks concurrently.

**To implement MVP only** (User Story 1):
Execute tasks T001-T022, then validate independently before proceeding.

**To test a single user story**:
Complete its phase, then run the checkpoint validation to confirm it works independently.
