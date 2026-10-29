"""Lazy, individually approved tools backed by import-free project metadata."""

from __future__ import annotations

import asyncio
import hashlib
import importlib
import importlib.abc
import importlib.machinery
import inspect
import json
import os
import re
import sys
import threading
import types
import typing
from collections import OrderedDict
from pathlib import Path
from typing import Any, Callable

from pydantic import ConfigDict, Field, create_model

from miminions.tools import ToolSchema, create_tool
from miminions.workspace_fs.discovery import FunctionMetadata, ProjectContext, project_key, scan_project, source_bytes

_execution_lock = threading.Lock()


async def _thread(func, *args, **kwargs):
    """Keep process settings stable until a cancelled synchronous operation exits."""
    task = asyncio.create_task(asyncio.to_thread(func, *args, **kwargs))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        try:
            await asyncio.shield(task)
        except Exception:
            pass
        raise


def _safe_type(spec: dict) -> Any:
    kind = spec["kind"]
    if kind == "list":
        return list[_safe_type(spec["items"])]
    if kind == "dict":
        return dict[str, _safe_type(spec["items"])]
    if kind == "union":
        return typing.Union[tuple(_safe_type(member) for member in spec["items"])]
    return {"str": str, "int": int, "float": float, "bool": bool, "none": type(None), "any": Any}[kind]


class _SourceLoader(importlib.machinery.SourceFileLoader):
    """Use current source, never stale bytecode, for approved workspace imports."""

    def __init__(self, name, path, root, selected, data):
        super().__init__(name, path)
        self.root, self.selected, self.data = root, selected, data

    def get_code(self, fullname):
        path = Path(self.path).resolve()
        current = source_bytes(self.root, path.relative_to(self.root).as_posix())
        if path == self.selected and current != self.data:
            raise RuntimeError("Project source changed during module loading. Start a new turn and approve again.")
        data = self.data if path == self.selected else current
        return compile(data, self.path, "exec", dont_inherit=True)


class _ProjectFinder(importlib.abc.MetaPathFinder):
    def __init__(self, root, selected, data, module_name):
        self.root, self.selected, self.data, self.module_name = root, selected, data, module_name

    def find_spec(self, fullname, path=None, target=None):
        if fullname == self.module_name:
            source_bytes(self.root, self.selected.relative_to(self.root).as_posix())
            loader = _SourceLoader(fullname, str(self.selected), self.root, self.selected, self.data)
            options = {"submodule_search_locations": [str(self.selected.parent)]} if self.selected.name == "__init__.py" else {}
            return importlib.util.spec_from_file_location(fullname, self.selected, loader=loader, **options)
        spec = importlib.machinery.PathFinder.find_spec(fullname, path)
        if spec and spec.origin and spec.origin.endswith(".py"):
            origin = Path(spec.origin).resolve()
            if origin.is_relative_to(self.root):
                spec.loader = _SourceLoader(fullname, spec.origin, self.root, self.selected, self.data)
                return spec
        return None


class WorkspaceTools:
    """One turn's catalog; search changes visibility, never execution permission."""

    def __init__(self, project: ProjectContext, approval: Callable[[str], bool], cache_path: Path | None = None):
        self.project = project
        self.approval = approval
        self.cache_path = cache_path
        self.active: OrderedDict[str, None] = OrderedDict()

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Search local Python function metadata and activate matching tools. Does not import project code."""
        terms = set(re.findall(r"\w+", query.lower()))
        ranked = []
        for function in self.project.functions:
            text = f"{function.name} {function.path} {function.signature} {function.docstring}".lower()
            score = sum(3 if term in function.name.lower() else 1 for term in terms if term in text)
            if score or not terms:
                ranked.append((-score, function.path, function.line, function))
        results = []
        for *_, function in sorted(ranked, key=lambda item: item[:3])[:max(1, min(limit, 20))]:
            self.active.pop(function.tool_name, None)
            self.active[function.tool_name] = None
            results.append({"tool_name": function.tool_name, "source": f"{function.path}:{function.line}",
                            "signature": function.signature, "return_annotation": function.return_annotation,
                            "description": function.docstring[:2000]})
        while len(self.active) > 32:
            self.active.popitem(last=False)
        return results

    def register(self, minion) -> None:
        minion.register_tool("workspace_search_tools", "Search and activate project functions without importing code.", self.search)
        for function in self.project.functions:
            self._register_function(minion, function)

    def _register_function(self, minion, function: FunctionMetadata) -> None:
        fields, parameters, annotations = {}, [], {}
        for index, param in enumerate(function.parameters):
            annotation = _safe_type(param["type"])
            default = ... if param["required"] else param["default"]
            # Aliases allow ordinary function arguments such as model_config or model_dump.
            fields[f"argument_{index}"] = (annotation, Field(default, alias=param["name"]))
            annotations[param["name"]] = annotation
            parameters.append(inspect.Parameter(
                param["name"], inspect.Parameter.KEYWORD_ONLY if param["keyword_only"] else inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=inspect.Parameter.empty if param["required"] else default, annotation=annotation,
            ))
        validator = create_model(function.tool_name, __config__=ConfigDict(extra="forbid", validate_default=True), **fields)

        async def invoke(**kwargs):
            # Direct execution uses the same validation as model-driven execution.
            values = validator.model_validate(kwargs).model_dump(by_alias=True)
            return await self._invoke(function, values)

        invoke.__name__ = function.name
        invoke.__signature__ = inspect.Signature(parameters)
        invoke.__annotations__ = annotations
        schema = validator.model_json_schema()
        generic = create_tool(function.tool_name, function.docstring or function.signature, invoke, schema=ToolSchema(
            function.tool_name, function.docstring, schema.get("properties", {}), schema.get("required", []), schema,
        ))
        minion.add_tool(generic, enabled=lambda: function.tool_name in self.active)

    async def _invoke(self, function: FunctionMetadata, arguments: dict) -> Any:
        while not _execution_lock.acquire(blocking=False):
            await asyncio.sleep(0.01)
        try:
            prompt = (f"Execute project function {function.signature}\n"
                      f"Source: {self.project.root / function.path}:{function.line}\n"
                      f"Arguments: {json.dumps(arguments, ensure_ascii=True)}\n"
                      "This permits importing project modules and executing top-level code and side effects. "
                      "Python runs with your OS permissions, without a sandbox. Allow this invocation?")
            approved = await _thread(self.approval, prompt)
            if not approved:
                raise PermissionError("Project function execution was not approved")
            data = source_bytes(self.project.root, function.path)
            if hashlib.sha256(data).hexdigest() != function.digest:
                # Keep the live callable tied to its original signature; a new turn rebuilds it.
                scan_project(self.project.root, self.cache_path)
                raise RuntimeError("Project source changed after discovery. Start a new turn to refresh tools and approve again.")
            return await self._execute(function, data, arguments)
        finally:
            _execution_lock.release()

    async def _execute(self, function: FunctionMetadata, data: bytes, arguments: dict) -> Any:
        root = self.project.root
        selected = root / function.path
        relative = Path(function.path)
        if relative.parts[0] == "src":
            relative = Path(*relative.parts[1:])
        parts = list(relative.with_suffix("").parts)
        if parts[-1] == "__init__":
            parts.pop()
        prefix = f"_miminions_project_{project_key(root)}"
        module_name = ".".join([prefix, *parts])
        namespace = types.ModuleType(prefix)
        namespace.__path__ = [str(root / "src"), str(root)]
        namespace.__package__ = prefix
        finder = _ProjectFinder(root, selected, data, module_name)
        old_path, old_cwd = sys.path[:], Path.cwd()
        old_modules = dict(sys.modules)
        try:
            sys.modules[prefix] = namespace
            sys.path[:0] = [str(root / "src"), str(root)]
            sys.meta_path.insert(0, finder)
            os.chdir(root)
            importlib.invalidate_caches()

            def load():
                if module_name == prefix:
                    spec = importlib.util.spec_from_file_location(prefix, selected, submodule_search_locations=[str(root)])
                    spec.loader = _SourceLoader(prefix, str(selected), root, selected, data)
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[prefix] = module
                    spec.loader.exec_module(module)
                module = importlib.import_module(module_name)
                if Path(getattr(module, "__file__", "")).resolve() != selected:
                    raise ImportError(f"Loaded module does not match discovered source: {function.path}")
                target = getattr(module, function.name)
                if not inspect.isfunction(target) or target.__module__ != module_name:
                    raise TypeError("Discovered function is no longer a local Python function")
                return target

            target = await _thread(load)
            if inspect.iscoroutinefunction(target):
                return await target(**arguments)
            return await _thread(target, **arguments)
        finally:
            os.chdir(old_cwd)
            sys.path[:] = old_path
            if finder in sys.meta_path:
                sys.meta_path.remove(finder)
            for name, module in list(sys.modules.items()):
                origin = getattr(module, "__file__", None)
                if name == prefix or name.startswith(prefix + ".") or (
                    name not in old_modules and origin and Path(origin).resolve().is_relative_to(root)
                ):
                    sys.modules.pop(name, None)
                    if name in old_modules:
                        sys.modules[name] = old_modules[name]
