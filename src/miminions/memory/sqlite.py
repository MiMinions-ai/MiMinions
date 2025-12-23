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
        cursor = self.conn.execute("SELECT id, text, metadata FROM knowledge")
        return [
            {"id": row[0], "text": row[1], "meta": eval(row[2]) if row[2] else {}}
            for row in cursor.fetchall()
        ]
    
    def clear(self) -> None:
        self.conn.execute("DELETE FROM knowledge")
        self.conn.execute("DELETE FROM knowledge_vec")
        self.conn.commit()
    
    def search_keyword(self, keyword: str, top_k: int = 5) -> List[Dict[str, Any]]:
        cursor = self.conn.execute(
            "SELECT id, text, metadata FROM knowledge WHERE text LIKE ? LIMIT ?",
            (f"%{keyword}%", top_k)
        )
        return [
            {"id": row[0], "text": row[1], "meta": eval(row[2]) if row[2] else {}}
            for row in cursor.fetchall()
        ]
    
    def close(self):
        self.conn.close()
    
    def __del__(self):
        if hasattr(self, 'conn'):
            self.conn.close()
