"""
Database tools for MiMinions agents

This module provides tools for interacting with PostgreSQL databases
with pgvector and pg_graphql support.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Union
from concurrent.futures import ThreadPoolExecutor

try:
    import psycopg
    import pgvector
    import numpy as np
except ImportError:
    psycopg = None
    pgvector = None
    np = None


class DatabaseTools:
    """
    Database tools for vector search and GraphQL operations
    """
    
    def __init__(self, connection_string: str):
        """
        Initialize database tools
        
        Args:
            connection_string: PostgreSQL connection string
        """
        if psycopg is None:
            raise ImportError("psycopg and pgvector are required for database operations")
        
        self.connection_string = connection_string
        self._connection = None
        self._async_connection = None
        self._executor = ThreadPoolExecutor(max_workers=4)
    
    def _get_connection(self):
        """Get synchronous database connection"""
        if self._connection is None or self._connection.closed:
            self._connection = psycopg.connect(self.connection_string)
        return self._connection
    
    async def _get_async_connection(self):
        """Get asynchronous database connection"""
        if self._async_connection is None or self._async_connection.closed:
            self._async_connection = await psycopg.AsyncConnection.connect(self.connection_string)
        return self._async_connection
    
    def _execute_vector_search(self, query_vector: List[float], table: str, 
                              vector_column: str = "embedding", 
                              limit: int = 10) -> List[Dict[str, Any]]:
        """Internal method to execute vector search"""
        conn = self._get_connection()
        with conn.cursor() as cur:
            # Convert list to numpy array for pgvector
            vector_array = np.array(query_vector)
            
            query = f"""
                SELECT *, {vector_column} <-> %s as distance
                FROM {table}
                ORDER BY distance
                LIMIT %s
            """
            cur.execute(query, (vector_array, limit))
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]
    
    async def _execute_vector_search_async(self, query_vector: List[float], table: str,
                                         vector_column: str = "embedding",
                                         limit: int = 10) -> List[Dict[str, Any]]:
        """Internal async method to execute vector search"""
        conn = await self._get_async_connection()
        async with conn.cursor() as cur:
            # Convert list to numpy array for pgvector
            vector_array = np.array(query_vector)
            
            query = f"""
                SELECT *, {vector_column} <-> %s as distance
                FROM {table}
                ORDER BY distance
                LIMIT %s
            """
            await cur.execute(query, (vector_array, limit))
            columns = [desc[0] for desc in cur.description]
            rows = await cur.fetchall()
            return [dict(zip(columns, row)) for row in rows]
    
    def _execute_graphql_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Internal method to execute GraphQL query"""
        conn = self._get_connection()
        with conn.cursor() as cur:
            # Execute GraphQL query using pg_graphql
            if variables:
                cur.execute("SELECT graphql.resolve($1, $2)", (query, json.dumps(variables)))
            else:
                cur.execute("SELECT graphql.resolve($1)", (query,))
            
            result = cur.fetchone()
            return result[0] if result else {}
    
    async def _execute_graphql_query_async(self, query: str, 
                                         variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Internal async method to execute GraphQL query"""
        conn = await self._get_async_connection()
        async with conn.cursor() as cur:
            # Execute GraphQL query using pg_graphql
            if variables:
                await cur.execute("SELECT graphql.resolve($1, $2)", (query, json.dumps(variables)))
            else:
                await cur.execute("SELECT graphql.resolve($1)", (query,))
            
            result = await cur.fetchone()
            return result[0] if result else {}
    
    # Public synchronous methods
    def vector_search(self, query_vector: List[float], table: str, 
                     vector_column: str = "embedding", 
                     limit: int = 10) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search
        
        Args:
            query_vector: Query vector as list of floats
            table: Table name to search in
            vector_column: Column name containing vectors
            limit: Maximum number of results
            
        Returns:
            List of matching records with distance scores
        """
        return self._execute_vector_search(query_vector, table, vector_column, limit)
    
    def graphql_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute GraphQL query for concept relations
        
        Args:
            query: GraphQL query string
            variables: Optional query variables
            
        Returns:
            Query result as dictionary
        """
        return self._execute_graphql_query(query, variables)
    
    # Public asynchronous methods
    async def vector_search_async(self, query_vector: List[float], table: str,
                                 vector_column: str = "embedding",
                                 limit: int = 10) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search asynchronously
        
        Args:
            query_vector: Query vector as list of floats
            table: Table name to search in
            vector_column: Column name containing vectors
            limit: Maximum number of results
            
        Returns:
            List of matching records with distance scores
        """
        return await self._execute_vector_search_async(query_vector, table, vector_column, limit)
    
    async def graphql_query_async(self, query: str, 
                                variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute GraphQL query for concept relations asynchronously
        
        Args:
            query: GraphQL query string
            variables: Optional query variables
            
        Returns:
            Query result as dictionary
        """
        return await self._execute_graphql_query_async(query, variables)
    
    def close(self):
        """Close database connections"""
        if self._connection and not self._connection.closed:
            self._connection.close()
        if self._executor:
            self._executor.shutdown(wait=True)
    
    async def close_async(self):
        """Close async database connections"""
        if self._async_connection and not self._async_connection.closed:
            await self._async_connection.close()
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