"""SQLite Memory CRUD Example for Simple Agent."""
from miminions.memory.sqlite import SQLiteMemory


def demo_crud():
    """Demo basic CRUD operations."""
    print("SQLite Memory CRUD Demo\n")
    
    memory = SQLiteMemory(db_path=":memory:")
    
    # Create
    print("Creating entries...")
    id1 = memory.create("Python is a programming language", metadata={"source": "demo"})
    id2 = memory.create("SQLite is a database", metadata={"type": "db"})
    print(f"  Created 2 entries")
    
    # Read
    print("\nReading by ID...")
    entry = memory.get_by_id(id1)
    print(f"  Text: {entry['text']}")
    print(f"  Meta: {entry['meta']}")
    
    # Update
    print("\nUpdating entry...")
    memory.update(id1, "Python is a versatile programming language")
    updated = memory.get_by_id(id1)
    print(f"  New text: {updated['text']}")
    
    # List
    print("\nListing all...")
    print(f"  Total: {len(memory.list_all())} entries")
    
    # Delete
    print("\nDeleting entry...")
    memory.delete(id2)
    print(f"  Remaining: {len(memory.list_all())} entries")
    
    # Clear
    print("\nClearing all...")
    memory.clear()
    print(f"  After clear: {len(memory.list_all())} entries")
    
    memory.close()
    print("\nDone!")


if __name__ == "__main__":
    demo_crud()
