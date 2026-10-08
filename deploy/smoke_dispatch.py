"""Smoke-test source or frozen CLI dispatch without making model requests.

Usage: python deploy/smoke_dispatch.py path/to/miminions-cli
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def main():
    binary = str(Path(sys.argv[1]).resolve())
    with tempfile.TemporaryDirectory(prefix="miminions-dispatch-") as home:
        env = {**os.environ, "MIMINIONS_HOME": home, "OPENROUTER_API_KEY": "test-placeholder"}

        def run(*args, check=True):
            result = subprocess.run([binary, *args], env=env, capture_output=True, text=True,
                                    encoding="utf-8", timeout=45)
            if check and result.returncode:
                log = Path(home) / "execution-instance.log"
                diagnostics = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
                raise RuntimeError(f"CLI {args!r} failed (exit {result.returncode}):\n{result.stderr}\n{diagnostics}")
            return result

        try:
            result = run("tool", "execute", "cli_add", "--arguments", '{"a":2,"b":3}', "--detach")
            task_id = re.search(r"Task (exec_[a-f0-9]+) accepted", result.stderr).group(1)
            # The submitting process has exited. Its worker must still function.
            events = [json.loads(line) for line in run("task", "tail", task_id, "--json").stdout.splitlines()]
            assert events[-1]["type"] == "completed", events
            assert any("Result: 5" in e["data"].get("text", "") for e in events)
            result = run("tool", "execute", "cli_add", "--arguments", '{"a":3,"b":4}')
            assert "Result: 7" in result.stdout
            assert "accepted" in result.stderr and "completed" in result.stderr
            print("Dispatch smoke test passed.")
        finally:
            run("instance", "stop", "--cancel", check=False)
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                state = json.loads(run("instance", "status", "--json").stdout)
                if not state.get("healthy"):
                    break
                time.sleep(0.1)
            else:
                raise RuntimeError("Execution instance did not stop")


if __name__ == "__main__":
    main()
