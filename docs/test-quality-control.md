# Test Cases Tips And Guidelines (Living Notes)

This page is intentionally lightweight.

Use it as a running collection of what works, what broke before, and what we want to keep doing in tests. We can keep adding notes here as we discover patterns.

Later, when this is stable, we can convert it into a stricter global standard.

## How To Use This Page

- Add new findings as short tips.
- Include one good example when possible.
- Prefer practical guidance over formal policy language.
- If a tip turns out wrong, update or remove it.

## Current Tips Index

- [Assertion messages should show real observed values.](#assertion-messages-should-show-real-observed-values)
- [Avoid executing functions directly inside assert statements.](#avoid-executing-functions-directly-inside-assert-statements)
- [For CLI exit code checks, always include command output.](#for-cli-exit-code-checks-always-include-command-output)
- [For output substring checks, report full output in got.](#for-output-substring-checks-report-full-output-in-got)
- [Keep tests aligned with actual product behavior.](#keep-tests-aligned-with-actual-product-behavior)
- [Use CliRunner only for Click commands.](#use-clirunner-only-for-click-commands)
- [For boolean assertions, describe expected behavior from the execution source.](#for-boolean-assertions-describe-the-expected-behavior-from-the-execution-source)
- [Reuse a named expected variable (for example target_value).](#reuse-a-named-expected-variable-for-example-target_value)
- [For membership checks, show the full collection in got (not the target literal).](#for-membership-checks-show-the-full-collection-in-got-not-the-target-literal)

## Current Tips

### Assertion messages should show real observed values

When an assertion fails, we should immediately see what actually came back.

Good:

```python
assert saved_data == test_data, f"expect result to be {test_data}, got {saved_data}"
```

Avoid:

```python
# Too abstract
f"expect x, got {x == y}"
```

Why this helps:

- Shows the concrete observed value when a test fails.
- Reduces time spent reproducing failures just to inspect values.
- Makes failure output useful in CI logs.

### Avoid executing functions directly inside assert statements

Calling a function directly inside an assertion or fallback message can execute it multiple times.
If that function is stateful, time-dependent, random, or has side effects, the assertion can become flaky or misleading.

Avoid:

```python
assert get_config() == expected, f"expect result to be {expected}, got {get_config()}"
```

Prefer:

```python
actual = get_config()
assert actual == expected, f"expect result to be {expected}, got {actual}"
```

Why this helps:

- The value under test is evaluated once.
- The failure message matches the exact value that was asserted.
- It avoids accidental side effects from repeated execution.

### For boolean assertions, describe the expected behavior from the execution source

Generic messages like "expect truthy value" or "expect falsy value" are often too vague.
For boolean checks, the fallback message should say what behavior was expected and from which execution result.

Avoid:

```python
assert not result, f"expect falsy value, got {result}"
```

Prefer:

```python
result = agent.run(prompt)
assert not result, f"expect agent.run returns no result, got {result}"
```

Another example:

```python
is_ready = runtime.initialize()
assert is_ready, f"expect runtime.initialize returns ready state True, got {is_ready}"
```

Why this helps:

- Makes intent explicit (what behavior is expected).
- Makes debugging faster (which execution produced the value).
- Avoids ambiguous "truthy/falsy" wording in failure output.

### Reuse a named expected variable (for example `target_value`)

When the expected object/value appears multiple times, define it once and reuse it.
This avoids copy/paste mistakes and keeps updates easy.

Avoid:

```python
assert result_payload == {"status": "ok", "count": 2}, (
    f"expect result to be {{'status': 'ok', 'count': 2}}, got {result_payload}"
)
```

Prefer:

```python
target_value = {"status": "ok", "count": 2}
assert result_payload == target_value, f"expect result to be {target_value}, got {result_payload}"
```

This pattern also works well for strings used in output checks:

```python
target_value = "Agent 'Test Agent' added successfully"
assert target_value in result.output, f"expect {target_value} in result.output, got {result.output}"
```

Why this helps:

- Single source of truth for expected values.
- Less noisy assertions.
- Safer refactoring when expected content changes.

### For membership checks, show the full collection in got (not the target literal)

When asserting that a specific value exists in a generated object or collection,
the fallback message should show the collection/object that was searched.

Avoid:

```python
assert "test_agent_2" in saved, f"expect 'test_agent_2' in saved, got {'test_agent_2'}"
```

Prefer:

```python
target_value = "test_agent_2"
assert target_value in saved, f"expect {target_value} in saved, got {saved}"
```

Why this helps:

- Shows the real container state when membership fails.
- Avoids misleading "got" values that only repeat the expected target.
- Makes debugging missing keys/items much faster.

### For CLI exit code checks, always include command output

This has been one of the most useful patterns for quick debugging.

```python
assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
```

And for failure expectations:

```python
assert result.exit_code != 0, f"expect cli exit code != 0, got {result.exit_code} with output: {result.output}"
```

Why this helps:

- Exit code alone is usually not enough to debug CLI failures.
- Including output captures the command's immediate error context.
- Makes local and CI failures easier to triage.

### For output substring checks, report full output in got

If we assert something is in command output, the fallback should print the full output, not a hardcoded literal.

Good:

```python
assert "Agent 'Test Agent' added successfully" in result.output, (
    f"expect \"Agent 'Test Agent' added successfully\" in result.output, got {result.output}"
)
```

Avoid:

```python
# Misleading: does not show real output
f"... got {'Agent ...'}"
```

Why this helps:

- Prevents false confidence from hardcoded literals in error messages.
- Shows exactly what the CLI returned at runtime.
- Speeds up mismatch diagnosis for output formatting/content issues.

### Keep tests aligned with actual product behavior

If implementation supports a behavior, tests should verify that behavior instead of an older assumption.

Example:

- If duplicate agent names produce suffixed IDs, test for the suffix behavior.
- Do not expect an "already exists" warning unless implementation rejects duplicates.

Why this helps:

- Prevents tests from encoding stale assumptions.
- Reduces noisy failures during intentional behavior changes.
- Keeps tests as reliable product documentation.

### Use CliRunner only for Click commands

Useful reminder from recent issues:

- Use CliRunner.invoke for Click commands and groups.
- For plain async helper functions, call them directly with await.

Why this helps:

- Avoids misuse errors like missing Click command metadata.
- Keeps test intent clear (CLI behavior vs helper behavior).
- Prevents brittle tests caused by incorrect test harness usage.

## Quick Checks We Can Run

```bash
# Find output assertions that still print a string literal in `got`
rg -n "in\s+[A-Za-z_][A-Za-z0-9_]*\.output,\s*f\"[^"]*got \{(?:'[^']*'|\"[^\"]*\")\}" tests/**/*cli*.py

# Review all CLI exit-code assertions
rg -n "assert .*exit_code.*" tests/**/*cli*.py
```

## Add New Notes Here

Template:

- Tip title
- Short context: what failed or what we observed.
- Recommended pattern (minimal code example).
- Why this helps (one line can be enough).

Keep entries short so this page stays easy to scan.
