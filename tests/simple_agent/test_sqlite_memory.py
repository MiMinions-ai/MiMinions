"""SQLite Memory CRUD tests for Simple Agent."""
from pathlib import Path
from miminions.memory.sqlite import SQLiteMemory


def test_create():
    print("test: create")
    memory = SQLiteMemory(db_path=":memory:")
    id1 = memory.create("Python is a programming language")
    assert id1 is not None
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


def test_update():
    print("test: update")
    memory = SQLiteMemory(db_path=":memory:")
    id = memory.create("Original text")
    success = memory.update(id, "Updated text")
    assert success is True
    entry = memory.get_by_id(id)
    assert entry["text"] == "Updated text"
    memory.close()


def test_delete():
    print("test: delete")
    memory = SQLiteMemory(db_path=":memory:")
    id = memory.create("Test entry")
    success = memory.delete(id)
    assert success is True
    assert memory.get_by_id(id) is None
    memory.close()


def test_list_all():
    print("test: list all")
    memory = SQLiteMemory(db_path=":memory:")
    memory.create("Entry 1")
    memory.create("Entry 2")
    memory.create("Entry 3")
    all_entries = memory.list_all()
    assert len(all_entries) == 3
    memory.close()


def test_clear():
    print("test: clear")
    memory = SQLiteMemory(db_path=":memory:")
    memory.create("Entry 1")
    memory.create("Entry 2")
    memory.clear()
    assert len(memory.list_all()) == 0
    memory.close()


if __name__ == "__main__":
    print("SQLite Memory CRUD Tests\n" + "=" * 40)
    tests = [test_create, test_get_by_id, test_update, test_delete, test_list_all, test_clear]
    for test in tests:
        test()
    print("\nAll tests passed!")
