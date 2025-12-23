import tempfile
import sys
from pathlib import Path

from miminions.memory.sqlite import SQLiteMemory

def test_create():
    print("test: create")
    memory = SQLiteMemory(db_path=":memory:")
    
    id1 = memory.create("Python is a programming language")
    assert id1 is not None, "Failed to create entry"
    assert isinstance(id1, str), "ID should be a string"
    
    id2 = memory.create("SQLite is a database", metadata={"source": "test"})
    assert id2 is not None, "Failed to create entry with metadata"
    assert id1 != id2, "IDs should be unique"
    
    memory.close()


def test_read_vector_search():
    print("test: vector search")
    memory = SQLiteMemory(db_path=":memory:")
    
    memory.create("Python is a programming language")
    memory.create("Machine learning uses neural networks")
    memory.create("SQLite is a database")
    
    results = memory.read("What is Python?", top_k=2)
    
    assert len(results) == 2, f"Expected 2 results, got {len(results)}"
    assert "Python" in results[0]["text"], "Top result should mention Python"
    assert "distance" in results[0], "Result should have distance"
    assert results[0]["distance"] <= results[1]["distance"], "Results should be ordered by distance"
    
    memory.close()


def test_read_empty_database():
    print("test: empty db read")
    memory = SQLiteMemory(db_path=":memory:")
    
    results = memory.read("test query")
    assert results == [], "Empty database should return empty list"
    
    memory.close()


def test_update():
    print("test: update")
    memory = SQLiteMemory(db_path=":memory:")
    
    id = memory.create("Original text")
    
    success = memory.update(id, "Updated text")
    assert success is True, "Update should succeed"
    
    entry = memory.get_by_id(id)
    assert entry["text"] == "Updated text", "Text should be updated"
    
    memory.close()


def test_update_nonexistent():
    print("test: update nonexistent")
    memory = SQLiteMemory(db_path=":memory:")
    
    success = memory.update("fake-id", "New text")
    assert success is False, "Update of non-existent entry should fail"
    
    memory.close()


def test_delete():
    print("test: delete")
    memory = SQLiteMemory(db_path=":memory:")
    
    id = memory.create("Test entry")
    
    success = memory.delete(id)
    assert success is True, "Delete should succeed"
    
    entry = memory.get_by_id(id)
    assert entry is None, "Entry should be deleted"
    
    memory.close()


def test_delete_nonexistent():
    print("test: delete nonexistent")
    memory = SQLiteMemory(db_path=":memory:")
    
    success = memory.delete("fake-id")
    assert success is False, "Delete of non-existent entry should fail"
    
    memory.close()


def test_get_by_id():
    print("test: get by id")
    memory = SQLiteMemory(db_path=":memory:")
    
    id = memory.create("Test knowledge", metadata={"tag": "test"})
    
    entry = memory.get_by_id(id)
    assert entry is not None, "Entry should exist"
    assert entry["id"] == id, "ID should match"
    assert entry["text"] == "Test knowledge", "Text should match"
    assert entry["meta"]["tag"] == "test", "Metadata should match"
    
    memory.close()


def test_get_by_id_nonexistent():
    print("test: get nonexistent")
    memory = SQLiteMemory(db_path=":memory:")
    
    entry = memory.get_by_id("fake-id")
    assert entry is None, "Non-existent entry should return None"
    
    memory.close()


def test_list_all():
    print("test: list all")
    memory = SQLiteMemory(db_path=":memory:")
    
    memory.create("Entry 1")
    memory.create("Entry 2")
    memory.create("Entry 3")
    
    all_entries = memory.list_all()
    assert len(all_entries) == 3, f"Expected 3 entries, got {len(all_entries)}"
    
    texts = [e["text"] for e in all_entries]
    assert "Entry 1" in texts, "Entry 1 should be in list"
    assert "Entry 2" in texts, "Entry 2 should be in list"
    assert "Entry 3" in texts, "Entry 3 should be in list"
    
    memory.close()


def test_list_all_empty():
    print("test: list empty")
    memory = SQLiteMemory(db_path=":memory:")
    
    all_entries = memory.list_all()
    assert all_entries == [], "Empty database should return empty list"
    
    memory.close()


def test_clear():
    print("test: clear")
    memory = SQLiteMemory(db_path=":memory:")
    
    memory.create("Entry 1")
    memory.create("Entry 2")
    memory.create("Entry 3")
    
    memory.clear()
    
    all_entries = memory.list_all()
    assert len(all_entries) == 0, "Database should be empty after clear"
    
    memory.close()


def test_search_keyword():
    print("test: keyword search")
    memory = SQLiteMemory(db_path=":memory:")
    
    memory.create("Python programming language")
    memory.create("Machine learning with Python")
    memory.create("SQLite database")
    
    results = memory.search_keyword("Python")
    assert len(results) == 2, f"Expected 2 results for 'Python', got {len(results)}"
    
    results = memory.search_keyword("database")
    assert len(results) == 1, f"Expected 1 result for 'database', got {len(results)}"
    assert "SQLite" in results[0]["text"], "Result should contain SQLite"
    
    memory.close()


def test_search_keyword_no_results():
    print("test: keyword search (no results)")
    memory = SQLiteMemory(db_path=":memory:")
    
    memory.create("Python programming")
    
    results = memory.search_keyword("JavaScript")
    assert results == [], "No matches should return empty list"
    
    memory.close()


def test_metadata_persistence():
    print("test: metadata")
    memory = SQLiteMemory(db_path=":memory:")
    
    metadata = {"source": "test", "priority": 1, "tags": ["ai", "ml"]}
    id = memory.create("Test with metadata", metadata=metadata)
    
    entry = memory.get_by_id(id)
    assert entry["meta"]["source"] == "test", "Metadata source should match"
    assert entry["meta"]["priority"] == 1, "Metadata priority should match"
    assert "ai" in entry["meta"]["tags"], "Metadata tags should contain 'ai'"
    
    memory.close()


def test_vector_search_ordering():
    print("test: search ordering")
    memory = SQLiteMemory(db_path=":memory:")
    
    memory.create("Dogs are mammals")
    memory.create("Cats are mammals")
    memory.create("Computers use electricity")
    
    results = memory.read("What are pets?", top_k=3)
    
    assert len(results) == 3, f"Expected 3 results, got {len(results)}"
    assert results[0]["distance"] <= results[1]["distance"], "Results should be ordered"
    assert results[1]["distance"] <= results[2]["distance"], "Results should be ordered"
    
    memory.close()


def test_update_with_vector_recomputation():
    print("test: vector recompute")
    memory = SQLiteMemory(db_path=":memory:")
    
    id = memory.create("Original about cats")
    
    results = memory.read("feline animals", top_k=1)
    assert results[0]["id"] == id, "Should find the cat entry"
    
    memory.update(id, "Quantum physics theories")
    
    results = memory.read("feline animals", top_k=1)
    old_distance = results[0]["distance"]
    
    results = memory.read("quantum mechanics", top_k=1)
    new_distance = results[0]["distance"]
    
    assert new_distance < old_distance, "Updated embedding should be closer to new query"
    
    memory.close()


def test_persistent_storage():
    print("test: disk persistence")
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    try:
        memory = SQLiteMemory(db_path=db_path)
        id = memory.create("Persistent entry")
        memory.close()
        
        new_memory = SQLiteMemory(db_path=db_path)
        entry = new_memory.get_by_id(id)
        
        assert entry is not None, "Entry should persist to disk"
        assert entry["text"] == "Persistent entry", "Text should match"
        
        new_memory.close()
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_default_persistent_storage():
    print("test: default storage location")
    
    memory = SQLiteMemory()
    
    assert memory.db_path is not None, "Should have a db_path"
    assert ".data" in memory.db_path, "Should use .data folder"
    assert memory.db_path.endswith("memory.db"), "Should use memory.db filename"
    
    id = memory.create("Default location test")
    entry = memory.get_by_id(id)
    assert entry is not None, "Entry should exist"
    
    memory.clear()
    memory.close()


def main():
    print("\nRunning SQLite memory tests\n")
    print("SESSION MODE TESTS")
    
    session_tests = [
        test_create,
        test_read_vector_search,
        test_read_empty_database,
        test_update,
        test_update_nonexistent,
        test_delete,
        test_delete_nonexistent,
        test_get_by_id,
        test_get_by_id_nonexistent,
        test_list_all,
        test_list_all_empty,
        test_clear,
        test_search_keyword,
        test_search_keyword_no_results,
        test_metadata_persistence,
        test_vector_search_ordering,
        test_update_with_vector_recomputation,
    ]
    
    persistent_tests = [
        test_persistent_storage,
        test_default_persistent_storage,
    ]
    
    passed = 0
    failed = 0
    
    for test in session_tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"{test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"{test.__name__} crashed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\nPersistent storage tests")
    
    for test in persistent_tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"{test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"{test.__name__} crashed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    total = len(session_tests) + len(persistent_tests)
    print(f"\n{passed}/{total} passed")
    
    if failed == 0:
        print("All tests passed")
        return 0
    else:
        print(f"{failed} failed")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
