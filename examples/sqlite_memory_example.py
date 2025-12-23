from miminions.memory.sqlite import SQLiteMemory

def demo_session_mode():
    """Demo using temporary session-based memory (lost when process ends)"""
    print("=== SQLite Vector Memory Demo (Session Mode) ===")
    
    print("\nSetting up memory (in-memory, temporary)...")
    memory = SQLiteMemory(db_path=":memory:")
    
    print("\nAdding some facts...")
    facts = [
        "Python is a high-level programming language.",
        "Machine learning is a subset of artificial intelligence.",
        "Neural networks are inspired by biological neurons.",
        "SQLite is a lightweight relational database.",
        "Vector embeddings represent text as numerical arrays.",
    ]
    
    ids = []
    for fact in facts:
        id = memory.create(fact, metadata={"source": "demo"})
        ids.append(id)
        print(f"  - {fact}")
    
    print("\nTrying vector search...")
    query = "What is a database?"
    print(f"Query: '{query}'")
    results = memory.read(query, top_k=3)
    print(f"Found {len(results)} matches:")
    for i, result in enumerate(results, 1):
        print(f"  {i}. {result['text']} (dist: {result['distance']:.3f})")
    
    print("\nKeyword search test...")
    keyword = "learning"
    print(f"Looking for: '{keyword}'")
    results = memory.search_keyword(keyword)
    print(f"Got {len(results)} results:")
    for result in results:
        print(f"  - {result['text']}")
    
    print("\nGrabbing entry by ID...")
    first_id = ids[0]
    entry = memory.get_by_id(first_id)
    if entry:
        print(f"ID: {first_id[:8]}...")
        print(f"Text: {entry['text']}")
        print(f"Meta: {entry['meta']}")
    
    print("\nUpdating an entry...")
    new_text = "Python is a versatile, high-level programming language used for AI."
    success = memory.update(first_id, new_text)
    print(f"Updated: {success}")
    updated = memory.get_by_id(first_id)
    print(f"New text: {updated['text']}")
    
    print("\nListing everything...")
    all_entries = memory.list_all()
    print(f"Total: {len(all_entries)} entries")
    
    print("\nDeleting one...")
    delete_id = ids[1]
    success = memory.delete(delete_id)
    print(f"Deleted {delete_id[:8]}... -> {success}")
    all_entries = memory.list_all()
    print(f"Remaining: {len(all_entries)}")
    
    print("\nClearing everything...")
    memory.clear()
    all_entries = memory.list_all()
    print(f"After clear: {len(all_entries)} entries")
    
    memory.close()
    print("\nSession mode demo done")


def demo_persistent_mode():
    """Demo using persistent storage (default location in package)"""
    print("\n=== SQLite Vector Memory Demo (Persistent Mode) ===")
    
    # Default persistent storage (in package .data folder)
    print("\nUsing default persistent storage.")
    memory = SQLiteMemory()  # db_path=None uses default
    
    memory.create("This persists between sessions.")
    print(f"DB path: {memory.db_path}")
    print(f"Entries: {len(memory.list_all())}")
    memory.close()
    
    print("\nUsing custom path")
    custom_memory = SQLiteMemory(db_path="./examples/.data/custom_memory.db")
    custom_memory.create("Stored at custom location.")
    print(f"DB path: {custom_memory.db_path}")
    print(f"Entries: {len(custom_memory.list_all())}")
    custom_memory.close()
    
    print("\nPersistent mode demo done")


def main():
    demo_session_mode()
    
    demo_persistent_mode()
    
    print("\nDone")


if __name__ == "__main__":
    main()
