"""SQLite Memory search tests for Pydantic Agent."""
from miminions.memory.sqlite import SQLiteMemory
from miminions.agent import create_pydantic_agent, ExecutionStatus


def setup_agent():
    memory = SQLiteMemory(db_path=":memory:")
    agent = create_pydantic_agent("SearchAgent", memory=memory)
    
    agent.execute("memory_store", text="Python is a programming language", metadata={"type": "language"})
    agent.execute("memory_store", text="Machine learning uses neural networks", metadata={"type": "ai"})
    agent.execute("memory_store", text="SQLite is a database", metadata={"type": "database"})
    agent.execute("memory_store", text="Deep learning requires GPUs", metadata={"type": "ai"})
    
    return agent, memory


def test_vector_search():
    print("test_vector_search")
    agent, memory = setup_agent()
    
    result = agent.execute("memory_recall", query="What is Python?", top_k=2)
    assert result.status == ExecutionStatus.SUCCESS
    assert len(result.result) == 2
    assert "distance" in result.result[0]
    memory.close()


def test_recall_knowledge():
    print("test_recall_knowledge")
    agent, memory = setup_agent()
    
    results = agent.recall_knowledge("artificial intelligence", top_k=2)
    assert len(results) == 2
    memory.close()


def test_memory_context():
    print("test_memory_context")
    agent, memory = setup_agent()
    
    context = agent.get_memory_context("programming", top_k=2)
    
    assert context.query == "programming"
    assert context.count > 0
    assert len(context.results) <= 2
    assert hasattr(context.results[0], 'text')
    memory.close()


def test_execution_timing():
    print("test_execution_timing")
    agent, memory = setup_agent()
    
    result = agent.execute("memory_recall", query="Python", top_k=1)
    assert result.execution_time_ms is not None
    assert result.execution_time_ms >= 0
    memory.close()


if __name__ == "__main__":
    print("Pydantic Agent SQLite Search Tests")
    tests = [test_vector_search, test_recall_knowledge, test_memory_context, test_execution_timing]
    for test in tests:
        test()
    print("All tests passed")
