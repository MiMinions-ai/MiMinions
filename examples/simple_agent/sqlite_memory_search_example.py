"""SQLite Memory Search Example for Simple Agent."""
from miminions.memory.sqlite import SQLiteMemory


def setup_memory():
    memory = SQLiteMemory(db_path=":memory:")
    facts = [
        ("Python is a high-level programming language.", {"type": "language"}),
        ("Machine learning uses neural networks.", {"type": "ai"}),
        ("SQLite is a lightweight database.", {"type": "database"}),
        ("JavaScript runs in browsers.", {"type": "language"}),
        ("Deep learning requires GPUs.", {"type": "ai"}),
    ]
    for text, meta in facts:
        memory.create(text, metadata=meta)
    return memory


def demo_searches():
    print("SQLite Memory Search Demo")
    memory = setup_memory()
    
    print("Vector Search:")
    for r in memory.read("What is artificial intelligence?", top_k=2):
        print(f"  {r['text']} (dist: {r['distance']:.3f})")
    
    print("Keyword Search:")
    for r in memory.get_by_keyword("learning"):
        print(f"  {r['text']}")
    
    print("Full Text Search:")
    for r in memory.full_text_search("high level"):
        print(f"  {r['text']}")
    
    print("Metadata Search:")
    for r in memory.metadata_search("type", "ai"):
        print(f"  {r['text']}")
    
    print("Regex Search:")
    for r in memory.regex_search(r".*learning.*"):
        print(f"  {r['text']}")
    
    print("Hybrid Search:")
    for r in memory.hybrid_search("programming language"):
        print(f"  [{r.get('source', 'unknown')}] {r['text']}")
    
    memory.close()
    print("Done")


if __name__ == "__main__":
    demo_searches()
