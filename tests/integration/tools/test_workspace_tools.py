"""Lazy search, validated execution, and durable approval integration."""

import asyncio
import json
import os
import py_compile
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.models.test import TestModel

from miminions.agent import create_minion
from miminions.execution import ExecutionRequest
from miminions.execution.handlers import TaskContext
from miminions.execution.store import ExecutionStore
from miminions.tools.workspace import WorkspaceTools
from miminions.workspace_fs.discovery import scan_project


def runtime(tmp_path, source, approval=None, relative="main.py"):
    project = tmp_path / "project"
    path = project / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    approval = approval or Mock(return_value=True)
    tools = WorkspaceTools(scan_project(project), approval)
    agent = create_minion("Project", model=TestModel())
    tools.register(agent)
    return agent, tools, approval, path


async def test_search_is_import_free_and_enables_tools_for_next_model_step(tmp_path):
    agent, tools, approval, _ = runtime(tmp_path, '''
from pathlib import Path
Path('imported.txt').write_text('import side effect')
def calculate(a: int, b: int = 2) -> int:
    """Calculate the sum of two numbers."""
    return a + b
''')
    function = tools.project.functions[0]
    rounds = []
    def model(messages, info):
        names = [tool.name for tool in info.function_tools]
        rounds.append(names)
        if len(rounds) == 1:
            assert function.tool_name not in names
            return ModelResponse(parts=[ToolCallPart("workspace_search_tools", {"query": "calculate"})])
        if len(rounds) == 2:
            assert function.tool_name in names
            assert not (tools.project.root / "imported.txt").exists()
            return ModelResponse(parts=[ToolCallPart(function.tool_name, {"a": 4})])
        return ModelResponse(parts=[TextPart("The sum is 6.")])
    agent.set_model(FunctionModel(model))
    before_cwd, before_path = Path.cwd(), sys.path[:]
    assert await agent.run("Calculate the sum") == "The sum is 6."
    assert Path.cwd() == before_cwd and sys.path == before_path
    assert (tools.project.root / "imported.txt").exists()
    approval.assert_called_once()
    assert "top-level code" in approval.call_args.args[0]
    assert '"a": 4' in approval.call_args.args[0]
    await agent.cleanup(rebuild=False)


async def test_denial_and_invalid_arguments_never_import(tmp_path):
    approval = Mock(return_value=False)
    agent, tools, _, _ = runtime(tmp_path, "raise AssertionError('imported')\ndef work(count: int): return count", approval)
    name = tools.project.functions[0].tool_name
    invalid = await agent.execute_async(name, {"count": "invalid"})
    assert invalid.error and "validation" in invalid.error
    approval.assert_not_called()
    denied = await agent.execute_async(name, {"count": 1})
    assert "not approved" in denied.error
    approval.assert_called_once()
    await agent.cleanup(rebuild=False)


async def test_every_invocation_requires_approval_and_imports_current_source(tmp_path):
    agent, tools, approval, _ = runtime(tmp_path, "def work(value: int): return value + 1")
    name = tools.project.functions[0].tool_name
    assert (await agent.execute_async(name, {"value": 1})).result == 2
    assert (await agent.execute_async(name, {"value": 2})).result == 3
    assert approval.call_count == 2
    await agent.cleanup(rebuild=False)


async def test_changed_source_during_approval_is_rejected(tmp_path):
    agent, tools, approval, path = runtime(tmp_path, "def work(): return 'original'")
    def change(_):
        path.write_text("raise AssertionError('changed source imported')\ndef work(): return 'changed'", encoding="utf-8")
        return True
    approval.side_effect = change
    result = await agent.execute_async(tools.project.functions[0].tool_name)
    assert "source changed" in result.error
    await agent.cleanup(rebuild=False)


@pytest.mark.parametrize("layout", ["", "src/"])
async def test_packages_relative_absolute_imports_and_async_functions(tmp_path, layout):
    source = "from .helpers import add\nasync def report(rows: list[int], title: str | None = None):\n    return add(rows)"
    agent, tools, _, path = runtime(tmp_path, source, relative=f"{layout}reports/main.py")
    (path.parent / "__init__.py").write_text("PACKAGE = True", encoding="utf-8")
    (path.parent / "helpers.py").write_text("def add(rows): return sum(rows)", encoding="utf-8")
    result = await agent.execute_async(tools.project.functions[0].tool_name, {"rows": [2, 3]})
    assert result.error is None and result.result == 5
    schema = agent.get_tool_info(tools.project.functions[0].tool_name)["parameters"]
    assert schema["properties"]["rows"]["items"]["type"] == "integer"
    assert {"type": "null"} in schema["properties"]["title"]["anyOf"]
    assert schema["additionalProperties"] is False
    await agent.cleanup(rebuild=False)


async def test_import_errors_are_returned_without_retry(tmp_path):
    agent, tools, approval, _ = runtime(tmp_path, "import missing_project_dependency_123\ndef work(): return 1")
    result = await agent.execute_async(tools.project.functions[0].tool_name)
    assert "missing_project_dependency_123" in result.error
    approval.assert_called_once()
    await agent.cleanup(rebuild=False)


async def test_durable_approval_can_be_answered_without_attached_cli(tmp_path):
    store = ExecutionStore(tmp_path / "home")
    task_id = store.enqueue(ExecutionRequest("prompt", {}))
    context = TaskContext(store, store.claim())
    agent, tools, _, _ = runtime(tmp_path, "def work(): return 'approved'", context.approval)
    operation = asyncio.create_task(agent.execute_async(tools.project.functions[0].tool_name))
    try:
        async with asyncio.timeout(10):
            while not store.approvals(task_id):
                await asyncio.sleep(0.01)
        request = store.approvals(task_id)[0]
        assert not operation.done()
        store.approve(task_id, request["id"], True)
        assert (await operation).result == "approved"
        assert len([e for e in store.events(task_id) if e.type == "approval_requested"]) == 1
    finally:
        if not operation.done():
            store.finish(task_id, "cancelled")
            await operation
        await agent.cleanup(rebuild=False)


async def test_cancelled_pending_approval_never_imports(tmp_path):
    store = ExecutionStore(tmp_path / "home")
    task_id = store.enqueue(ExecutionRequest("prompt", {}))
    context = TaskContext(store, store.claim())
    agent, tools, _, _ = runtime(tmp_path, "raise AssertionError('imported')\ndef work(): return 1", context.approval)
    operation = asyncio.create_task(agent.execute_async(tools.project.functions[0].tool_name))
    async with asyncio.timeout(10):
        while not store.approvals(task_id):
            await asyncio.sleep(0.01)
    store.finish(task_id, "cancelled")
    result = await asyncio.wait_for(operation, 10)
    assert "cancelled" in result.error.lower()
    await agent.cleanup(rebuild=False)


async def test_search_limits_and_activation_are_bounded(tmp_path):
    source = "\n".join(f"def task_{i}(value: int): return value" for i in range(60))
    agent, tools, approval, _ = runtime(tmp_path, source)
    assert len(tools.search("task", 1000)) == 20
    for i in range(60):
        tools.search(f"task_{i}")
    assert len(tools.active) == 32
    approval.assert_not_called()
    await agent.cleanup(rebuild=False)


async def test_reserved_parameter_names_validate_and_preserve_defaults(tmp_path):
    agent, tools, _, _ = runtime(tmp_path, "def work(model_config: int, model_dump: str = 'ok'):\n    return [model_config, model_dump]")
    result = await agent.execute_async(tools.project.functions[0].tool_name, {"model_config": 3})
    assert result.error is None and result.result == [3, "ok"]
    schema = agent.get_tool_info(tools.project.functions[0].tool_name)["parameters"]
    assert set(schema["properties"]) == {"model_config", "model_dump"}
    await agent.cleanup(rebuild=False)


async def test_absolute_local_imports_ignore_stale_bytecode(tmp_path):
    agent, tools, _, path = runtime(tmp_path, "def work():\n    from helpers import answer\n    return answer()")
    helper = path.parent / "helpers.py"
    helper.write_text("def answer(): return 'old'", encoding="utf-8")
    py_compile.compile(str(helper), doraise=True)
    previous = helper.stat()
    helper.write_text("def answer(): return 'new'", encoding="utf-8")
    os.utime(helper, ns=(previous.st_atime_ns, previous.st_mtime_ns))
    before = sys.modules.get("helpers")
    result = await agent.execute_async(tools.project.functions[0].tool_name)
    assert result.error is None and result.result == "new"
    assert sys.modules.get("helpers") is before
    await agent.cleanup(rebuild=False)


async def test_project_root_package_functions(tmp_path):
    agent, tools, _, _ = runtime(tmp_path, "def work(): return 42", relative="__init__.py")
    result = await agent.execute_async(tools.project.functions[0].tool_name)
    assert result.error is None and result.result == 42
    await agent.cleanup(rebuild=False)


async def test_function_failure_restores_process_settings(tmp_path):
    agent, tools, approval, _ = runtime(tmp_path, "def work():\n    raise RuntimeError('project failure')")
    before_cwd, before_path, before_finders = Path.cwd(), sys.path[:], sys.meta_path[:]
    result = await agent.execute_async(tools.project.functions[0].tool_name)
    assert "project failure" in result.error
    assert Path.cwd() == before_cwd and sys.path == before_path and sys.meta_path == before_finders
    approval.assert_called_once()
    await agent.cleanup(rebuild=False)


async def test_parallel_project_calls_are_serialized(tmp_path):
    source = '''
import asyncio
from pathlib import Path
async def work(label: str):
    path = Path('order.txt')
    text = path.read_text() if path.exists() else ''
    path.write_text(text + label + ':start;')
    await asyncio.sleep(0.03)
    path.write_text(path.read_text() + label + ':end;')
    return label
'''
    agent, tools, approval, _ = runtime(tmp_path, source)
    name = tools.project.functions[0].tool_name
    results = await asyncio.gather(agent.execute_async(name, {"label": "a"}), agent.execute_async(name, {"label": "b"}))
    assert [r.result for r in results] == ["a", "b"]
    assert (tools.project.root / "order.txt").read_text() == "a:start;a:end;b:start;b:end;"
    assert approval.call_count == 2
    await agent.cleanup(rebuild=False)


async def test_package_import_cannot_replace_selected_source_before_loading(tmp_path):
    agent, tools, approval, path = runtime(tmp_path, "def work(): return 'original'", relative="pkg/main.py")
    (path.parent / "__init__.py").write_text(
        "from pathlib import Path\nPath(__file__).with_name('main.py').write_text(\"raise AssertionError('changed code executed')\")",
        encoding="utf-8",
    )
    result = await agent.execute_async(tools.project.functions[0].tool_name)
    assert "source changed" in result.error
    assert "changed code executed" not in result.error
    approval.assert_called_once()
    await agent.cleanup(rebuild=False)
