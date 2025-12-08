import sqlite3
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
from .base_memory import BaseMemory
from uuid import uuid4
from sentence_transformers import SentenceTransformer


class SQLiteMemory(BaseMemory):    
    def __init__(self, db_path: str = ":memory:", model_name: str = "all-MiniLM-L6-v2", dim: int = 384):
        """
        Initialize SQLite vector memory
        
        Args:
            db_path: Path to SQLite database file, or ":memory:" for in-memory
            model_name: SentenceTransformer model for embeddings
            dim: Dimension of embeddings (must match model output)
        """
        self.db_path = db_path
        self.dim = dim
        self.encoder = SentenceTransformer(model_name)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._setup_tables()
    
    def _setup_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                embedding BLOB NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_text ON knowledge(text)")
        self.conn.commit()
    
    def create(self, text: str, metadata: Dict[str, Any] = None) -> str:
        """Add knowledge to memory and return its ID"""
        id = str(uuid4())
        vector = self.encoder.encode([text])[0].astype("float32")
        
        self.conn.execute(
            "INSERT INTO knowledge (id, text, embedding, metadata) VALUES (?, ?, ?, ?)",
            (id, text, vector.tobytes(), str(metadata or {}))
        )
        self.conn.commit()
        return id
    
    def read(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve top-k similar knowledge entries using vector similarity"""
        query_vec = self.encoder.encode([query])[0].astype("float32")
        
        cursor = self.conn.execute("SELECT id, text, embedding, metadata FROM knowledge")
        results = []
        
        for row in cursor:
            id, text, embedding_blob, metadata = row
            embedding = np.frombuffer(embedding_blob, dtype="float32")
            
            distance = float(np.linalg.norm(query_vec - embedding))
            
            results.append({
                "id": id,
                "text": text,
                "meta": eval(metadata) if metadata else {},
                "distance": distance
            })
        
        results.sort(key=lambda x: x["distance"])
        return results[:top_k]
    
    def update(self, id: str, new_text: str) -> bool:
        """Update an entry by ID"""
        cursor = self.conn.execute("SELECT id FROM knowledge WHERE id = ?", (id,))
        if not cursor.fetchone():
            return False
        
        new_vec = self.encoder.encode([new_text])[0].astype("float32")
        
        self.conn.execute(
            "UPDATE knowledge SET text = ?, embedding = ? WHERE id = ?",
            (new_text, new_vec.tobytes(), id)
        )
        self.conn.commit()
        return True
    
    def delete(self, id: str) -> bool:
        """Delete an entry by ID"""
        cursor = self.conn.execute("DELETE FROM knowledge WHERE id = ?", (id,))
        self.conn.commit()
        return cursor.rowcount > 0
    
    def get_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """Retrieve an entry by ID"""
        cursor = self.conn.execute(
            "SELECT id, text, metadata FROM knowledge WHERE id = ?", (id,)
        )
        row = cursor.fetchone()
        
        if row:
            return {
                "id": row[0],
                "text": row[1],
                "meta": eval(row[2]) if row[2] else {}
            }
        return None
    
    def get_by_keyword():
        pass

    def full_test_search():
        pass
    
    def metadata_search():
        pass

    def regex_search():
        pass

    def hybrid_search():
        pass

    def date_time_search():
        pass
    
    def list_all(self) -> List[Dict[str, Any]]:
        """List all knowledge entries"""
        cursor = self.conn.execute("SELECT id, text, metadata FROM knowledge")
        return [
            {"id": row[0], "text": row[1], "meta": eval(row[2]) if row[2] else {}}
            for row in cursor.fetchall()
        ]
    
    def clear(self) -> None:
        """Clear all knowledge from memory"""
        self.conn.execute("DELETE FROM knowledge")
        self.conn.commit()
    
    def search_keyword(self, keyword: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Simple keyword search using SQL LIKE"""
        cursor = self.conn.execute(
            "SELECT id, text, metadata FROM knowledge WHERE text LIKE ? LIMIT ?",
            (f"%{keyword}%", top_k)
        )
        return [
            {"id": row[0], "text": row[1], "meta": eval(row[2]) if row[2] else {}}
            for row in cursor.fetchall()
        ]
    
    def close(self):
        """Close database connection"""
        self.conn.close()
    
    def __del__(self):
        """Cleanup on deletion"""
        if hasattr(self, 'conn'):
            self.conn.close()
