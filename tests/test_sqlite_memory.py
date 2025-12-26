"""Tests for SQLite Memory CRUD operations."""
import tempfile
import sys
from pathlib import Path

from miminions.memory.sqlite import SQLiteMemory

_FILE_DIR = Path(__file__).parent
_DATA_DIR = _FILE_DIR / ".data"
_TEST_DB = _DATA_DIR / "test_crud.db"


def cleanup():
    """Remove persistent databases created by tests."""
    if _TEST_DB.exists():
        _TEST_DB.unlink()
    if _DATA_DIR.exists() and not any(_DATA_DIR.iterdir()):
        _DATA_DIR.rmdir()


def test_create():
    print("test: create")
    memory = SQLiteMemory(db_path=":memory:")
    
    id1 = memory.create("Python is a programming language")
    assert id1 is not None
    assert isinstance(id1, str)
    
    id2 = memory.create("SQLite is a database", metadata={"source": "test"})
    assert id1 != id2
    
    memory.close()


def test_get_by_id():
    print("test: get by id")
    memory = SQLiteMemory(db_path=":memory:")
    
    id = memory.create("Test knowledge", metadata={"tag": "test"})
    entry = memory.get_by_id(id)
    
    assert entry is not None
    assert entry["id"] == id
    assert entry["text"] == "Test knowledge"
    assert entry["meta"]["tag"] == "test"
    
    memory.close()


def test_get_by_id_nonexistent():
    print("test: get nonexistent")
    memory = SQLiteMemory(db_path=":memory:")
    
    entry = memory.get_by_id("fake-id")
    assert entry is None
    
    memory.close()


def test_update():
    print("test: update")
    memory = SQLiteMemory(db_path=":memory:")
    
    id = memory.create("Original text")
    success = memory.update(id, "Updated text")
    
    assert success is True
    entry = memory.get_by_id(id)
    assert entry["text"] == "Updated text"
    
    memory.close()


def test_update_nonexistent():
    print("test: update nonexistent")
    memory = SQLiteMemory(db_path=":memory:")
    
    success = memory.update("fake-id", "New text")
    assert success is False
    
    memory.close()


def test_delete():
    print("test: delete")
    memory = SQLiteMemory(db_path=":memory:")
    
    id = memory.create("Test entry")
    success = memory.delete(id)
    
    assert success is True
    assert memory.get_by_id(id) is None
    
    memory.close()


def test_delete_nonexistent():
    print("test: delete nonexistent")
    memory = SQLiteMemory(db_path=":memory:")
    
    success = memory.delete("fake-id")
    assert success is False
    
    memory.close()


def test_list_all():
    print("test: list all")
    memory = SQLiteMemory(db_path=":memory:")
    
    memory.create("Entry 1")
    memory.create("Entry 2")
    memory.create("Entry 3")
    
    all_entries = memory.list_all()
    assert len(all_entries) == 3
    
    texts = [e["text"] for e in all_entries]
    assert "Entry 1" in texts
    assert "Entry 2" in texts
    assert "Entry 3" in texts
    
    memory.close()


def test_list_all_empty():
    print("test: list empty")
    memory = SQLiteMemory(db_path=":memory:")
    
    assert memory.list_all() == []
    
    memory.close()


def test_clear():
    print("test: clear")
    memory = SQLiteMemory(db_path=":memory:")
    
    memory.create("Entry 1")
    memory.create("Entry 2")
    memory.clear()
    
    assert len(memory.list_all()) == 0
    
    memory.close()


def test_metadata_persistence():
    print("test: metadata")
    memory = SQLiteMemory(db_path=":memory:")
    
    metadata = {"source": "test", "priority": 1, "tags": ["ai", "ml"]}
    id = memory.create("Test with metadata", metadata=metadata)
    
    entry = memory.get_by_id(id)
    assert entry["meta"]["source"] == "test"
    assert entry["meta"]["priority"] == 1
    assert "ai" in entry["meta"]["tags"]
    
    memory.close()


def test_persistent_storage():
    print("test: disk persistence")
    
    db_path = str(_TEST_DB)
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        memory = SQLiteMemory(db_path=db_path)
        id = memory.create("Persistent entry")
        memory.close()
        
        new_memory = SQLiteMemory(db_path=db_path)
        entry = new_memory.get_by_id(id)
        
        assert entry is not None
        assert entry["text"] == "Persistent entry"
        
        new_memory.close()
    finally:
        pass  # cleanup() handles file removal


def test_default_persistent_storage():
    print("test: default storage location")
    
    memory = SQLiteMemory()
    
    assert memory.db_path is not None
    assert ".data" in memory.db_path
    assert memory.db_path.endswith("memory.db")
    
    memory.clear()
    memory.close()


def main():
    print("\nSQLite Memory CRUD Tests\n")
    
    tests = [
        test_create,
        test_get_by_id,
        test_get_by_id_nonexistent,
        test_update,
        test_update_nonexistent,
        test_delete,
        test_delete_nonexistent,
        test_list_all,
        test_list_all_empty,
        test_clear,
        test_metadata_persistence,
        test_persistent_storage,
        test_default_persistent_storage,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            failed += 1
    
    print(f"\n{passed}/{len(tests)} passed")
    cleanup()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
