"""SQLite Memory CRUD Example for Simple Agent."""
from miminions.memory.sqlite import SQLiteMemory


def demo_crud():
    print("SQLite Memory CRUD Demo")
    
    memory = SQLiteMemory(db_path=":memory:")
    
    print("Creating entries...")
    id1 = memory.create("Python is a programming language", metadata={"source": "demo"})
    id2 = memory.create("SQLite is a database", metadata={"type": "db"})
    print(f"  Created 2 entries")
    
    print("Reading by ID...")
    entry = memory.get_by_id(id1)
    print(f"  Text: {entry['text']}")
    print(f"  Meta: {entry['meta']}")
    
    print("Updating entry...")
    memory.update(id1, "Python is a versatile programming language")
    updated = memory.get_by_id(id1)
    print(f"  New text: {updated['text']}")
    
    print("Listing all...")
    print(f"  Total: {len(memory.list_all())} entries")
    
    print("Deleting entry...")
    memory.delete(id2)
    print(f"  Remaining: {len(memory.list_all())} entries")
    
    print("Clearing all...")
    memory.clear()
    print(f"  After clear: {len(memory.list_all())} entries")
    
    memory.close()
    print("Done")


if __name__ == "__main__":
    demo_crud()
