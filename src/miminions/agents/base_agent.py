"""
Base agent module for MiMinions

This module provides the core BaseAgent class that integrates all the tools
and capabilities for knowledge retrieval, concept relations, and web search.
"""

import asyncio
from typing import Any, Callable, Dict, List, Optional, Union
from concurrent.futures import ThreadPoolExecutor

from .tools.database import DatabaseTools
from .tools.search import SearchTools


class BaseAgent:
    """
    Base agent with integrated tools for knowledge retrieval and exploration
    """
    
    def __init__(self, 
                 connection_string: Optional[str] = None,
                 max_workers: int = 4,
                 name: str = "BaseAgent"):
        """
        Initialize the base agent
        
        Args:
            connection_string: PostgreSQL connection string for database tools
            max_workers: Maximum number of concurrent operations
            name: Agent name for identification
        """
        self.name = name
        self.max_workers = max_workers
        self._custom_tools: Dict[str, Callable] = {}
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Initialize database tools if connection string provided
        if connection_string:
            self.database_tools = DatabaseTools(connection_string)
        else:
            self.database_tools = None
        
        # Initialize search tools if available
        try:
            self.search_tools = SearchTools(max_workers)
        except ImportError:
            self.search_tools = None
    
    def _validate_database_tools(self):
        """Internal method to validate database tools availability"""
        if self.database_tools is None:
            raise ValueError("Database tools not initialized. Provide connection_string in constructor.")
    
    def _validate_search_tools(self):
        """Internal method to validate search tools availability"""
        if self.search_tools is None:
            raise ValueError("Search tools not initialized. Install googlesearch-python and duckduckgo-search packages.")
    
    def _execute_custom_tool(self, tool_name: str, *args, **kwargs) -> Any:
        """Internal method to execute custom tools"""
        if tool_name not in self._custom_tools:
            raise ValueError(f"Tool '{tool_name}' not found. Available tools: {list(self._custom_tools.keys())}")
        
        tool_func = self._custom_tools[tool_name]
        return tool_func(*args, **kwargs)
    
    async def _execute_custom_tool_async(self, tool_name: str, *args, **kwargs) -> Any:
        """Internal async method to execute custom tools"""
        if tool_name not in self._custom_tools:
            raise ValueError(f"Tool '{tool_name}' not found. Available tools: {list(self._custom_tools.keys())}")
        
        tool_func = self._custom_tools[tool_name]
        
        # If tool is a coroutine, await it; otherwise run in executor
        if asyncio.iscoroutinefunction(tool_func):
            return await tool_func(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(self._executor, tool_func, *args, **kwargs)
    
    # Tool management methods
    def add_tool(self, name: str, tool_func: Callable) -> None:
        """
        Add a custom tool to the agent
        
        Args:
            name: Tool name
            tool_func: Tool function (can be sync or async)
        """
        self._custom_tools[name] = tool_func
    
    def remove_tool(self, name: str) -> None:
        """
        Remove a custom tool from the agent
        
        Args:
            name: Tool name to remove
        """
        if name in self._custom_tools:
            del self._custom_tools[name]
    
    def list_tools(self) -> List[str]:
        """
        List all available custom tools
        
        Returns:
            List of tool names
        """
        return list(self._custom_tools.keys())
    
    def has_tool(self, name: str) -> bool:
        """
        Check if a tool is available
        
        Args:
            name: Tool name
            
        Returns:
            True if tool exists
        """
        return name in self._custom_tools
    
    # Synchronous methods for database operations
    def vector_search(self, query_vector: List[float], table: str,
                     vector_column: str = "embedding",
                     limit: int = 10) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search for knowledge retrieval
        
        Args:
            query_vector: Query vector as list of floats
            table: Table name to search in
            vector_column: Column name containing vectors
            limit: Maximum number of results
            
        Returns:
            List of matching records with distance scores
        """
        self._validate_database_tools()
        return self.database_tools.vector_search(query_vector, table, vector_column, limit)
    
    def concept_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute GraphQL query for concept relations
        
        Args:
            query: GraphQL query string
            variables: Optional query variables
            
        Returns:
            Query result as dictionary
        """
        self._validate_database_tools()
        return self.database_tools.graphql_query(query, variables)
    
    def web_search(self, query: str, num_results: int = 10,
                  prefer_engine: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Perform web search for exploratory activities
        
        Args:
            query: Search query string
            num_results: Maximum number of results
            prefer_engine: Preferred search engine ("google" or "duckduckgo")
            
        Returns:
            List of search results
        """
        self._validate_search_tools()
        return self.search_tools.search(query, num_results, prefer_engine)
    
    def execute_tool(self, tool_name: str, *args, **kwargs) -> Any:
        """
        Execute a custom tool
        
        Args:
            tool_name: Name of the tool to execute
            *args: Positional arguments for the tool
            **kwargs: Keyword arguments for the tool
            
        Returns:
            Tool execution result
        """
        return self._execute_custom_tool(tool_name, *args, **kwargs)
    
    # Asynchronous methods for database operations
    async def vector_search_async(self, query_vector: List[float], table: str,
                                 vector_column: str = "embedding",
                                 limit: int = 10) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search for knowledge retrieval asynchronously
        
        Args:
            query_vector: Query vector as list of floats
            table: Table name to search in
            vector_column: Column name containing vectors
            limit: Maximum number of results
            
        Returns:
            List of matching records with distance scores
        """
        self._validate_database_tools()
        return await self.database_tools.vector_search_async(query_vector, table, vector_column, limit)
    
    async def concept_query_async(self, query: str, 
                                variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute GraphQL query for concept relations asynchronously
        
        Args:
            query: GraphQL query string
            variables: Optional query variables
            
        Returns:
            Query result as dictionary
        """
        self._validate_database_tools()
        return await self.database_tools.graphql_query_async(query, variables)
    
    async def web_search_async(self, query: str, num_results: int = 10,
                              prefer_engine: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Perform web search for exploratory activities asynchronously
        
        Args:
            query: Search query string
            num_results: Maximum number of results
            prefer_engine: Preferred search engine ("google" or "duckduckgo")
            
        Returns:
            List of search results
        """
        self._validate_search_tools()
        return await self.search_tools.search_async(query, num_results, prefer_engine)
    
    async def execute_tool_async(self, tool_name: str, *args, **kwargs) -> Any:
        """
        Execute a custom tool asynchronously
        
        Args:
            tool_name: Name of the tool to execute
            *args: Positional arguments for the tool
            **kwargs: Keyword arguments for the tool
            
        Returns:
            Tool execution result
        """
        return await self._execute_custom_tool_async(tool_name, *args, **kwargs)
    
    async def parallel_search(self, query: str, num_results: int = 10) -> Dict[str, List[Dict[str, Any]]]:
        """
        Perform parallel search across multiple engines
        
        Args:
            query: Search query string
            num_results: Maximum number of results per engine
            
        Returns:
            Dictionary with results from each engine
        """
        self._validate_search_tools()
        return await self.search_tools.parallel_search(query, num_results)
    
    # Advanced methods combining multiple capabilities
    def knowledge_search(self, query: str, query_vector: Optional[List[float]] = None,
                        table: str = "knowledge_base", 
                        vector_column: str = "embedding",
                        limit: int = 10,
                        include_web_search: bool = True,
                        web_results: int = 5) -> Dict[str, Any]:
        """
        Comprehensive knowledge search combining vector search and web search
        
        Args:
            query: Search query string
            query_vector: Optional query vector for vector search
            table: Table name for vector search
            vector_column: Vector column name
            limit: Maximum vector search results
            include_web_search: Whether to include web search results
            web_results: Maximum web search results
            
        Returns:
            Combined search results
        """
        results = {"query": query}
        
        # Vector search if vector and database tools available
        if query_vector and self.database_tools:
            try:
                results["vector_results"] = self.vector_search(query_vector, table, vector_column, limit)
            except Exception as e:
                results["vector_error"] = str(e)
        
        # Web search if enabled and search tools available
        if include_web_search and self.search_tools:
            try:
                results["web_results"] = self.web_search(query, web_results)
            except Exception as e:
                results["web_error"] = str(e)
        elif include_web_search and not self.search_tools:
            results["web_error"] = "Search tools not available"
        
        return results
    
    async def knowledge_search_async(self, query: str, query_vector: Optional[List[float]] = None,
                                   table: str = "knowledge_base",
                                   vector_column: str = "embedding",
                                   limit: int = 10,
                                   include_web_search: bool = True,
                                   web_results: int = 5) -> Dict[str, Any]:
        """
        Comprehensive knowledge search combining vector search and web search asynchronously
        
        Args:
            query: Search query string
            query_vector: Optional query vector for vector search
            table: Table name for vector search
            vector_column: Vector column name
            limit: Maximum vector search results
            include_web_search: Whether to include web search results
            web_results: Maximum web search results
            
        Returns:
            Combined search results
        """
        results = {"query": query}
        
        # Prepare tasks
        tasks = []
        
        # Vector search if vector and database tools available
        if query_vector and self.database_tools:
            tasks.append(("vector", self.vector_search_async(query_vector, table, vector_column, limit)))
        
        # Web search if enabled and search tools available
        if include_web_search and self.search_tools:
            tasks.append(("web", self.web_search_async(query, web_results)))
        elif include_web_search and not self.search_tools:
            results["web_error"] = "Search tools not available"
        
        # Execute tasks concurrently
        if tasks:
            task_results = await asyncio.gather(*[task[1] for task in tasks], return_exceptions=True)
            
            for i, (task_type, _) in enumerate(tasks):
                result = task_results[i]
                if isinstance(result, Exception):
                    results[f"{task_type}_error"] = str(result)
                else:
                    results[f"{task_type}_results"] = result
        
        return results
    
    def close(self):
        """Close all agent resources"""
        if self.database_tools:
            self.database_tools.close()
        if self.search_tools:
            self.search_tools.close()
        if self._executor:
            self._executor.shutdown(wait=True)
    
    async def close_async(self):
        """Close all agent resources asynchronously"""
        if self.database_tools:
            await self.database_tools.close_async()
        if self.search_tools:
            await self.search_tools.close_async()
        if self._executor:
            self._executor.shutdown(wait=True)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close_async()
    
    def __repr__(self):
        return f"BaseAgent(name='{self.name}', tools={len(self._custom_tools)})"