"""Pydantic AI Agent Implementation"""

import asyncio
import inspect
import time
from typing import Any, Callable, Dict, List, Optional
from pathlib import Path

from pydantic_ai import Agent, Tool, RunContext
from pydantic_ai.models.test import TestModel
from mcp import StdioServerParameters

from ..tools import GenericTool
from ..tools.mcp_adapter import MCPToolAdapter
from ..memory.base_memory import BaseMemory
from ..utils.chunker import TextChunker

from .models import (
    AgentConfig, AgentState, ExecutionStatus, MemoryEntry, MemoryQueryResult,
    ParameterType, ToolDefinition, ToolExecutionRequest, ToolExecutionResult,
    ToolParameter, ToolSchema,
)


def _python_type_to_param_type(py_type: type) -> ParameterType:
    """Map Python type to ParameterType."""
    mapping = {
        int: ParameterType.INTEGER, float: ParameterType.NUMBER,
        bool: ParameterType.BOOLEAN, str: ParameterType.STRING,
        list: ParameterType.ARRAY, dict: ParameterType.OBJECT,
    }
    return mapping.get(py_type, ParameterType.STRING)


def _extract_schema(func: Callable) -> ToolSchema:
    """Extract ToolSchema from function signature."""
    params = []
    for name, p in inspect.signature(func).parameters.items():
        py_type = p.annotation if p.annotation != inspect.Parameter.empty else str
        has_default = p.default != inspect.Parameter.empty
        params.append(ToolParameter(
            name=name,
            type=_python_type_to_param_type(py_type),
            description=name,
            required=not has_default,
            default=p.default if has_default else None,
        ))
    return ToolSchema(parameters=params)


class RegisteredTool:
    """Internal tool wrapper for direct execution."""
    def __init__(self, definition: ToolDefinition, func: Callable):
        self.definition = definition
        self.func = func

    def execute(self, **kwargs) -> Any:
        return self.func(**kwargs)

    async def execute_async(self, **kwargs) -> Any:
        result = self.func(**kwargs)
        return await result if asyncio.iscoroutine(result) else result


class PydanticAgent:
    """
    Pydantic AI-based agent implementation.
    
    Uses pydantic_ai infrastructure for LLM-ready tool management.
    Currently operates in direct execution mode (no LLM) but structured
    for easy LLM integration by replacing TestModel with a real model.
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        memory: Optional[BaseMemory] = None,
        chunk_size: int = 800,
        overlap: int = 150,
        model: Optional[Any] = None,
    ):
        self.config = AgentConfig(name=name, description=description, chunk_size=chunk_size, overlap=overlap)
        self._tools: Dict[str, RegisteredTool] = {}
        self._memory = memory
        self._mcp_adapter = MCPToolAdapter()
        self._connected_servers: Dict[str, StdioServerParameters] = {}
        self._chunker = TextChunker(chunk_size=chunk_size, overlap=overlap)
        
        # Replace TestModel with real model for LLM support
        self._model = model or TestModel()
        self._pydantic_ai_agent: Optional[Agent] = None
        self._pydantic_ai_tools: List[Tool] = []
        
        if self._memory:
            self._register_memory_tools()

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def description(self) -> str:
        return self.config.description

    @property
    def memory(self) -> Optional[BaseMemory]:
        return self._memory

    def get_state(self) -> AgentState:
        return AgentState(
            config=self.config,
            tool_count=len(self._tools),
            has_memory=self._memory is not None,
            connected_servers=list(self._connected_servers.keys()),
        )
    
    def _rebuild_pydantic_ai_agent(self) -> None:
        """Rebuild the pydantic_ai Agent with current tools."""
        self._pydantic_ai_agent = Agent(
            model=self._model,
            tools=self._pydantic_ai_tools,
            instructions=self.config.description or f"Agent: {self.config.name}",
        )
    
    # tool management
    def register_tool(self, name: str, description: str, func: Callable, schema: Optional[ToolSchema] = None) -> ToolDefinition:
        """Register a tool with the agent."""
        schema = schema or _extract_schema(func)
        definition = ToolDefinition(name=name, description=description, schema=schema)
        if name in self._tools:
            print(f"Warning: Replacing existing tool '{name}'")
            # Remove old tool from pydantic_ai tools
            self._pydantic_ai_tools = [t for t in self._pydantic_ai_tools if t.name != name]
        
        self._tools[name] = RegisteredTool(definition=definition, func=func)
        
        pydantic_ai_tool = Tool(func, name=name, description=description, takes_ctx=False)
        self._pydantic_ai_tools.append(pydantic_ai_tool)
        
        return definition

    def add_function_as_tool(self, name: str, description: str, func: Callable) -> ToolDefinition:
        """Alias for register_tool."""
        return self.register_tool(name, description, func)

    def add_tool(self, tool: GenericTool) -> ToolDefinition:
        """Add a GenericTool."""
        params = []
        if hasattr(tool, 'schema') and tool.schema:
            type_map = {
                "string": ParameterType.STRING, "integer": ParameterType.INTEGER,
                "number": ParameterType.NUMBER, "boolean": ParameterType.BOOLEAN,
                "array": ParameterType.ARRAY, "object": ParameterType.OBJECT,
            }
            for pname, pinfo in tool.schema.parameters.items():
                params.append(ToolParameter(
                    name=pname,
                    type=type_map.get(pinfo.get("type", "string"), ParameterType.STRING),
                    description=pinfo.get("description", pname),
                    required=pname in tool.schema.required,
                    default=pinfo.get("default"),
                ))
        return self.register_tool(tool.name, tool.description, tool.run, ToolSchema(parameters=params))

    def unregister_tool(self, name: str) -> bool:
        """Remove a tool by name."""
        if name in self._tools:
            del self._tools[name]
            self._pydantic_ai_tools = [t for t in self._pydantic_ai_tools if t.name != name]
            return True
        return False

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self._tools[name].definition if name in self._tools else None

    def list_tools(self) -> List[str]:
        return list(self._tools.keys())

    def get_tool_definitions(self) -> List[ToolDefinition]:
        return [t.definition for t in self._tools.values()]

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """Get JSON-serializable schemas for LLM tool calling."""
        return [t.definition.to_dict() for t in self._tools.values()]

    def get_tool_info(self, name: str) -> Optional[Dict[str, Any]]:
        tool = self._tools.get(name)
        if not tool:
            return None
        return {
            "name": tool.definition.name,
            "description": tool.definition.description,
            "schema": tool.definition.to_dict(),
            "parameters": tool.definition.schema_def.to_json_schema(),
        }

    def search_tools(self, query: str) -> List[str]:
        q = query.lower()
        return [n for n, t in self._tools.items() if q in n.lower() or q in t.definition.description.lower()]

    # execution
    def execute(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None, **kwargs) -> ToolExecutionResult:
        """Execute a tool and return structured result."""
        args = {**(arguments or {}), **kwargs}
        if tool_name not in self._tools:
            return ToolExecutionResult.from_error(tool_name, f"Tool '{tool_name}' not found")

        tool = self._tools[tool_name]
        start = time.time()
        try:
            result = tool.execute(**args)
            if asyncio.iscoroutine(result):
                return ToolExecutionResult.from_error(tool_name, "Async tool - use execute_async()")
            return ToolExecutionResult.success(tool_name, result, (time.time() - start) * 1000)
        except Exception as e:
            return ToolExecutionResult.from_error(tool_name, str(e), (time.time() - start) * 1000)

    async def execute_async(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None, **kwargs) -> ToolExecutionResult:
        """Execute a tool asynchronously."""
        args = {**(arguments or {}), **kwargs}
        if tool_name not in self._tools:
            return ToolExecutionResult.from_error(tool_name, f"Tool '{tool_name}' not found")

        tool = self._tools[tool_name]
        start = time.time()
        try:
            result = await tool.execute_async(**args)
            return ToolExecutionResult.success(tool_name, result, (time.time() - start) * 1000)
        except Exception as e:
            return ToolExecutionResult.from_error(tool_name, str(e), (time.time() - start) * 1000)

    def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """Execute tool and return raw result (raises exceptions on error)."""
        if tool_name not in self._tools:
            raise ValueError(f"Tool '{tool_name}' not found")
        try:
            result = self._tools[tool_name].execute(**kwargs)
            if asyncio.iscoroutine(result):
                raise RuntimeError("Async tool - use execute_tool_async()")
            return result
        except Exception as e:
            raise RuntimeError(f"Error executing '{tool_name}': {e}")

    async def execute_tool_async(self, tool_name: str, **kwargs) -> Any:
        """Execute tool asynchronously and return raw result."""
        if tool_name not in self._tools:
            raise ValueError(f"Tool '{tool_name}' not found")
        try:
            return await self._tools[tool_name].execute_async(**kwargs)
        except Exception as e:
            raise RuntimeError(f"Error executing '{tool_name}': {e}")

    def execute_request(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """Execute from a ToolExecutionRequest (for LLM integration)."""
        return self.execute(request.tool_name, request.arguments)

    # memory
    def _register_memory_tools(self) -> None:
        """Register memory CRUD tools."""
        self.register_tool("memory_store", "Store knowledge", self._memory_store)
        self.register_tool("memory_recall", "Recall knowledge", self._memory_recall)
        self.register_tool("memory_update", "Update knowledge", self._memory_update)
        self.register_tool("memory_delete", "Delete knowledge", self._memory_delete)
        self.register_tool("memory_get", "Get by ID", self._memory_get)
        self.register_tool("memory_list", "List all", self._memory_list)
        self.register_tool("ingest_document", "Ingest document with chunking", self._ingest_document)

    def _memory_store(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        if not self._memory:
            raise ValueError("No memory attached")
        return self._memory.create(text, metadata)

    def _memory_recall(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if not self._memory:
            raise ValueError("No memory attached")
        return self._memory.read(query, top_k)

    def _memory_update(self, id: str, new_text: str) -> bool:
        if not self._memory:
            raise ValueError("No memory attached")
        return self._memory.update(id, new_text)

    def _memory_delete(self, id: str) -> bool:
        if not self._memory:
            raise ValueError("No memory attached")
        return self._memory.delete(id)

    def _memory_get(self, id: str) -> Optional[Dict[str, Any]]:
        if not self._memory:
            raise ValueError("No memory attached")
        return self._memory.get_by_id(id) if hasattr(self._memory, 'get_by_id') else None

    def _memory_list(self) -> List[Dict[str, Any]]:
        if not self._memory:
            raise ValueError("No memory attached")
        return self._memory.list_all() if hasattr(self._memory, 'list_all') else []

    def _ingest_document(self, filepath: str, chunk_size: Optional[int] = None, overlap: Optional[int] = None) -> Dict[str, Any]:
        """Ingest a document (PDF or text) into memory."""
        if not self._memory:
            raise ValueError("No memory attached")

        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        ext = path.suffix.lower()
        if ext == '.pdf':
            text = self._extract_pdf(filepath)
            file_type = 'pdf'
        elif ext in ['.txt', '.md', '.text']:
            text = path.read_text(encoding='utf-8')
            file_type = 'text'
        else:
            raise ValueError(f"Unsupported file type: {ext}")

        if not text.strip():
            return {"status": "error", "message": "No text extracted", "filepath": str(filepath), "chunks_stored": 0}

        chunker = TextChunker(
            chunk_size=chunk_size or self._chunker.chunk_size,
            overlap=overlap or self._chunker.overlap,
        ) if chunk_size or overlap else self._chunker

        metadata = {"source": str(filepath), "filename": path.name, "file_type": file_type}
        chunks = chunker.chunk_text(text, metadata=metadata)
        chunk_ids = [self._memory.create(c["text"], c["metadata"]) for c in chunks]

        return {
            "status": "success", "message": f"Ingested {path.name}", "filepath": str(filepath),
            "file_type": file_type, "total_characters": len(text), "chunks_stored": len(chunks),
            "chunk_ids": chunk_ids, "chunk_size": chunker.chunk_size, "overlap": chunker.overlap,
        }

    def _extract_pdf(self, filepath: str) -> str:
        try:
            import pdfplumber
        except ImportError:
            raise ImportError("pdfplumber required: pip install pdfplumber")
        parts = []
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                if text := page.extract_text():
                    parts.append(text)
        return "\n\n".join(parts)

    def set_memory(self, memory: BaseMemory) -> None:
        """Attach memory and register tools."""
        self._memory = memory
        self._register_memory_tools()

    def get_memory_context(self, query: str, top_k: int = 5) -> MemoryQueryResult:
        """Get memory context as structured result."""
        if not self._memory:
            return MemoryQueryResult.empty(query, "No memory attached")
        raw = self._memory.read(query, top_k=top_k)
        if not raw:
            return MemoryQueryResult.empty(query)
        entries = [MemoryEntry(id=r.get("id", ""), text=r.get("text", ""), metadata=r.get("meta", {})) for r in raw]
        return MemoryQueryResult(query=query, results=entries, count=len(entries))

    def store_knowledge(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        return self._memory_store(text, metadata)

    def recall_knowledge(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        return self._memory_recall(query, top_k)

    # mcp inqtegration
    async def connect_mcp_server(self, server_name: str, server_params: StdioServerParameters) -> None:
        await self._mcp_adapter.connect_to_server(server_name, server_params)
        self._connected_servers[server_name] = server_params
        print(f"Connected to MCP server: {server_name}")

    async def load_tools_from_mcp_server(self, server_name: str) -> List[ToolDefinition]:
        if server_name not in self._connected_servers:
            raise ValueError(f"Server '{server_name}' not connected")
        tools = await self._mcp_adapter.load_all_tools_from_server(server_name)
        defs = [self.add_tool(t) for t in tools]
        print(f"Loaded {len(tools)} tools from: {server_name}")
        return defs

    async def load_tools_from_all_servers(self) -> List[ToolDefinition]:
        defs = []
        for name in self._connected_servers:
            defs.extend(await self.load_tools_from_mcp_server(name))
        return defs

    # cleanup
    async def cleanup(self) -> None:
        await self._mcp_adapter.close_all_connections()

    def get_pydantic_ai_agent(self) -> Agent:
        """Get the underlying pydantic_ai Agent for LLM operations. Use for when integrating with an LLM."""
        self._rebuild_pydantic_ai_agent()
        return self._pydantic_ai_agent

    def set_model(self, model: Any) -> None:
        self._model = model
        self._rebuild_pydantic_ai_agent()

    def __str__(self) -> str:
        mem = "with memory" if self._memory else "no memory"
        model_name = getattr(self._model, 'model_name', 'test') if self._model else 'none'
        return f"PydanticAgent({self.name}, tools={len(self._tools)}, model={model_name}, {mem})"

    def __repr__(self) -> str:
        return self.__str__()


def create_pydantic_agent(
    name: str,
    description: str = "",
    memory: Optional[BaseMemory] = None,
    model: Optional[Any] = None,
) -> PydanticAgent:
    """
    Create a new PydanticAgent instance.
    
    Args:
        name: Agent name
        description: Agent description
        memory: Optional memory backend (FAISSMemory, SQLiteMemory)
        model: Optional pydantic_ai model. Defaults to TestModel (no LLM).
               Pass a real model like 'openai:gpt-4' for LLM support.
    
    Returns:
        PydanticAgent instance ready for tool registration and execution
    """
    return PydanticAgent(name=name, description=description, memory=memory, model=model)
