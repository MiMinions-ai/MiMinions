"""Tests for SQLite Memory search operations."""
import sys
from pathlib import Path
from miminions.memory.sqlite import SQLiteMemory

_FILE_DIR = Path(__file__).parent
_DATA_DIR = _FILE_DIR / ".data"
_TEST_DB = _DATA_DIR / "test_search.db"


def cleanup():
    """Remove persistent databases created by tests."""
    if _TEST_DB.exists():
        _TEST_DB.unlink()
    if _DATA_DIR.exists() and not any(_DATA_DIR.iterdir()):
        _DATA_DIR.rmdir()


def setup_memory():
    """Create memory with test data."""
    memory = SQLiteMemory(db_path=":memory:")
    # Generated these test entries with gpt
    memory.create("Python is a programming language", metadata={"type": "language"})
    memory.create("Machine learning uses neural networks", metadata={"type": "ai"})
    memory.create("SQLite is a database", metadata={"type": "database"})
    memory.create("Deep learning requires GPUs", metadata={"type": "ai"})
    return memory


def test_vector_search():
    print("test: vector search")
    memory = setup_memory()
    
    results = memory.read("What is Python?", top_k=2)
    
    assert len(results) == 2
    assert "distance" in results[0]
    assert results[0]["distance"] <= results[1]["distance"]
    
    memory.close()


def test_vector_search_empty():
    print("test: vector search empty")
    memory = SQLiteMemory(db_path=":memory:")
    
    results = memory.read("test query")
    assert results == []
    
    memory.close()


def test_keyword_search():
    print("test: keyword search")
    memory = setup_memory()
    
    results = memory.get_by_keyword("learning")
    assert len(results) == 2
    
    results = memory.get_by_keyword("database")
    assert len(results) == 1
    
    memory.close()


def test_keyword_search_no_results():
    print("test: keyword search no results")
    memory = setup_memory()
    
    results = memory.get_by_keyword("JavaScript")
    assert results == []
    
    memory.close()


def test_full_text_search():
    print("test: full text search")
    memory = setup_memory()
    
    results = memory.full_text_search("programming language")
    assert len(results) == 1
    assert "Python" in results[0]["text"]
    
    memory.close()


def test_full_text_search_no_match():
    print("test: full text search no match")
    memory = setup_memory()
    
    results = memory.full_text_search("quantum physics")
    assert results == []
    
    memory.close()


def test_metadata_search():
    print("test: metadata search")
    memory = setup_memory()
    
    results = memory.metadata_search("type", "ai")
    assert len(results) == 2
    
    results = memory.metadata_search("type", "database")
    assert len(results) == 1
    
    memory.close()


def test_metadata_search_no_match():
    print("test: metadata search no match")
    memory = setup_memory()
    
    results = memory.metadata_search("type", "nonexistent")
    assert results == []
    
    memory.close()


def test_regex_search():
    print("test: regex search")
    memory = setup_memory()
    
    results = memory.regex_search(r".*learning.*")
    assert len(results) == 2
    
    results = memory.regex_search(r"^Python.*")
    assert len(results) == 1
    
    memory.close()


def test_regex_search_no_match():
    print("test: regex search no match")
    memory = setup_memory()
    
    results = memory.regex_search(r"^JavaScript.*")
    assert results == []
    
    memory.close()


def test_hybrid_search():
    print("test: hybrid search")
    memory = setup_memory()
    
    results = memory.hybrid_search("programming")
    assert len(results) > 0
    assert "source" in results[0]
    
    memory.close()


def test_datetime_search():
    print("test: datetime search")
    memory = setup_memory()
    
    results = memory.date_time_search()
    assert len(results) > 0
    assert "created_at" in results[0]
    
    memory.close()


def test_vector_search_ordering():
    print("test: vector search ordering")
    memory = SQLiteMemory(db_path=":memory:")
    
    memory.create("Dogs are mammals")
    memory.create("Cats are mammals")
    memory.create("Computers use electricity")
    
    results = memory.read("What are pets?", top_k=3)
    
    assert len(results) == 3
    assert results[0]["distance"] <= results[1]["distance"]
    assert results[1]["distance"] <= results[2]["distance"]
    
    memory.close()


def main():
    print("\nSQLite Memory Search Tests\n")
    
    tests = [
        test_vector_search,
        test_vector_search_empty,
        test_keyword_search,
        test_keyword_search_no_results,
        test_full_text_search,
        test_full_text_search_no_match,
        test_metadata_search,
        test_metadata_search_no_match,
        test_regex_search,
        test_regex_search_no_match,
        test_hybrid_search,
        test_datetime_search,
        test_vector_search_ordering,
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
