"""SQLite Memory Example - CRUD and Search operations."""

from miminions.memory.sqlite import SQLiteMemory
from miminions.agent import create_pydantic_agent


def main():
    print("SQLite Memory Demo")
    
    memory = SQLiteMemory(db_path=":memory:")
    agent = create_pydantic_agent("DemoAgent", memory=memory)
    
    print("\n1. Storing entries")
    facts = [
        ("Python is a high-level programming language.", {"type": "language"}),
        ("Machine learning uses neural networks.", {"type": "tech"}),
        ("SQLite is a lightweight database.", {"type": "database"}),
        ("JavaScript runs in browsers.", {"type": "language"}),
    ]
    
    ids = []
    for text, meta in facts:
        result = agent.execute("memory_store", text=text, metadata=meta)
        ids.append(result.result)
        print(f"  Stored: {text[:40]}... (id: {result.result[:8]})")
    
    print("\n2. Reading by ID")
    result = agent.execute("memory_get", id=ids[0])
    print(f"- Text: {result.result['text']}")
    print(f"- Meta: {result.result['meta']}")
    
    print("\n3. Updating entry")
    agent.execute("memory_update", id=ids[0], new_text="Python is a versatile programming language.")
    result = agent.execute("memory_get", id=ids[0])
    print(f"- Updated: {result.result['text']}")
    
    print("\n4. Vector search")
    result = agent.execute("memory_recall", query="What is artificial intelligence?", top_k=2)
    for r in result.result:
        print(f"  - {r['text']} (dist: {r['distance']:.3f})")
    
    print("\n5. Convenience methods")
    results = agent.recall_knowledge("programming", top_k=2)
    for r in results:
        print(f"  - {r['text']}")
    
    print("\n6. Structured context (MemoryQueryResult)")
    context = agent.get_memory_context("learning", top_k=2)
    print(f"- Query: {context.query}")
    print(f"- Count: {context.count}")
    for entry in context.results:
        print(f"  - {entry.text}")
    
    print("\n7. List all entries")
    result = agent.execute("memory_list")
    print(f"- Total: {len(result.result)} entries")
    
    print("\n8. Deleting entry")
    agent.execute("memory_delete", id=ids[-1])
    result = agent.execute("memory_list")
    print(f"- Remaining: {len(result.result)} entries")
    
    memory.close()
    print("\nDone")


if __name__ == "__main__":
    main()
