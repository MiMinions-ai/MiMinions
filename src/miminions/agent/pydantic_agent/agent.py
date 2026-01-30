"""
Pydantic Agent Implementation

This module provides the main PydanticAgent class that mirrors the Simple Agent's
capabilities but uses Pydantic models for strong typing and validation.

The agent supports:
- Tool registration with Pydantic schema validation
- Memory integration (same interface as Simple Agent)
- Deterministic tool execution
- MCP server integration

The architecture is designed to easily add an LLM later without refactoring:
- All inputs and outputs are Pydantic models
- Tool schemas are JSON-serializable for LLM consumption
- Execution is separated from any future reasoning loop
"""

import asyncio
import inspect
import time
from typing import Any, Callable, Dict, List, Optional, Union

from mcp import StdioServerParameters

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools import GenericTool, SimpleTool
from tools.mcp_adapter import MCPToolAdapter
from memory.base_memory import BaseMemory
from utils.chunker import TextChunker

from .models import (
    AgentConfig,
    AgentState,
    ExecutionStatus,
    MemoryEntry,
    MemoryQueryResult,
    ParameterType,
    ToolDefinition,
    ToolExecutionRequest,
    ToolExecutionResult,
    ToolParameter,
    ToolSchema,
)


def _python_type_to_parameter_type(python_type: type) -> ParameterType:
    """Convert Python type to ParameterType enum"""
    type_mapping = {
        int: ParameterType.INTEGER,
        float: ParameterType.NUMBER,
        bool: ParameterType.BOOLEAN,
        str: ParameterType.STRING,
        list: ParameterType.ARRAY,
        dict: ParameterType.OBJECT,
    }
    return type_mapping.get(python_type, ParameterType.STRING)


def _extract_tool_schema(func: Callable) -> ToolSchema:
    """Extract a ToolSchema from a function's signature"""
    sig = inspect.signature(func)
    parameters = []
    
    for param_name, param in sig.parameters.items():
        # Get type annotation
        param_type = param.annotation
        if param_type == inspect.Parameter.empty:
            param_type = str
        
        # Check if parameter has default value
        has_default = param.default != inspect.Parameter.empty
        
        tool_param = ToolParameter(
            name=param_name,
            type=_python_type_to_parameter_type(param_type),
            description=param_name,  # Could be enhanced with docstring parsing
            required=not has_default,
            default=param.default if has_default else None,
        )
        parameters.append(tool_param)
    
    return ToolSchema(parameters=parameters)


class RegisteredTool:
    """Internal representation of a registered tool with its Pydantic definition"""
    
    def __init__(self, definition: ToolDefinition, func: Callable):
        self.definition = definition
        self.func = func
    
    def execute(self, **kwargs) -> Any:
        """Execute the tool with provided arguments"""
        return self.func(**kwargs)
    
    async def execute_async(self, **kwargs) -> Any:
        """Execute the tool asynchronously"""
        result = self.func(**kwargs)
        if asyncio.iscoroutine(result):
            return await result
        return result


class PydanticAgent:
    """
    Pydantic-based agent with strong typing and validation.
    
    This agent mirrors the Simple Agent's capabilities but uses Pydantic models
    for inputs, outputs, and tool schemas. It is designed to be easily extended
    with an LLM in the future.
    
    Example:
        agent = PydanticAgent(name="MyAgent", description="A helpful agent")
        
        def add(a: int, b: int) -> int:
            return a + b
        
        agent.register_tool("add", "Add two numbers", add)
        
        result = agent.execute("add", a=1, b=2)
        print(result.result)  # 3
    """
    
    def __init__(
        self,
        name: str,
        description: str = "",
        memory: Optional[BaseMemory] = None,
        chunk_size: int = 800,
        overlap: int = 150,
    ):
        """
        Initialize the Pydantic Agent.
        
        Args:
            name: Agent name
            description: Agent description
            memory: Optional memory system for knowledge storage
            chunk_size: Size of text chunks for document ingestion
            overlap: Overlap between chunks
        """
        self.config = AgentConfig(
            name=name,
            description=description,
            chunk_size=chunk_size,
            overlap=overlap,
        )
        
        self._tools: Dict[str, RegisteredTool] = {}
        self._memory = memory
        self._mcp_adapter = MCPToolAdapter()
        self._connected_servers: Dict[str, StdioServerParameters] = {}
        self._chunker = TextChunker(chunk_size=chunk_size, overlap=overlap)
        
        # Auto-register memory tools if memory is provided
        if self._memory:
            self._register_memory_tools()
    
    @property
    def name(self) -> str:
        """Get agent name"""
        return self.config.name
    
    @property
    def description(self) -> str:
        """Get agent description"""
        return self.config.description
    
    @property
    def memory(self) -> Optional[BaseMemory]:
        """Get the attached memory system"""
        return self._memory
    
    def get_state(self) -> AgentState:
        """Get the current state of the agent"""
        return AgentState(
            config=self.config,
            tool_count=len(self._tools),
            has_memory=self._memory is not None,
            connected_servers=list(self._connected_servers.keys()),
        )
    
    # =========================================================================
    # Tool Registration
    # =========================================================================
    
    def register_tool(
        self,
        name: str,
        description: str,
        func: Callable,
        schema: Optional[ToolSchema] = None,
    ) -> ToolDefinition:
        """
        Register a tool with the agent.
        
        Args:
            name: Unique tool name
            description: Human-readable description
            func: The callable to execute
            schema: Optional explicit schema (auto-extracted from func if not provided)
        
        Returns:
            The created ToolDefinition
        """
        if schema is None:
            schema = _extract_tool_schema(func)
        
        definition = ToolDefinition(name=name, description=description, schema=schema)
        
        if name in self._tools:
            print(f"Warning: Tool '{name}' already exists, replacing...")
        
        self._tools[name] = RegisteredTool(definition=definition, func=func)
        return definition
    
    def add_function_as_tool(self, name: str, description: str, func: Callable) -> ToolDefinition:
        """
        Add a Python function as a tool (Simple Agent compatible method).
        
        This is an alias for register_tool() for compatibility with Simple Agent.
        """
        return self.register_tool(name, description, func)
    
    def add_tool(self, tool: GenericTool) -> ToolDefinition:
        """
        Add a GenericTool to the agent (Simple Agent compatible method).
        
        Args:
            tool: A GenericTool instance
        
        Returns:
            The created ToolDefinition
        """
        # Convert GenericTool schema to ToolSchema
        parameters = []
        if hasattr(tool, 'schema') and tool.schema:
            for param_name, param_info in tool.schema.parameters.items():
                param_type = param_info.get("type", "string")
                type_mapping = {
                    "string": ParameterType.STRING,
                    "integer": ParameterType.INTEGER,
                    "number": ParameterType.NUMBER,
                    "boolean": ParameterType.BOOLEAN,
                    "array": ParameterType.ARRAY,
                    "object": ParameterType.OBJECT,
                }
                parameters.append(ToolParameter(
                    name=param_name,
                    type=type_mapping.get(param_type, ParameterType.STRING),
                    description=param_info.get("description", param_name),
                    required=param_name in tool.schema.required,
                    default=param_info.get("default"),
                ))
        
        schema = ToolSchema(parameters=parameters)
        return self.register_tool(tool.name, tool.description, tool.run, schema)
    
    def unregister_tool(self, name: str) -> bool:
        """
        Unregister a tool by name.
        
        Args:
            name: Tool name to remove
        
        Returns:
            True if tool was removed, False if not found
        """
        if name in self._tools:
            del self._tools[name]
            return True
        return False
    
    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Get a tool definition by name"""
        if name in self._tools:
            return self._tools[name].definition
        return None
    
    def list_tools(self) -> List[str]:
        """List all registered tool names"""
        return list(self._tools.keys())
    
    def get_tool_definitions(self) -> List[ToolDefinition]:
        """Get all tool definitions"""
        return [t.definition for t in self._tools.values()]
    
    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """
        Get JSON-serializable schemas for all tools.
        
        This format is suitable for LLM tool calling interfaces.
        """
        return [t.definition.to_dict() for t in self._tools.values()]
    
    def get_tool_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific tool"""
        tool = self._tools.get(name)
        if tool is None:
            return None
        
        return {
            "name": tool.definition.name,
            "description": tool.definition.description,
            "schema": tool.definition.to_dict(),
            "parameters": tool.definition.schema_def.to_json_schema(),
        }
    
    def search_tools(self, query: str) -> List[str]:
        """Search for tools by name or description"""
        query_lower = query.lower()
        return [
            name for name, tool in self._tools.items()
            if query_lower in name.lower() or query_lower in tool.definition.description.lower()
        ]
    
    # =========================================================================
    # Tool Execution
    # =========================================================================
    
    def execute(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None, **kwargs) -> ToolExecutionResult:
        """
        Execute a tool by name with validation.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Dictionary of arguments (alternative to kwargs)
            **kwargs: Arguments to pass to the tool
        
        Returns:
            ToolExecutionResult with status, result, and timing
        """
        # Merge arguments dict with kwargs
        args = {**(arguments or {}), **kwargs}
        
        if tool_name not in self._tools:
            return ToolExecutionResult.error(
                tool_name=tool_name,
                error=f"Tool '{tool_name}' not found. Available tools: {self.list_tools()}",
            )
        
        tool = self._tools[tool_name]
        start_time = time.time()
        
        try:
            result = tool.execute(**args)
            
            if asyncio.iscoroutine(result):
                return ToolExecutionResult.error(
                    tool_name=tool_name,
                    error=f"Tool '{tool_name}' is async. Use 'await agent.execute_async()' instead.",
                )
            
            execution_time = (time.time() - start_time) * 1000
            return ToolExecutionResult.success(
                tool_name=tool_name,
                result=result,
                execution_time_ms=execution_time,
            )
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return ToolExecutionResult.error(
                tool_name=tool_name,
                error=str(e),
                execution_time_ms=execution_time,
            )
    
    async def execute_async(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None, **kwargs) -> ToolExecutionResult:
        """
        Execute a tool asynchronously (for MCP tools).
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Dictionary of arguments (alternative to kwargs)
            **kwargs: Arguments to pass to the tool
        
        Returns:
            ToolExecutionResult with status, result, and timing
        """
        args = {**(arguments or {}), **kwargs}
        
        if tool_name not in self._tools:
            return ToolExecutionResult.error(
                tool_name=tool_name,
                error=f"Tool '{tool_name}' not found. Available tools: {self.list_tools()}",
            )
        
        tool = self._tools[tool_name]
        start_time = time.time()
        
        try:
            result = await tool.execute_async(**args)
            execution_time = (time.time() - start_time) * 1000
            return ToolExecutionResult.success(
                tool_name=tool_name,
                result=result,
                execution_time_ms=execution_time,
            )
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return ToolExecutionResult.error(
                tool_name=tool_name,
                error=str(e),
                execution_time_ms=execution_time,
            )
    
    def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Execute a tool and return the raw result (Simple Agent compatible).
        
        This method matches the Simple Agent's interface for compatibility.
        Raises exceptions on error rather than returning a result object.
        """
        if tool_name not in self._tools:
            raise ValueError(f"Tool '{tool_name}' not found. Available tools: {self.list_tools()}")
        
        tool = self._tools[tool_name]
        
        try:
            result = tool.execute(**kwargs)
            if asyncio.iscoroutine(result):
                raise RuntimeError(
                    f"Tool '{tool_name}' is async. Use 'await agent.execute_tool_async()' instead."
                )
            return result
        except Exception as e:
            raise RuntimeError(f"Error executing tool '{tool_name}': {str(e)}")
    
    async def execute_tool_async(self, tool_name: str, **kwargs) -> Any:
        """
        Execute a tool asynchronously and return the raw result (Simple Agent compatible).
        """
        if tool_name not in self._tools:
            raise ValueError(f"Tool '{tool_name}' not found. Available tools: {self.list_tools()}")
        
        tool = self._tools[tool_name]
        
        try:
            return await tool.execute_async(**kwargs)
        except Exception as e:
            raise RuntimeError(f"Error executing tool '{tool_name}': {str(e)}")
    
    def execute_request(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """
        Execute a tool from a ToolExecutionRequest model.
        
        This is the primary method for future LLM integration, accepting
        structured requests and returning structured results.
        """
        return self.execute(request.tool_name, request.arguments)
    
    # =========================================================================
    # Memory Operations
    # =========================================================================
    
    def _register_memory_tools(self) -> None:
        """Register CRUD memory operations as tools"""
        self.register_tool(
            "memory_store",
            "Store knowledge in agent's long-term memory",
            self._memory_store,
        )
        self.register_tool(
            "memory_recall",
            "Recall relevant knowledge from agent's long-term memory",
            self._memory_recall,
        )
        self.register_tool(
            "memory_update",
            "Update existing knowledge in agent's memory",
            self._memory_update,
        )
        self.register_tool(
            "memory_delete",
            "Delete knowledge from agent's memory",
            self._memory_delete,
        )
        self.register_tool(
            "memory_get",
            "Get specific knowledge entry by ID",
            self._memory_get,
        )
        self.register_tool(
            "memory_list",
            "List all knowledge entries in memory",
            self._memory_list,
        )
        self.register_tool(
            "ingest_document",
            "Ingest a document (PDF or text) into memory with chunking and detailed stats",
            self._ingest_document,
        )
    
    def _memory_store(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store knowledge in memory"""
        if not self._memory:
            raise ValueError("No memory system attached to agent")
        return self._memory.create(text, metadata)
    
    def _memory_recall(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Recall knowledge from memory"""
        if not self._memory:
            raise ValueError("No memory system attached to agent")
        return self._memory.read(query, top_k)
    
    def _memory_update(self, id: str, new_text: str) -> bool:
        """Update knowledge in memory"""
        if not self._memory:
            raise ValueError("No memory system attached to agent")
        return self._memory.update(id, new_text)
    
    def _memory_delete(self, id: str) -> bool:
        """Delete knowledge from memory"""
        if not self._memory:
            raise ValueError("No memory system attached to agent")
        return self._memory.delete(id)
    
    def _memory_get(self, id: str) -> Optional[Dict[str, Any]]:
        """Get specific knowledge by ID"""
        if not self._memory:
            raise ValueError("No memory system attached to agent")
        if hasattr(self._memory, 'get_by_id'):
            return self._memory.get_by_id(id)
        return None
    
    def _memory_list(self) -> List[Dict[str, Any]]:
        """List all knowledge in memory"""
        if not self._memory:
            raise ValueError("No memory system attached to agent")
        if hasattr(self._memory, 'list_all'):
            return self._memory.list_all()
        return []
    
    def _extract_text_from_pdf(self, filepath: str) -> str:
        """Extract text from a PDF file"""
        try:
            import pdfplumber
        except ImportError:
            raise ImportError(
                "pdfplumber is required for PDF support. "
                "Install it with: pip install pdfplumber"
            )
        
        text_parts = []
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        
        return "\n\n".join(text_parts)
    
    def _ingest_document(
        self,
        filepath: str,
        chunk_size: Optional[int] = None,
        overlap: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Ingest a document (PDF or text) into memory with chunking"""
        if not self._memory:
            raise ValueError("No memory system attached to agent")
        
        path = Path(filepath)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        file_extension = path.suffix.lower()
        
        if file_extension == '.pdf':
            text = self._extract_text_from_pdf(filepath)
            file_type = 'pdf'
        elif file_extension in ['.txt', '.md', '.text']:
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()
            file_type = 'text'
        else:
            raise ValueError(f"Unsupported file type: {file_extension}. Supported: .pdf, .txt, .md")
        
        if not text.strip():
            return {
                "status": "error",
                "message": "No text could be extracted from the document",
                "filepath": str(filepath),
                "chunks_stored": 0,
            }
        
        if chunk_size or overlap:
            chunker = TextChunker(
                chunk_size=chunk_size or self._chunker.chunk_size,
                overlap=overlap or self._chunker.overlap,
            )
        else:
            chunker = self._chunker
        
        base_metadata = {
            "source": str(filepath),
            "filename": path.name,
            "file_type": file_type,
        }
        
        chunks = chunker.chunk_text(text, metadata=base_metadata)
        
        chunk_ids = []
        for chunk in chunks:
            chunk_id = self._memory.create(chunk["text"], chunk["metadata"])
            chunk_ids.append(chunk_id)
        
        return {
            "status": "success",
            "message": f"Successfully ingested {path.name}",
            "filepath": str(filepath),
            "file_type": file_type,
            "total_characters": len(text),
            "chunks_stored": len(chunks),
            "chunk_ids": chunk_ids,
            "chunk_size": chunker.chunk_size,
            "overlap": chunker.overlap,
        }
    
    def set_memory(self, memory: BaseMemory) -> None:
        """Attach a memory system to the agent and register memory tools"""
        self._memory = memory
        self._register_memory_tools()
    
    def get_memory_context(self, query: str, top_k: int = 5) -> MemoryQueryResult:
        """
        Get memory context as a structured Pydantic model.
        
        Args:
            query: The search query
            top_k: Maximum number of results
        
        Returns:
            MemoryQueryResult with matching entries
        """
        if self._memory is None:
            return MemoryQueryResult.empty(query, "No memory system attached")
        
        raw_results = self._memory.read(query, top_k=top_k)
        
        if not raw_results:
            return MemoryQueryResult.empty(query, "No relevant knowledge found")
        
        entries = []
        for result in raw_results:
            entries.append(MemoryEntry(
                id=result.get("id", ""),
                text=result.get("text", ""),
                metadata=result.get("meta", {}),
            ))
        
        return MemoryQueryResult(
            query=query,
            results=entries,
            count=len(entries),
        )
    
    def store_knowledge(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store knowledge in memory (convenience method)"""
        return self._memory_store(text, metadata)
    
    def recall_knowledge(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Recall knowledge from memory (convenience method)"""
        return self._memory_recall(query, top_k)
    
    # =========================================================================
    # MCP Server Integration
    # =========================================================================
    
    async def connect_mcp_server(self, server_name: str, server_params: StdioServerParameters) -> None:
        """Connect to an MCP server"""
        await self._mcp_adapter.connect_to_server(server_name, server_params)
        self._connected_servers[server_name] = server_params
        print(f"Connected to MCP server: {server_name}")
    
    async def load_tools_from_mcp_server(self, server_name: str) -> List[ToolDefinition]:
        """Load all tools from a specific MCP server"""
        if server_name not in self._connected_servers:
            raise ValueError(f"Server '{server_name}' not connected. Connect first using connect_mcp_server()")
        
        tools = await self._mcp_adapter.load_all_tools_from_server(server_name)
        definitions = []
        for tool in tools:
            definition = self.add_tool(tool)
            definitions.append(definition)
        
        print(f"Loaded {len(tools)} tools from MCP server: {server_name}")
        return definitions
    
    async def load_tools_from_all_servers(self) -> List[ToolDefinition]:
        """Load tools from all connected MCP servers"""
        all_definitions = []
        for server_name in self._connected_servers.keys():
            definitions = await self.load_tools_from_mcp_server(server_name)
            all_definitions.extend(definitions)
        return all_definitions
    
    # =========================================================================
    # Lifecycle
    # =========================================================================
    
    async def cleanup(self) -> None:
        """Clean up resources (close MCP connections)"""
        await self._mcp_adapter.close_all_connections()
    
    def __str__(self) -> str:
        server_count = len(self._connected_servers)
        memory_status = "with memory" if self._memory else "no memory"
        return f"PydanticAgent({self.name}, tools={len(self._tools)}, servers={server_count}, {memory_status})"
    
    def __repr__(self) -> str:
        return self.__str__()


def create_pydantic_agent(
    name: str,
    description: str = "",
    memory: Optional[BaseMemory] = None,
) -> PydanticAgent:
    """
    Create a new Pydantic Agent instance.
    
    Args:
        name: Agent name
        description: Agent description
        memory: Optional memory system
    
    Returns:
        A configured PydanticAgent instance
    """
    return PydanticAgent(name=name, description=description, memory=memory)
