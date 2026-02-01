"""SQLite Memory Test Suite."""

from miminions.memory.sqlite import SQLiteMemory
from miminions.agent import create_pydantic_agent, ExecutionStatus


def setup_agent():
    memory = SQLiteMemory(db_path=":memory:")
    agent = create_pydantic_agent("TestAgent", memory=memory)
    return agent, memory


def test_crud():
    """Test create, read, update, delete operations."""
    print("test_crud")
    agent, memory = setup_agent()
    
    result = agent.execute("memory_store", text="Python is a programming language", metadata={"source": "test"})
    assert result.status == ExecutionStatus.SUCCESS
    id1 = result.result
    
    # Read by ID
    result = agent.execute("memory_get", id=id1)
    assert result.result["text"] == "Python is a programming language"
    assert result.result["meta"]["source"] == "test"
    
    # Update
    result = agent.execute("memory_update", id=id1, new_text="Python is a versatile language")
    assert result.result is True
    
    result = agent.execute("memory_get", id=id1)
    assert "versatile" in result.result["text"]
    
    # Delete
    result = agent.execute("memory_delete", id=id1)
    assert result.result is True
    
    result = agent.execute("memory_get", id=id1)
    assert result.result is None
    
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
    assert len(result.result) == 3
    
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
    assert result.status == ExecutionStatus.SUCCESS
    assert len(result.result) == 2
    assert "distance" in result.result[0]
    
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
    assert len(results) >= 1
    
    # get_memory_context
    context = agent.get_memory_context("programming", top_k=2)
    assert context.query == "programming"
    assert context.count > 0
    assert hasattr(context.results[0], 'text')
    
    memory.close()
    print("PASSED")


def test_execution_timing():
    """Test that execution time is tracked."""
    print("test_execution_timing")
    agent, memory = setup_agent()
    
    agent.execute("memory_store", text="Test entry")
    result = agent.execute("memory_recall", query="Test", top_k=1)
    
    assert result.execution_time_ms is not None
    assert result.execution_time_ms >= 0
    
    memory.close()
    print("PASSED")


if __name__ == "__main__":
    print("SQLite Memory Tests")
    tests = [test_crud, test_list, test_vector_search, test_convenience_methods, test_execution_timing]
    for test in tests:
        test()
    print("\nAll tests passed")
