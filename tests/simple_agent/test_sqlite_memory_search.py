"""SQLite Memory search tests for Simple Agent."""
from miminions.memory.sqlite import SQLiteMemory


def setup_memory():
    memory = SQLiteMemory(db_path=":memory:")
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
    memory.close()


def test_keyword_search():
    print("test: keyword search")
    memory = setup_memory()
    results = memory.get_by_keyword("learning")
    assert len(results) == 2
    memory.close()


def test_full_text_search():
    print("test: full text search")
    memory = setup_memory()
    results = memory.full_text_search("programming language")
    assert len(results) == 1
    assert "Python" in results[0]["text"]
    memory.close()


def test_metadata_search():
    print("test: metadata search")
    memory = setup_memory()
    results = memory.metadata_search("type", "ai")
    assert len(results) == 2
    memory.close()


def test_regex_search():
    print("test: regex search")
    memory = setup_memory()
    results = memory.regex_search(r".*learning.*")
    assert len(results) == 2
    memory.close()


def test_hybrid_search():
    print("test: hybrid search")
    memory = setup_memory()
    results = memory.hybrid_search("programming")
    assert len(results) > 0
    memory.close()


if __name__ == "__main__":
    print("SQLite Memory Search Tests")
    tests = [test_vector_search, test_keyword_search, test_full_text_search, 
             test_metadata_search, test_regex_search, test_hybrid_search]
    for test in tests:
        test()
    print("All tests passed")
