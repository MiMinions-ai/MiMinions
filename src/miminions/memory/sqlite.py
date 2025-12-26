import sqlite3
import sqlite_vec
import struct
from pathlib import Path
from typing import List, Dict, Any, Optional
from .base_memory import BaseMemory
from uuid import uuid4
from sentence_transformers import SentenceTransformer


_DEFAULT_DB_DIR = Path(__file__).parent / ".data"
_DEFAULT_DB_PATH = _DEFAULT_DB_DIR / "memory.db"


def _serialize_f32(vector: list) -> bytes:
    return struct.pack(f"{len(vector)}f", *vector)


class SQLiteMemory(BaseMemory):
    """
    SQLite-based vector memory using sqlite-vec.
    
    Storage options:
        - db_path=":memory:" -> temporary, session-based (lost when process ends)
        - db_path=None -> persistent, uses default location in package
        - db_path="/your/path.db" -> persistent, uses your specified path
    """
    
    def __init__(
        self, 
        db_path: Optional[str] = None,
        model_name: str = "all-MiniLM-L6-v2", 
        dim: int = 384
    ):
        if db_path is None:
            _DEFAULT_DB_DIR.mkdir(parents=True, exist_ok=True)
            self.db_path = str(_DEFAULT_DB_PATH)
        elif db_path == ":memory:":
            self.db_path = ":memory:"
        else:
            user_path = Path(db_path)
            user_path.parent.mkdir(parents=True, exist_ok=True)
            self.db_path = str(user_path)
        
        self.dim = dim
        self.encoder = SentenceTransformer(model_name)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.enable_load_extension(True)
        sqlite_vec.load(self.conn)
        self.conn.enable_load_extension(False)
        self._setup_tables()
    
    def _setup_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_text ON knowledge(text)")
        
        self.conn.execute(f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_vec USING vec0(
                id TEXT PRIMARY KEY,
                embedding float[{self.dim}]
            )
        """)
        self.conn.commit()
    
    def create(self, text: str, metadata: Dict[str, Any] = None) -> str:
        id = str(uuid4())
        vector = self.encoder.encode([text])[0].tolist()
        
        self.conn.execute(
            "INSERT INTO knowledge (id, text, metadata) VALUES (?, ?, ?)",
            (id, text, str(metadata or {}))
        )
        self.conn.execute(
            "INSERT INTO knowledge_vec (id, embedding) VALUES (?, ?)",
            (id, _serialize_f32(vector))
        )
        self.conn.commit()
        return id
    
    def read(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        query_vec = self.encoder.encode([query])[0].tolist()
        
        cursor = self.conn.execute("""
            SELECT v.id, v.distance, k.text, k.metadata
            FROM knowledge_vec v
            JOIN knowledge k ON v.id = k.id
            WHERE embedding MATCH ? AND k = ?
            ORDER BY distance
        """, (_serialize_f32(query_vec), top_k))
        
        results = []
        for row in cursor:
            id, distance, text, metadata = row
            results.append({
                "id": id,
                "text": text,
                "meta": eval(metadata) if metadata else {},
                "distance": float(distance)
            })
        
        return results
    
    def update(self, id: str, new_text: str) -> bool:
        cursor = self.conn.execute("SELECT id FROM knowledge WHERE id = ?", (id,))
        if not cursor.fetchone():
            return False
        
        new_vec = self.encoder.encode([new_text])[0].tolist()
        
        self.conn.execute(
            "UPDATE knowledge SET text = ? WHERE id = ?",
            (new_text, id)
        )
        self.conn.execute("DELETE FROM knowledge_vec WHERE id = ?", (id,))
        self.conn.execute(
            "INSERT INTO knowledge_vec (id, embedding) VALUES (?, ?)",
            (id, _serialize_f32(new_vec))
        )
        self.conn.commit()
        return True
    
    def delete(self, id: str) -> bool:
        cursor = self.conn.execute("DELETE FROM knowledge WHERE id = ?", (id,))
        self.conn.execute("DELETE FROM knowledge_vec WHERE id = ?", (id,))
        self.conn.commit()
        return cursor.rowcount > 0
    
    def get_by_id(self, id: str) -> Optional[Dict[str, Any]]:
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
    
    def get_by_keyword(self, keyword: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search entries containing keyword (case-insensitive)."""
        cursor = self.conn.execute(
            "SELECT id, text, metadata FROM knowledge WHERE LOWER(text) LIKE LOWER(?) LIMIT ?",
            (f"%{keyword}%", top_k)
        )
        return [
            {"id": row[0], "text": row[1], "meta": eval(row[2]) if row[2] else {}}
            for row in cursor.fetchall()
        ]

    def full_text_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for entries containing all words in query."""
        words = query.lower().split()
        if not words:
            return []
        
        conditions = " AND ".join(["LOWER(text) LIKE ?" for _ in words])
        params = [f"%{word}%" for word in words] + [top_k]
        
        cursor = self.conn.execute(
            f"SELECT id, text, metadata FROM knowledge WHERE {conditions} LIMIT ?",
            params
        )
        return [
            {"id": row[0], "text": row[1], "meta": eval(row[2]) if row[2] else {}}
            for row in cursor.fetchall()
        ]
    
    def metadata_search(self, key: str, value: Any, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search entries by metadata key-value pair."""
        cursor = self.conn.execute(
            "SELECT id, text, metadata FROM knowledge LIMIT ?", (top_k * 10,)
        )
        results = []
        for row in cursor.fetchall():
            meta = eval(row[2]) if row[2] else {}
            if meta.get(key) == value:
                results.append({"id": row[0], "text": row[1], "meta": meta})
                if len(results) >= top_k:
                    break
        return results

    def regex_search(self, pattern: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search entries matching regex pattern."""
        import re
        cursor = self.conn.execute("SELECT id, text, metadata FROM knowledge")
        results = []
        for row in cursor.fetchall():
            if re.search(pattern, row[1], re.IGNORECASE):
                results.append({
                    "id": row[0], "text": row[1], 
                    "meta": eval(row[2]) if row[2] else {}
                })
                if len(results) >= top_k:
                    break
        return results

    def hybrid_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Combine vector and keyword search."""
        vector_results = self.read(query, top_k=top_k)
        keyword_results = self.get_by_keyword(query, top_k=top_k)
        
        seen_ids = set()
        combined = []
        for r in vector_results:
            if r["id"] not in seen_ids:
                r["source"] = "vector"
                combined.append(r)
                seen_ids.add(r["id"])
        for r in keyword_results:
            if r["id"] not in seen_ids:
                r["source"] = "keyword"
                combined.append(r)
                seen_ids.add(r["id"])
        return combined[:top_k]

    def date_time_search(self, start: str = None, end: str = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search entries by creation date range (ISO format: YYYY-MM-DD)."""
        if start and end:
            cursor = self.conn.execute(
                "SELECT id, text, metadata, created_at FROM knowledge WHERE created_at BETWEEN ? AND ? LIMIT ?",
                (start, end, top_k)
            )
        elif start:
            cursor = self.conn.execute(
                "SELECT id, text, metadata, created_at FROM knowledge WHERE created_at >= ? LIMIT ?",
                (start, top_k)
            )
        elif end:
            cursor = self.conn.execute(
                "SELECT id, text, metadata, created_at FROM knowledge WHERE created_at <= ? LIMIT ?",
                (end, top_k)
            )
        else:
            cursor = self.conn.execute(
                "SELECT id, text, metadata, created_at FROM knowledge LIMIT ?", (top_k,)
            )
        return [
            {"id": row[0], "text": row[1], "meta": eval(row[2]) if row[2] else {}, "created_at": row[3]}
            for row in cursor.fetchall()
        ]
    
    def list_all(self) -> List[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT id, text, metadata FROM knowledge")
        return [
            {"id": row[0], "text": row[1], "meta": eval(row[2]) if row[2] else {}}
            for row in cursor.fetchall()
        ]
    
    def clear(self) -> None:
        self.conn.execute("DELETE FROM knowledge")
        self.conn.execute("DELETE FROM knowledge_vec")
        self.conn.commit()
    
    def close(self):
        self.conn.close()
    
    def __del__(self):
        if hasattr(self, 'conn'):
            self.conn.close()
