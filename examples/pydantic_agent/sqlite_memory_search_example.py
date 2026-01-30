"""SQLite Memory Search Example for Pydantic Agent."""
from miminions.memory.sqlite import SQLiteMemory
from miminions.agent.pydantic_agent import create_pydantic_agent


def setup_agent():
    memory = SQLiteMemory(db_path=":memory:")
    agent = create_pydantic_agent("SearchAgent", memory=memory)
    
    facts = [
        ("Python is a high-level programming language.", {"type": "language"}),
        ("Machine learning uses neural networks.", {"type": "ai"}),
        ("SQLite is a lightweight database.", {"type": "database"}),
        ("JavaScript runs in browsers.", {"type": "language"}),
        ("Deep learning requires GPUs.", {"type": "ai"}),
    ]
    for text, meta in facts:
        agent.execute("memory_store", text=text, metadata=meta)
    
    return agent, memory


def demo_searches():
    print("Pydantic Agent SQLite Memory Search Demo\n")
    agent, memory = setup_agent()
    
    # Using execute() - returns ToolExecutionResult
    print("Vector Search (via execute):")
    result = agent.execute("memory_recall", query="What is artificial intelligence?", top_k=2)
    print(f"  Status: {result.status.value}")
    print(f"  Time: {result.execution_time_ms:.2f}ms")
    for r in result.result:
        print(f"  - {r['text']} (dist: {r['distance']:.3f})")
    
    # Using recall_knowledge() - returns raw list
    print("\nRecall Knowledge (convenience method):")
    results = agent.recall_knowledge("programming", top_k=2)
    for r in results:
        print(f"  - {r['text']}")
    
    # Using get_memory_context() - returns MemoryQueryResult model
    print("\nMemory Context (Pydantic model):")
    context = agent.get_memory_context("learning", top_k=2)
    print(f"  Query: {context.query}")
    print(f"  Count: {context.count}")
    for entry in context.results:
        print(f"  - ID: {entry.id[:8]}... Text: {entry.text}")
    
    memory.close()
    print("\nDone!")


if __name__ == "__main__":
    demo_searches()
