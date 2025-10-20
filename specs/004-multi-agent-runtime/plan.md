# Implementation Plan: Multi-Agent Runtime System

**Branch**: `004-multi-agent-runtime` | **Date**: 2025-10-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-multi-agent-runtime/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Build a multi-agent runtime system that enables concurrent execution of multiple AI agents with robust task queue management, agent lifecycle control (start/stop/pause/resume), inter-agent communication, and configurable resource limits. The system must support at least 10 concurrent agents, provide real-time status monitoring, handle agent failures gracefully with complete isolation, and maintain <100ms message delivery latency. Core architecture will use Python asyncio for concurrency, SQLite for local state persistence (aligned with local-first principle), and a priority-based task queue with dependency management.

## Technical Context

**Language/Version**: Python 3.12+ (per project standards)
**Primary Dependencies**:
- Core: asyncio (stdlib), threading, multiprocessing
- Data: pydantic (validation), SQLite (state persistence)
- Existing: fastmcp, openai-agents integration layer
- Optional: NEEDS CLARIFICATION (monitoring, distributed execution)

**Storage**: SQLite for local persistence (agent state, task queue, event logs) - aligns with local-first architecture
**Testing**: pytest with pytest-asyncio for async tests, 80% coverage target per TDD principle
**Target Platform**: Local executable Python package (Linux/macOS/Windows) - fully offline capable
**Project Type**: Single project (library + optional CLI)
**Performance Goals**:
- 10+ concurrent agents without degradation
- <100ms inter-agent message delivery (p95)
- Task queue processes 100 tasks in <60 seconds
- <1s latency for real-time status queries

**Constraints**:
- Must work completely offline (cloud features optional only)
- Memory usage within configured per-agent limits (enforced)
- Agent isolation: zero impact from crashes (required for FR-005, FR-015)
- Graceful degradation without optional dependencies

**Scale/Scope**:
- 10+ concurrent agents (SC-001)
- Task queue supporting 100+ tasks with priorities and dependencies
- Event log for full audit trail (FR-012)
- Production-ready with zero critical concurrency bugs after 1 month testing (SC-010)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md`:

- [x] **Local-First Architecture**: ✓ PASS - SQLite local storage, fully offline capable, no mandatory cloud dependencies
- [x] **Framework Agnostic**: ✓ PASS - Integrates with fastmcp/openai-agents but core runtime is standalone; agents can use any framework
- [x] **Optional Dependencies**: ✓ PASS - Core uses stdlib (asyncio, threading, sqlite3) + minimal deps (pydantic); monitoring/distributed features will be optional extras
- [x] **TDD (NON-NEGOTIABLE)**: ✓ PASS - Test plan required in Phase 1, tests written before implementation per Red-Green-Refactor cycle, 80% coverage target
- [x] **Documentation Excellence**: ✓ PASS - All public runtime APIs will have docstrings, quickstart.md with examples in Phase 1, CLI help text
- [x] **Open Governance**: ✓ PASS - New feature (no breaking changes), will follow PR review process
- [x] **Semantic Versioning**: ✓ PASS - MINOR version bump (new feature, backwards compatible, e.g., 0.1.0 -> 0.2.0)
- [x] **Simplicity & YAGNI**: ✓ PASS - Complexity justified by 5 prioritized user stories in spec.md with clear acceptance criteria and real user needs (concurrent execution, task management, lifecycle control)

**Gate Status**: ✅ ALL GATES PASS - Proceed to Phase 0

**Phase 1 Re-Evaluation**: ✅ ALL GATES STILL PASS
- Local-first: Confirmed via SQLite schema in research.md
- Framework agnostic: Confirmed via BaseAgent + AgentProtocol in agent-interface.md
- Optional dependencies: Confirmed via monitoring extras in research.md
- TDD: Test examples provided in quickstart.md, tests to be written before implementation
- Documentation: Comprehensive contracts, data model, and quickstart completed
- Simplicity: Design maintains focus on justified user needs from spec.md

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
├── runtime/
│   ├── __init__.py
│   ├── agent_runtime.py      # Main AgentRuntime class (runtime-api.md)
│   ├── task_queue.py          # Priority queue + dependency management
│   ├── message_bus.py         # Inter-agent communication (messaging-api.md)
│   ├── agent_supervisor.py    # Process management and monitoring
│   └── resource_manager.py    # Resource limits enforcement
│
├── agents/
│   ├── __init__.py
│   ├── base.py                # BaseAgent class (agent-interface.md)
│   ├── protocol.py            # AgentProtocol interface
│   └── context.py             # AgentContext injected into agents
│
├── models/
│   ├── __init__.py
│   ├── agent.py               # AgentInstance, AgentStatus
│   ├── task.py                # Task, TaskStatus, TaskDependency
│   ├── message.py             # AgentMessage
│   ├── event.py               # EventLog, EventType, Severity
│   ├── runtime_state.py       # RuntimeState, RuntimeStatus
│   └── resource_limit.py      # ResourceLimit
│
├── storage/
│   ├── __init__.py
│   ├── database.py            # SQLite connection and schema
│   ├── migrations/            # Schema migration scripts
│   │   └── 001_initial.sql
│   └── repositories/          # Data access layer
│       ├── agent_repo.py
│       ├── task_repo.py
│       └── event_repo.py
│
└── utils/
    ├── __init__.py
    ├── logger.py              # Logging configuration
    ├── metrics.py             # Optional metrics (requires [monitoring] extra)
    └── exceptions.py          # Custom exceptions

tests/
├── contract/                  # API contract tests (verify interfaces)
│   ├── test_runtime_api.py
│   ├── test_agent_interface.py
│   └── test_messaging_api.py
│
├── integration/               # Multi-component integration tests
│   ├── test_agent_execution.py
│   ├── test_task_dependencies.py
│   ├── test_inter_agent_messaging.py
│   └── test_lifecycle_management.py
│
└── unit/                      # Unit tests for individual components
    ├── test_task_queue.py
    ├── test_message_bus.py
    ├── test_agent_supervisor.py
    ├── test_resource_manager.py
    └── test_models.py
```

**Structure Decision**: Single project structure selected (Option 1) because:
- Multi-agent runtime is a library component, not a standalone application
- No frontend/backend separation needed (pure Python library)
- Follows existing project structure: `src/miminions/` for code, `tests/` for tests
- Aligns with local-first principle (no client-server architecture required)
- Supports both library usage and optional CLI wrapper in future

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |

