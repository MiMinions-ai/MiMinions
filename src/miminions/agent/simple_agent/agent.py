"""
Enhanced Simple Agent with MCP Server Support and Memory

This module provides an enhanced agent that can dynamically load tools from MCP servers
and use them alongside regular generic tools, with integrated memory capabilities.
"""

import asyncio
from typing import List, Dict, Any, Optional, Union
from mcp import StdioServerParameters

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools import GenericTool, SimpleTool
from tools.mcp_adapter import MCPToolAdapter
from memory.base_memory import BaseMemory
from utils.chunker import TextChunker

class Agent:
    """Enhanced simple agent that can work with MCP servers and generic tools"""
    
    def __init__(self, name: str, description: str = "", memory: Optional[BaseMemory] = None, 
                 chunk_size: int = 800, overlap: int = 150):
        self.name = name
        self.description = description
        self.tools: List[GenericTool] = []
        self.memory = memory
        self.mcp_adapter = MCPToolAdapter()
        self.connected_servers: Dict[str, StdioServerParameters] = {}
        self.chunker = TextChunker(chunk_size=chunk_size, overlap=overlap)
        
        # Auto-register memory tools if memory is provided
        if self.memory:
            self._register_memory_tools()
    
    def _register_memory_tools(self):
        """Register CRUD memory operations as tools"""
        self.add_function_as_tool(
            "memory_store",
            "Store knowledge in agent's long-term memory",
            self._memory_store
        )
        
        self.add_function_as_tool(
            "memory_recall",
            "Recall relevant knowledge from agent's long-term memory",
            self._memory_recall
        )
        
        self.add_function_as_tool(
            "memory_update",
            "Update existing knowledge in agent's memory",
            self._memory_update
        )
        
        self.add_function_as_tool(
            "memory_delete",
            "Delete knowledge from agent's memory",
            self._memory_delete
        )
        
        self.add_function_as_tool(
            "memory_get",
            "Get specific knowledge entry by ID",
            self._memory_get
        )
        
        self.add_function_as_tool(
            "memory_list",
            "List all knowledge entries in memory",
            self._memory_list
        )
        
        self.add_function_as_tool(
            "ingest_document",
            "Ingest a document (PDF or text) into memory with chunking and detailed stats",
            self._ingest_document
        )
    
    def _memory_store(self, text: str, metadata: Dict[str, Any] = None) -> str:
        """Store knowledge in memory"""
        if not self.memory:
            raise ValueError("No memory system attached to agent")
        return self.memory.create(text, metadata)
    
    def _memory_recall(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Recall knowledge from memory"""
        if not self.memory:
            raise ValueError("No memory system attached to agent")
        return self.memory.read(query, top_k)
    
    def _memory_update(self, id: str, new_text: str) -> bool:
        """Update knowledge in memory"""
        if not self.memory:
            raise ValueError("No memory system attached to agent")
        return self.memory.update(id, new_text)
    
    def _memory_delete(self, id: str) -> bool:
        """Delete knowledge from memory"""
        if not self.memory:
            raise ValueError("No memory system attached to agent")
        return self.memory.delete(id)
    
    def _memory_get(self, id: str) -> Optional[Dict[str, Any]]:
        """Get specific knowledge by ID"""
        if not self.memory:
            raise ValueError("No memory system attached to agent")
        if hasattr(self.memory, 'get_by_id'):
            return self.memory.get_by_id(id)
        return None
    
    def _memory_list(self) -> List[Dict[str, Any]]:
        """List all knowledge in memory"""
        if not self.memory:
            raise ValueError("No memory system attached to agent")
        if hasattr(self.memory, 'list_all'):
            return self.memory.list_all()
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
            for page_num, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        
        return "\n\n".join(text_parts)
    
    def _ingest_document(self, filepath: str, chunk_size: Optional[int] = None, 
                        overlap: Optional[int] = None) -> Dict[str, Any]:
        """Ingest a document (PDF or text) into memory with chunking"""
        if not self.memory:
            raise ValueError("No memory system attached to agent")
        
        from pathlib import Path
        path = Path(filepath)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        # Determine file type and extract text
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
                "chunks_stored": 0
            }
        
        # Create chunker with custom settings if provided
        if chunk_size or overlap:
            chunker = TextChunker(
                chunk_size=chunk_size or self.chunker.chunk_size,
                overlap=overlap or self.chunker.overlap
            )
        else:
            chunker = self.chunker
        
        # Chunk the document
        base_metadata = {
            "source": str(filepath),
            "filename": path.name,
            "file_type": file_type
        }
        
        chunks = chunker.chunk_text(text, metadata=base_metadata)
        
        # Store each chunk in memory
        chunk_ids = []
        for chunk in chunks:
            chunk_id = self.memory.create(chunk["text"], chunk["metadata"])
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
            "overlap": chunker.overlap
        }
    
    async def connect_mcp_server(self, server_name: str, server_params: StdioServerParameters):
        """Connect to an MCP server"""
        await self.mcp_adapter.connect_to_server(server_name, server_params)
        self.connected_servers[server_name] = server_params
        print(f"Connected to MCP server: {server_name}")
    
    async def load_tools_from_mcp_server(self, server_name: str):
        """Load all tools from a specific MCP server"""
        if server_name not in self.connected_servers:
            raise ValueError(f"Server '{server_name}' not connected. Connect first using connect_mcp_server()")
        
        tools = await self.mcp_adapter.load_all_tools_from_server(server_name)
        for tool in tools:
            self.add_tool(tool)
        
        print(f"Loaded {len(tools)} tools from MCP server: {server_name}")
        return tools
    
    async def load_tools_from_all_servers(self):
        """Load tools from all connected MCP servers"""
        all_tools = []
        for server_name in self.connected_servers.keys():
            tools = await self.load_tools_from_mcp_server(server_name)
            all_tools.extend(tools)
        return all_tools
    
    def add_tool(self, tool: GenericTool) -> None:
        """Add a generic tool to the agent"""
        existing = self.get_tool(tool.name)
        if existing:
            print(f"Warning: Tool '{tool.name}' already exists, replacing...")
            self.tools = [t for t in self.tools if t.name != tool.name]
        
        self.tools.append(tool)
    
    def add_function_as_tool(self, name: str, description: str, func: callable) -> None:
        """Add a regular Python function as a tool"""
        tool = SimpleTool(name=name, description=description, func=func)
        self.add_tool(tool)
    
    def get_tool(self, name: str) -> Optional[GenericTool]:
        """Get a tool by name"""
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None
    
    def list_tools(self) -> List[str]:
        """List all available tool names"""
        return [tool.name for tool in self.tools]
    
    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """Get schema for all tools"""
        return [tool.to_dict() for tool in self.tools]
    
    def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """Execute a tool by name (for synchronous tools only)
        
        For MCP tools or other async tools, use execute_tool_async() instead.
        """
        tool = self.get_tool(tool_name)
        if tool is None:
            raise ValueError(f"Tool '{tool_name}' not found. Available tools: {self.list_tools()}")
        
        try:
            result = tool.run(**kwargs)
            if asyncio.iscoroutine(result):
                raise RuntimeError(
                    f"Tool '{tool_name}' is async. Use 'await agent.execute_tool_async()' instead."
                )
            return result
        except Exception as e:
            raise RuntimeError(f"Error executing tool '{tool_name}': {str(e)}")
    
    async def execute_tool_async(self, tool_name: str, **kwargs) -> Any:
        """Execute a tool by name (async version for MCP tools)"""
        tool = self.get_tool(tool_name)
        if tool is None:
            raise ValueError(f"Tool '{tool_name}' not found. Available tools: {self.list_tools()}")
        
        try:
            result = tool.run(**kwargs)
            if asyncio.iscoroutine(result):
                return await result
            return result
        except Exception as e:
            raise RuntimeError(f"Error executing tool '{tool_name}': {str(e)}")
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific tool"""
        tool = self.get_tool(tool_name)
        if tool is None:
            return None
        
        return {
            "name": tool.name,
            "description": tool.description,
            "schema": tool.to_dict(),
            "parameters": tool.schema.parameters if hasattr(tool, 'schema') else {}
        }
    
    def search_tools(self, query: str) -> List[str]:
        """Search for tools by name or description"""
        query_lower = query.lower()
        matching_tools = []
        
        for tool in self.tools:
            if (query_lower in tool.name.lower() or 
                query_lower in tool.description.lower()):
                matching_tools.append(tool.name)
        
        return matching_tools
    
    def set_memory(self, memory: BaseMemory) -> None:
        """Attach a memory system to the agent and register memory tools"""
        self.memory = memory
        self._register_memory_tools()

    def get_memory_context(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """Get memory context as structured data for LLM consumption"""
        if self.memory is None:
            return {
                "query": query,
                "results": [],
                "count": 0,
                "message": "No memory system attached"
            }
        
        results = self.memory.read(query, top_k=top_k)
        
        if not results:
            return {
                "query": query,
                "results": [],
                "count": 0,
                "message": "No relevant knowledge found"
            }
        
        clean_results = []
        for result in results:
            clean_results.append({
                "text": result.get("text", ""),
                "relevance": round(1 / (1 + result.get("distance", 0)), 2),
                "metadata": result.get("meta", {})
            })
        
        return {
            "query": query,
            "results": clean_results,
            "count": len(clean_results)
        }

    def store_knowledge(self, text: str, metadata: Dict[str, Any] = None) -> str:
        """Store knowledge in memory (convenience method)"""
        return self._memory_store(text, metadata)
    
    def recall_knowledge(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Recall knowledge from memory (convenience method)"""
        return self._memory_recall(query, top_k)

    async def cleanup(self):
        """Clean up resources (close MCP connections)"""
        await self.mcp_adapter.close_all_connections()
    
    def __str__(self) -> str:
        server_count = len(self.connected_servers)
        memory_status = "with memory" if self.memory else "no memory"
        return f"Agent({self.name}, tools={len(self.tools)}, servers={server_count}, {memory_status})"
    
    def __repr__(self) -> str:
        return self.__str__()


def create_simple_agent(name: str, description: str = "", memory: Optional[BaseMemory] = None) -> Agent:
    """Create a new simple agent instance with optional memory"""
    return Agent(name=name, description=description, memory=memory)
