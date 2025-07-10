"""
Database tools for MiMinions agents

This module provides tools for interacting with PostgreSQL databases
with pgvector and pg_graphql support.
"""

import asyncio
import json
import uuid
from datetime import datetime
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
    
    # Session-based methods for conversation management
    def store_session_message(self, session_id: str, role: str, content: str, 
                             embedding: Optional[List[float]] = None,
                             metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Store a message in a conversation session
        
        Args:
            session_id: Unique session identifier
            role: Message role (user, assistant, system)
            content: Message content
            embedding: Optional content embedding for semantic search
            metadata: Optional additional metadata
            
        Returns:
            Message ID
        """
        return self._store_session_message(session_id, role, content, embedding, metadata)
    
    async def store_session_message_async(self, session_id: str, role: str, content: str,
                                        embedding: Optional[List[float]] = None,
                                        metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Store a message in a conversation session asynchronously
        
        Args:
            session_id: Unique session identifier
            role: Message role (user, assistant, system)
            content: Message content
            embedding: Optional content embedding for semantic search
            metadata: Optional additional metadata
            
        Returns:
            Message ID
        """
        return await self._store_session_message_async(session_id, role, content, embedding, metadata)
    
    def get_session_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieve conversation history for a session
        
        Args:
            session_id: Session identifier
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of messages in chronological order
        """
        return self._get_session_history(session_id, limit)
    
    async def get_session_history_async(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieve conversation history for a session asynchronously
        
        Args:
            session_id: Session identifier
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of messages in chronological order
        """
        return await self._get_session_history_async(session_id, limit)
    
    def search_session_context(self, session_id: str, query_vector: List[float],
                              limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for relevant context within a session using vector similarity
        
        Args:
            session_id: Session identifier
            query_vector: Query vector for similarity search
            limit: Maximum number of results
            
        Returns:
            List of relevant messages with similarity scores
        """
        return self._search_session_context(session_id, query_vector, limit)
    
    async def search_session_context_async(self, session_id: str, query_vector: List[float],
                                         limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for relevant context within a session using vector similarity asynchronously
        
        Args:
            session_id: Session identifier
            query_vector: Query vector for similarity search
            limit: Maximum number of results
            
        Returns:
            List of relevant messages with similarity scores
        """
        return await self._search_session_context_async(session_id, query_vector, limit)
    
    # Internal methods for session operations
    def _store_session_message(self, session_id: str, role: str, content: str,
                              embedding: Optional[List[float]] = None,
                              metadata: Optional[Dict[str, Any]] = None) -> str:
        """Internal method to store session message"""
        conn = self._get_connection()
        with conn.cursor() as cur:
            message_id = str(uuid.uuid4())
            timestamp = datetime.utcnow()
            
            # Convert embedding to numpy array if provided
            embedding_array = np.array(embedding) if embedding and np is not None else None
            metadata_json = json.dumps(metadata) if metadata else None
            
            # Create sessions table if not exists
            cur.execute("""
                CREATE TABLE IF NOT EXISTS conversation_sessions (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    embedding vector,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes if not exist
            cur.execute("""
                CREATE INDEX IF NOT EXISTS session_idx ON conversation_sessions (session_id)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS created_idx ON conversation_sessions (created_at)
            """)
            
            # Insert message
            cur.execute("""
                INSERT INTO conversation_sessions 
                (id, session_id, role, content, embedding, metadata, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (message_id, session_id, role, content, embedding_array, metadata_json, timestamp))
            
            conn.commit()
            return message_id
    
    async def _store_session_message_async(self, session_id: str, role: str, content: str,
                                         embedding: Optional[List[float]] = None,
                                         metadata: Optional[Dict[str, Any]] = None) -> str:
        """Internal async method to store session message"""
        conn = await self._get_async_connection()
        async with conn.cursor() as cur:
            message_id = str(uuid.uuid4())
            timestamp = datetime.utcnow()
            
            # Convert embedding to numpy array if provided
            embedding_array = np.array(embedding) if embedding and np is not None else None
            metadata_json = json.dumps(metadata) if metadata else None
            
            # Create sessions table if not exists
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS conversation_sessions (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    embedding vector,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes if not exist
            await cur.execute("""
                CREATE INDEX IF NOT EXISTS session_idx ON conversation_sessions (session_id)
            """)
            await cur.execute("""
                CREATE INDEX IF NOT EXISTS created_idx ON conversation_sessions (created_at)
            """)
            
            # Insert message
            await cur.execute("""
                INSERT INTO conversation_sessions 
                (id, session_id, role, content, embedding, metadata, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (message_id, session_id, role, content, embedding_array, metadata_json, timestamp))
            
            await conn.commit()
            return message_id
    
    def _get_session_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Internal method to get session history"""
        conn = self._get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, session_id, role, content, metadata, created_at
                FROM conversation_sessions
                WHERE session_id = %s
                ORDER BY created_at ASC
                LIMIT %s
            """, (session_id, limit))
            
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]
    
    async def _get_session_history_async(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Internal async method to get session history"""
        conn = await self._get_async_connection()
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT id, session_id, role, content, metadata, created_at
                FROM conversation_sessions
                WHERE session_id = %s
                ORDER BY created_at ASC
                LIMIT %s
            """, (session_id, limit))
            
            columns = [desc[0] for desc in cur.description]
            rows = await cur.fetchall()
            return [dict(zip(columns, row)) for row in rows]
    
    def _search_session_context(self, session_id: str, query_vector: List[float],
                               limit: int = 10) -> List[Dict[str, Any]]:
        """Internal method to search session context"""
        conn = self._get_connection()
        with conn.cursor() as cur:
            # Convert list to numpy array for pgvector
            vector_array = np.array(query_vector)
            
            cur.execute("""
                SELECT id, session_id, role, content, metadata, created_at,
                       embedding <-> %s as distance
                FROM conversation_sessions
                WHERE session_id = %s AND embedding IS NOT NULL
                ORDER BY distance
                LIMIT %s
            """, (vector_array, session_id, limit))
            
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]
    
    async def _search_session_context_async(self, session_id: str, query_vector: List[float],
                                          limit: int = 10) -> List[Dict[str, Any]]:
        """Internal async method to search session context"""
        conn = await self._get_async_connection()
        async with conn.cursor() as cur:
            # Convert list to numpy array for pgvector
            vector_array = np.array(query_vector)
            
            await cur.execute("""
                SELECT id, session_id, role, content, metadata, created_at,
                       embedding <-> %s as distance
                FROM conversation_sessions
                WHERE session_id = %s AND embedding IS NOT NULL
                ORDER BY distance
                LIMIT %s
            """, (vector_array, session_id, limit))
            
            columns = [desc[0] for desc in cur.description]
            rows = await cur.fetchall()
            return [dict(zip(columns, row)) for row in rows]
    
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