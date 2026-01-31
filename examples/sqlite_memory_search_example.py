"""SQLite Memory Search Example - All search methods."""
from pathlib import Path
from miminions.memory.sqlite import SQLiteMemory

_FILE_DIR = Path(__file__).parent
_DATA_DIR = _FILE_DIR / ".data"
_SEARCH_DB = _DATA_DIR / "search_example.db"


def cleanup():
    """Remove persistent databases created by this demo."""
    if _SEARCH_DB.exists():
        _SEARCH_DB.unlink()
    if _DATA_DIR.exists() and not any(_DATA_DIR.iterdir()):
        _DATA_DIR.rmdir()


def setup_memory():
    """Create memory with sample data."""
    memory = SQLiteMemory(db_path=":memory:")
    
    facts = [
        ("Python is a high-level programming language.", {"type": "language", "year": 1991}),
        ("Machine learning uses neural networks.", {"type": "ai", "year": 2010}),
        ("SQLite is a lightweight database.", {"type": "database", "year": 2000}),
        ("JavaScript runs in browsers.", {"type": "language", "year": 1995}),
        ("Deep learning requires GPUs.", {"type": "ai", "year": 2012}),
    ]
    
    for text, meta in facts:
        memory.create(text, metadata=meta)
    
    return memory


def demo_vector_search(memory):
    """Vector similarity search."""
    print("Vector Search")
    results = memory.read("What is artificial intelligence?", top_k=2)
    for r in results:
        print(f"  {r['text']} (dist: {r['distance']:.3f})")


def demo_keyword_search(memory):
    """Keyword search."""
    print("\nKeyword Search")
    results = memory.get_by_keyword("learning")
    for r in results:
        print(f"  {r['text']}")


def demo_full_text_search(memory):
    """Full text search (all words must match)."""
    print("\nFull Text Search")
    results = memory.full_text_search("high level")
    for r in results:
        print(f"  {r['text']}")


def demo_metadata_search(memory):
    """Search by metadata."""
    print("\nMetadata Search")
    results = memory.metadata_search("type", "ai")
    for r in results:
        print(f"  {r['text']} - {r['meta']}")


def demo_regex_search(memory):
    """Regex pattern search."""
    print("\nRegex Search")
    results = memory.regex_search(r".*learning.*")
    for r in results:
        print(f"  {r['text']}")


def demo_hybrid_search(memory):
    """Combined vector + keyword search."""
    print("\nHybrid Search")
    results = memory.hybrid_search("programming language")
    for r in results:
        print(f"  [{r.get('source', 'unknown')}] {r['text']}")


def demo_datetime_search(memory):
    """Date range search."""
    print("\nDateTime Search")
    results = memory.date_time_search()
    for r in results[:3]:
        print(f"  {r['text']} - {r['created_at']}")


if __name__ == "__main__":
    print("SQLite Memory Search Demo\n")
    
    memory = setup_memory()
    
    demo_vector_search(memory)
    demo_keyword_search(memory)
    demo_full_text_search(memory)
    demo_metadata_search(memory)
    demo_regex_search(memory)
    demo_hybrid_search(memory)
    demo_datetime_search(memory)
    
    memory.close()
    cleanup()
    print("\nDone")
