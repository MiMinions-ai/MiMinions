# Minimal terminal experience: Rich + prompt_toolkit

Status: proposal only; implementation has not started.

## Goal

Add restrained terminal styling, spinners, real progress bars, live status updates,
and editable chat input with history and completion. Keep Click as the command
router and preserve execution, approval, streaming, and scripting behavior.

This document records repository findings, a proposed implementation, estimates,
expected output, and acceptance criteria. Estimates are planning ranges, not
measured implementation results.

## Verified current behavior

| Area | Finding | Evidence |
| --- | --- | --- |
| Dependencies | Click is declared; Rich and prompt_toolkit are not direct dependencies. | [pyproject.toml](../pyproject.toml) |
| Dependency source | requirements.txt delegates to project extras; do not duplicate dependency declarations there. | [requirements.txt](../requirements.txt) |
| Command loading | Root help uses lazy subcommand loading and deliberately avoids bootstrap and heavy imports. | [main.py](../src/miminions/interface/cli/main.py), [help tests](../tests/unit/interface/test_cli_lazy_help.py) |
| Chat input | The async chat loop currently calls synchronous `input("> ")`; blank input is ignored, and `/exit` and `/quit` end chat. | [chat.py](../src/miminions/interface/cli/operations/chat.py) |
| Chat lifecycle | Each message submits a durable `chat_turn`; exit queues detached session distillation if a turn was submitted. | [chat.py](../src/miminions/interface/cli/operations/chat.py), [chat tests](../tests/unit/interface/test_cli_chat.py) |
| Shared rendering | `follow_task` renders execution events for attached submissions and task tail. JSON replay bypasses human formatting. | [dispatch.py](../src/miminions/interface/cli/operations/dispatch.py), [task.py](../src/miminions/interface/cli/management/task.py) |
| Streams | Response/tool output goes to stdout; lifecycle, activity, errors, and approval guidance go to stderr. | [dispatch.py](../src/miminions/interface/cli/operations/dispatch.py), [CLI documentation](../docs/modules/cli.md) |
| Approval | Interactive approval requires stdin and stderr TTYs. Noninteractive followers print guidance and never approve automatically. | [dispatch.py](../src/miminions/interface/cli/operations/dispatch.py), [dispatch tests](../tests/unit/test_execution_dispatch.py) |
| Interruption | Interrupting attachment detaches, rather than cancelling execution. Exit codes are 0, 1, and 130. | [dispatch.py](../src/miminions/interface/cli/operations/dispatch.py) |
| Progress data | Events have an open string type and dictionary payload. Inspected execution producers emit phases and heartbeats, but no structured progress event. | [models.py](../src/miminions/system/execution/models.py), [handlers.py](../src/miminions/system/execution/handlers.py), [worker.py](../src/miminions/system/execution/worker.py) |
| Measurable work | `_tool_test` iterates a known list of tool names, providing a concrete first progress-bar use case. | [handlers.py](../src/miminions/system/execution/handlers.py) |
| Heartbeats | Quiet running tasks emit a responsiveness message after about five seconds; this is not evidence of model/tool progress. | [worker.py](../src/miminions/system/execution/worker.py) |
| State location | `get_config_dir` honors `MIMINIONS_HOME`; terminal history must not be written into the user's project. | [paths.py](../src/miminions/core/paths.py) |
| Standalone build | PyInstaller collects MiMinions submodules; new third-party terminal dependencies still need a frozen-build smoke check. | [miminions-cli.spec](../miminions-cli.spec) |

Observed baseline sizes: chat 176 lines, dispatch 132, prompt 57, dispatch tests
433, chat tests 79, and lazy-help tests 127. These are physical lines, including
comments and whitespace, and are not estimates of logic complexity.

## Proposed scope and defaults

### Included

- Rich for bold headings, dim metadata, restrained semantic colors, one live
  status region, spinner, and determinate progress display.
- prompt_toolkit for chat line editing, in-session history, Ctrl+R search, and
  Tab completion of the existing `/exit` and `/quit` commands.
- Real progress events for `tool test`, not fabricated percentages for model work.
- Plain fallbacks for redirected output and unsupported terminals.
- Regression tests and an update to the existing public CLI guide.

### Not included

- Full-screen TUI, alternate screen, panels everywhere, animated banners, sounds,
  artificial typewriter delays, or rewriting all management command output.
- Replacement of Click, execution scheduling, model streaming, or approval policy.
- Shell-wide completion, file-path completion, agent-name lookup, new slash
  commands, syntax highlighting, Markdown re-rendering, or multiline key bindings.
- Persistent input history by default. Chat already persists transcripts;
  introducing another disk copy of potentially sensitive prompts is unnecessary.
- Version bump.

The history and completion defaults above are recommendations awaiting approval,
not inferred final requirements. Persistent history can be considered separately
with explicit opt-in, storage permissions, retention, and deletion behavior.

## Architecture and implementation

### 1. Add two direct dependencies

Declare `rich` and `prompt-toolkit` in [pyproject.toml](../pyproject.toml).
Choose tested minimum versions during implementation, compatible with the
repository's supported Python range. Do not rely on transitive installation.

Keep these imports out of the root CLI startup path. Do not install or modify
dependencies merely to produce this plan.

### 2. Add one small terminal helper module

Proposed new file: `src/miminions/interface/cli/terminal.py`.

Keep the abstraction local and concrete: terminal capability selection, a chat
input factory, and an execution display. Avoid a plugin system or renderer tree.

Capability policy:

- Enhanced chat input requires stdin, stdout, and stderr to be TTYs and a
  supported terminal; otherwise retain the current `input` path.
- Live execution display also requires all three TTYs. This deliberately keeps
  piped invocations predictable, even when stderr remains attached to a terminal.
- `TERM=dumb` selects plain output. `NO_COLOR` disables colors and dim styling;
  it does not, by itself, mean "disable all interaction."
- Proposed `--plain` on `chat start` disables enhanced input and live effects for
  that chat session. One-shot commands retain automatic detection in this scope.
- Use ASCII markers/spinner initially, avoiding font and encoding assumptions.
- Render external text literally: never interpret model output, tool output,
  paths, approval text, or error messages as Rich markup.

### 3. Upgrade chat input without changing session semantics

Create one `PromptSession` per interactive chat with `InMemoryHistory`,
history search, and a `WordCompleter` limited to `/exit` and `/quit`.

Use `await prompt_async(...)` in the existing async loop. Keep Enter to submit,
Up/Down to recall, Ctrl+R to search, and Tab to complete. Avoid automatically
executing suggestions. Retain blank-input and EOF/Ctrl+C behavior.

Input editing runs only while waiting for the next message. Execution follows
after input returns, so no concurrent prompt and Rich live display is needed.
Approvals remain Click confirmations, with the live region suspended first.
No background prompt patching should be introduced unless testing proves a need.

History is in-memory only, scoped to this chat invocation, and not preloaded from
transcripts. It is not a security guarantee: submitted messages still follow
existing transcript and execution persistence behavior.

### 4. Integrate live rendering at the shared dispatch boundary

Keep JSON output and the existing plain event path separate from Rich rendering.
Preserve `_echo` and its Windows/broken-pipe behavior for raw output.

| Event | Enhanced presentation |
| --- | --- |
| Accepted / started | Keep acceptance acknowledgement and its ordering; begin queued/running status. |
| `phase` | Update the single live status message. |
| `heartbeat` | Indicate responsiveness without implying measured work or resetting elapsed time. |
| `retry` | Preserve a visible warning; update waiting status. |
| `tool_call` | Show activity; retain verbose argument behavior. |
| `text_delta`, `stdout`, `stderr` | Clear/suspend live output before raw writes; never style or buffer payloads. |
| `approval_requested` | Suspend live output, perform existing confirmation, then resume if still running. |
| `turn_end` | Retain verbose usage and latency reporting. |
| `progress` | Update a bar only from valid completed/total counts. |
| Terminal event | Stop live output and print a durable completed/failed/cancelled line. |

Two streams can address the same terminal. Do not assume a Rich stderr console
automatically coordinates raw stdout writes. Stop the transient region before
streaming begins; leave it off during contiguous text output. Resume only on a
later phase/tool event when the output is at a safe line boundary. Never insert
newlines into response payloads just to accommodate decoration.

Use context-manager/finally cleanup so interrupts, EOF, approval aborts, broken
pipes, and renderer errors do not leave a spinner or hidden cursor behind.
Preserve the detach message and return codes; do not cancel tasks on UI teardown.

### 5. Add truthful progress to the existing tool-test batch

Proposed additive event:

```json
{"type": "progress", "data": {"label": "Testing tools", "completed": 2, "total": 5}}
```

The actual persisted event retains the existing envelope with task ID, sequence,
and timestamp. No database migration or dataclass shape change is expected.

- Emit initial `0/N` and one update after each attempted tool finishes.
- Count failed tool attempts as processed work, not successful work. A full bar
  does not override the existing failed terminal result.
- For zero tools, show "No tools to test"; never divide by zero.
- For unknown totals, use a spinner. Never turn heartbeats, tokens, or elapsed
  time into a percentage.
- Validate progress counts at the producer/helper boundary. Malformed progress
  must produce an explicit diagnostic rather than a misleading bar.
- Plain followers receive concise progress lines; this is an intentional
  additive human-output change. JSON followers receive the new events unchanged.
- Older event streams without progress remain fully supported.

This is the only proposed execution-layer behavior addition. Do not introduce a
general progress protocol across every provider or tool in the first iteration.

## Estimated changes

"Lines" below means added or materially edited physical lines, not net file
growth, unchanged context, mechanical reformatting, or representation-only edits.
Ranges include small integration adjustments but not optional future features.

| File / change surface | Estimated lines | Logic units |
| --- | ---: | ---: |
| New terminal helper: capabilities, input, display lifecycle | 140-210 | 7 |
| Existing dispatch: select display, route events, preserve cleanup | 45-75 | 5 |
| Existing chat: input selection, async prompt, `--plain` | 25-45 | 3 |
| Existing handlers: tool-test progress events | 10-20 | 2 |
| Dependency declarations | 2 | 0 |
| Existing help test: guard terminal imports on root help | 10-20 | 0 |
| Existing chat tests: enhanced and fallback input | 65-100 | 0 |
| Existing dispatch tests: display and compatibility cases | 130-200 | 0 |
| Tool-test producer tests, preferably in an existing execution test file | 35-60 | 0 |
| Existing CLI guide | 35-60 | 0 |
| **Total** | **497-792** | **17** |

Production Python subtotal: **220-350 lines**; dependency metadata: **2 lines**;
tests: **240-380 lines**; public documentation: **35-60 lines**.
Approximately **9 files**, of which one is new, if producer tests fit the existing
execution test files. This planning document is excluded from implementation LOC.

"Logic unit" means one cohesive responsibility, not AST nodes, branch count,
cyclomatic complexity, or number of functions. The 17 units are:

1. Detect terminal capabilities and plain mode.
2. Select styling/ASCII policy.
3. Construct the prompt session and completion/history configuration.
4. Start and stop the transient display safely.
5. Update spinner/status and elapsed time.
6. Update determinate progress or empty-work display.
7. Suspend/resume around raw output and prompts.
8. Select JSON, plain, or enhanced dispatch.
9. Route lifecycle/activity events.
10. Preserve raw payload writes and safe line boundaries.
11. Coordinate approval display and existing confirmation.
12. Preserve terminal results, interruption, and broken-pipe cleanup.
13. Select chat input mode and expose `--plain`.
14. Await editable input and preserve blank/exit/interrupt semantics.
15. Preserve turn submission and distillation lifecycle with the new input path.
16. Emit initial and per-tool progress.
17. Handle zero tools and processed-versus-successful counts.

Estimate confidence is medium. Cross-stream redraw behavior is the largest
uncertainty. A packaging adjustment is contingent: allow another **5-15 lines**
if a frozen-build smoke check demonstrates missing imports or metadata.
Disk history and richer completion are not hidden in these estimates.

## Projected terminal results

These are illustrative mockups, not captured output. Color and dim text are
described rather than required for understanding.

### Interactive chat

```text
Workspace : my-project
Session   : 20261115T234200000000Z_a1b2c3d4
Enter to send | Up/Down history | Ctrl+R search | Tab complete
Type '/exit' or '/quit' to end the session.

> summarize this project
Task exec_... accepted; follow with miminions task tail exec_...
- Resolving workspace and context...  0.4s
```

The last line is transient. Once response text arrives, it disappears and raw
text streams immediately:

```text
This project provides an agent framework with...
[ok] Task exec_... completed.

> /ex
  /exit
```

Tab completes `/ex` to `/exit`; the completion menu appears only while editing.
Keep existing acceptance/task references available for troubleshooting.

### Measured tool testing

```text
Testing tools  [########------------] 2/5  40%  1.8s
```

Existing individual tool results remain on stdout. The bar is transient on
stderr; output writes suspend it. Final status remains explicit:

```text
[error] Task exec_... failed. 1 tool test(s) failed
```

### Approval and plain operation

The spinner clears before the existing approval prompt, whose default stays No.
Redirected/chat-plain operation keeps ordinary line-oriented input and output.
`task tail --json` remains newline-delimited event JSON, without styling,
spinners, prompt escape sequences, or extra human lines.

## Delivery order and verification gates

1. Add dependency declarations and the terminal helper; keep lazy help untouched.
2. Wire chat input and plain mode; verify session and distillation regressions.
3. Wire shared execution display; verify stream fidelity and failure paths.
4. Emit and render real tool-test progress; verify zero, success, and failed tools.
5. Update public CLI documentation and perform terminal/package smoke checks.

Planned focused validation command:

```bash
python -m pytest tests/unit/interface/test_cli_chat.py tests/unit/test_execution_dispatch.py tests/unit/interface/test_cli_lazy_help.py tests/unit/test_execution_stream_retry.py -q
```

If producer tests require another existing test file, add that exact file to the
same run. Use the repository environment; install missing dependencies only after
the manifest changes or an actual missing-dependency failure.

Then run the existing structural and lint gates:

```bash
python scripts/check_structure.py
ruff check --statistics src tests
```

Acceptance coverage:

- Prompt editing/history/completion via prompt_toolkit pipe input and dummy
  output, not merely a mocked `prompt_async` call.
- Non-TTY fallback; explicit plain mode; `NO_COLOR`; `TERM=dumb`.
- Blank input, both exit commands, EOF, Ctrl+C, failed turn continuation,
  resumed sessions, and one finalization submission.
- Exact stdout bytes across arbitrary delta boundaries and missing trailing
  newline; literal markup-like payloads; stderr separation.
- JSON replay envelope, ordering, and sequence cursor unchanged, apart from the
  intentionally added progress events on newly produced tool-test tasks.
- Approval suspension, default denial, noninteractive no-auto-approval, races.
- Progress initialization, each attempted tool, zero tools, invalid counts, and
  final failure despite a fully processed batch.
- Completion/failure/cancellation exit codes and broken-pipe detach behavior.
- Root help remains lazy and satisfies its existing warm-help timing assertion.
- Real pseudo-terminal smoke checks for rendering/cleanup on a narrow terminal,
  resizing, and interrupted streaming. Unit snapshots alone cannot prove this.
- macOS/Linux and Windows console checks before calling support complete.
- `python -m build` and standalone PyInstaller build/help/chat smoke checks in a
  suitable build environment. Do not preemptively alter the PyInstaller spec.

## Risks and decisions before implementation

1. Approve minimal completion and invocation-local history, or explicitly expand
   scope to persistent history/path completion.
2. Approve chat-local `--plain` versus a broader global terminal-mode option.
   The latter needs additional option propagation and a revised estimate.
3. Approve the additive tool-test progress events and their plain-text lines.
   Consumers must not assume a closed event-type enumeration.
4. Cross-stream rendering, terminal capability differences, and frozen packaging
   need runtime checks; they have not been verified by this planning exercise.
5. Keep all work frontend-local except the small tool-test progress producer.
   Unrelated existing issues found during reading are outside this plan.

## Work performed for this proposal

Inspected the CLI entry point, chat loop, dispatch renderer, tool execution
helpers, execution events/producers, heartbeat producer, state paths, dependency
metadata, packaging spec, structural checker, CLI documentation, and related tests.

No application code, dependencies, configuration, or versions were changed.
No tests, builds, dependency installation, terminal prototype, or benchmark was
run for this documentation-only proposal. The mockups, estimates, and proposed
event contract remain unimplemented.
