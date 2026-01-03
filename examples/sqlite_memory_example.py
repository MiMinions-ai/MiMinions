"""SQLite Memory CRUD Example"""
from pathlib import Path
from miminions.memory.sqlite import SQLiteMemory

_FILE_DIR = Path(__file__).parent
_DATA_DIR = _FILE_DIR / ".data"
_CUSTOM_DB = _DATA_DIR / "custom.db"

# Default database location
_DEFAULT_DB_DIR = Path(__file__).parent.parent / "src" / "miminions" / "memory" / ".data"
_DEFAULT_DB = _DEFAULT_DB_DIR / "memory.db"


def cleanup():
    """Remove persistent databases created by this demo."""
    if _CUSTOM_DB.exists():
        _CUSTOM_DB.unlink()
    if _DATA_DIR.exists() and not any(_DATA_DIR.iterdir()):
        _DATA_DIR.rmdir()
    # Clean up default database
    if _DEFAULT_DB.exists():
        _DEFAULT_DB.unlink()
    if _DEFAULT_DB_DIR.exists() and not any(_DEFAULT_DB_DIR.iterdir()):
        _DEFAULT_DB_DIR.rmdir()


def demo_crud():
    """Demo basic CRUD operations."""
    print("SQLite Memory CRUD Demo\n")
    
    memory = SQLiteMemory(db_path=":memory:")
    
    print("Creating entries")
    id1 = memory.create("Python is a programming language", metadata={"source": "demo"})
    id2 = memory.create("SQLite is a database", metadata={"type": "db"})
    print(f"  Created 2 entries")
    
    print("\nReading by ID")
    entry = memory.get_by_id(id1)
    print(f"  ID: {id1[:8]}")
    print(f"  Text: {entry['text']}")
    print(f"  Meta: {entry['meta']}")
    
    print("\nUpdating entry")
    memory.update(id1, "Python is a versatile programming language")
    updated = memory.get_by_id(id1)
    print(f"  New text: {updated['text']}")
    
    print("\nListing all")
    all_entries = memory.list_all()
    print(f"  Total: {len(all_entries)} entries")
    
    print("\nDeleting entry")
    memory.delete(id2)
    print(f"  Remaining: {len(memory.list_all())} entries")
    
    print("\nClearing all")
    memory.clear()
    print(f"  After clear: {len(memory.list_all())} entries")
    
    memory.close()
    print("\nDone")


def demo_persistent():
    """Demo persistent storage options."""
    print("\nPersistent Storage Demo\n")
    
    print("Default storage:")
    memory = SQLiteMemory()
    memory.create("Persists between sessions")
    print(f"  Path: {memory.db_path}")
    print(f"  Entries: {len(memory.list_all())}")
    memory.close()
    
    print("\nCustom storage:")
    custom = SQLiteMemory(db_path=str(_CUSTOM_DB))
    custom.create("Custom location")
    print(f"  Path: {custom.db_path}")
    custom.close()
    
    print("\nDone")


if __name__ == "__main__":
    demo_crud()
    demo_persistent()
    cleanup()
