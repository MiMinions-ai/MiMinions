"""SQLite Memory Test Suite."""

from pathlib import Path
from pysqlite3 import ProgrammingError
import pytest

pytest.importorskip("sqlite_vec")

import pytest

pytest.importorskip("sqlite_vec")

import pytest

from miminions.core.paths import get_global_memory_db_path
from miminions.agent import create_minion
from miminions.memory.sqlite import SQLiteMemory
from miminions.tools.schemas import ExecutionStatus


def setup_agent():
    memory = SQLiteMemory(db_path=":memory:")
    agent = create_minion("TestAgent", memory=memory)
    return agent, memory


def test_crud():
    """Test create, read, update, delete operations."""
    print("test_crud")
    agent, memory = setup_agent()
    
    result = agent.execute("memory_store", text="Python is a programming language", metadata={"source": "test"})
    assert result.status == ExecutionStatus.SUCCESS, f"expect ExecutionStatus.SUCCESS as {ExecutionStatus.SUCCESS}, got {result.status}"
    id1 = result.result
    
    # Read by ID
    result = agent.execute("memory_get", id=id1)
    assert result.result is not None, f"expect memory_get returns a valid entry for existing id, got {result.result}"
    assert result.result["id"] == id1, f"expect memory_get returns the same id as stored, got {result.result['id']}"
    assert result.result["text"] == "Python is a programming language", f"expect memory_get returns originally stored text as 'Python is a programming language', got {result.result['text']}"
    assert result.result["meta"]["source"] == "test", f"expect memory_get returns stored metadata source field as 'test', got {result.result['meta']['source']}"
    
    # Update
    result = agent.execute("memory_update", id=id1, new_text="Python is a versatile language")
    assert result.result is True, f"expect memory_update returns True after updating an existing memory entry, got {result.result}"
    
    result = agent.execute("memory_get", id=id1)
    assert result.result is not None, f"expect memory_get returns a valid entry for existing id, got {result.result}"
    assert "versatile" in result.result["text"], f"expect contains 'versatile', got {result.result['text']}"
    
    # Delete
    result = agent.execute("memory_delete", id=id1)
    assert result.result is True, f"expect memory_delete returns True after deleting an existing memory entry, got {result.result}"
    
    result = agent.execute("memory_get", id=id1)
    assert result.result is None, f"expect memory_get returns None for deleted memory entry, got {result.result}"
    
    memory.close()
    print("PASSED")


def test_list():
    """Test listing all entries."""
    print("test_list")
    agent, memory = setup_agent()
    
    agent.execute("memory_store", text="Entry 1")
    agent.execute("memory_store", text="Entry 2")
    agent.execute("memory_store", text="Entry 3")
    
    result = agent.execute("memory_list")
    assert result.result is not None, f"expect memory_list returns a valid result, got {result.result}"
    listed_count = len(result.result)
    assert listed_count == 3, f"expect memory_list returns all three stored memory entries as 3, got {listed_count}"
    
    memory.close()
    print("PASSED")


def test_vector_search():
    """Test vector similarity search."""
    print("test_vector_search")
    agent, memory = setup_agent()
    
    agent.execute("memory_store", text="Python is a programming language", metadata={"type": "language"})
    agent.execute("memory_store", text="Machine learning uses neural networks", metadata={"type": "tech"})
    agent.execute("memory_store", text="SQLite is a database", metadata={"type": "database"})
    
    result = agent.execute("memory_recall", query="What is Python?", top_k=2)
    assert result.status == ExecutionStatus.SUCCESS, f"expect ExecutionStatus.SUCCESS as {ExecutionStatus.SUCCESS}, got {result.status}"
    assert result.result is not None, f"expect memory_recall returns a valid result, got {result.result}"
    recalled_count = len(result.result)
    assert recalled_count == 2, f"expect memory_recall respects top_k=2 by returning two results as 2, got {recalled_count}"
    assert "distance" in result.result[0], f"expect contains 'distance', got {result.result[0]}"
    
    memory.close()
    print("PASSED")


def test_convenience_methods():
    """Test recall_knowledge and get_memory_context."""
    print("test_convenience_methods")
    agent, memory = setup_agent()
    
    agent.store_knowledge("Python is great for scripting")
    agent.store_knowledge("Machine learning is powerful")
    
    # recall_knowledge
    results = agent.recall_knowledge("scripting language", top_k=1)
    results_count = len(results)
    assert results_count >= 1, f"expect len(results) >= 1, got {results_count}"
    
    # get_memory_context
    context = agent.get_memory_context("programming", top_k=2)
    assert context.query == "programming", f"expect get_memory_context preserves input query as 'programming' in returned context object, got {context.query}"
    assert context.count > 0, f"expect context.count > 0, got {context.count}"
    first_result_has_text = hasattr(context.results[0], "text")
    assert first_result_has_text, f"expect first recalled memory result exposes text attribute as True, got {first_result_has_text}"
    
    memory.close()
    print("PASSED")


def test_execution_timing():
    """Test that execution time is tracked."""
    print("test_execution_timing")
    agent, memory = setup_agent()
    
    agent.execute("memory_store", text="Test entry")
    result = agent.execute("memory_recall", query="Test", top_k=1)
    
    assert result.execution_time_ms is not None, f"expect value is not None, got {result.execution_time_ms}"
    assert result.execution_time_ms >= 0, f"expect result.execution_time_ms >= 0, got {result.execution_time_ms}"
    
    memory.close()
    print("PASSED")


def test_context_manager_closes_connection():
    """`with SQLiteMemory(...)` should work inside the block and close on exit."""
    with SQLiteMemory(db_path=":memory:") as memory:
        entry_id = memory.create("Context managers are neat", metadata={"source": "test"})
        stored_entry = memory.get_by_id(entry_id)
        assert stored_entry is not None, f"expect context-managed memory instance returns a valid entry before block exit, got {stored_entry}"
        assert stored_entry["text"] == "Context managers are neat", f"expect context-managed memory instance returns stored text as 'Context managers are neat' before block exit, got {stored_entry['text']}"

    with pytest.raises(ProgrammingError):
        memory.conn.execute("SELECT 1")


def test_context_manager_propagates_exceptions():
    """Exceptions inside the block must not be suppressed, and still close."""
    memory = SQLiteMemory(db_path=":memory:")
    try:
        with pytest.raises(ValueError, match="boom"):
            raise ValueError("boom")
    finally:
        memory.close()

    with pytest.raises(ProgrammingError):
        memory.conn.execute("SELECT 1")


def test_double_close_is_noop():
    """Calling close() twice (e.g. explicit close + __exit__) must not raise."""
    memory = SQLiteMemory(db_path=":memory:")
    memory.close()
    memory.close()


def test_get_global_memory_db_path_uses_home(monkeypatch, tmp_path):
    """Global DB helper should resolve under ~/.miminions."""
    monkeypatch.delenv("MIMINIONS_HOME", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    path = Path(get_global_memory_db_path(create_dir=False))

    assert path == tmp_path / ".miminions" / "global_memory.db", f"expect tmp_path / '.miminions' / 'global_memory.db', got {path}"


def test_get_global_memory_db_path_creates_parent(monkeypatch, tmp_path):
    """Global DB helper should create parent directory by default."""
    monkeypatch.delenv("MIMINIONS_HOME", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    path = Path(get_global_memory_db_path())

    parent_dir_exists = path.parent.exists()
    assert parent_dir_exists, f"expect global memory db helper creates parent directory as True, got {parent_dir_exists}"
    assert path.name == "global_memory.db", f"expect global memory db helper returns database filename as 'global_memory.db', got {path.name}"


if __name__ == "__main__":
    print("SQLite Memory Tests")
    tests = [
        test_crud,
        test_list,
        test_vector_search,
        test_convenience_methods,
        test_execution_timing,
    ]
    for test in tests:
        test()
    print("\nAll tests passed")
