"""FAISS Memory Test Suite."""

import asyncio
import sys
from pathlib import Path

from miminions.agent import create_minion, MemoryQueryResult, MemoryEntry, ExecutionStatus
from miminions.memory.faiss import FAISSMemory


async def test_memory_attachment():
    """Test attaching memory to agent."""
    print("test_memory_attachment")
    agent = create_minion("TestAgent")
    assert agent.get_state().has_memory == False
    
    memory = FAISSMemory(dim=384)
    agent.set_memory(memory)
    assert agent.get_state().has_memory == True
    assert "memory_store" in agent.list_tools()
    
    await agent.cleanup()
    print("PASSED")
    return True


async def test_memory_crud():
    """Test full CRUD operations."""
    print("test_memory_crud")
    memory = FAISSMemory(dim=384)
    agent = create_minion("TestAgent", memory=memory)

    result = agent.execute("memory_store", text="Test knowledge", metadata={"tag": "test"})
    assert result.status == ExecutionStatus.SUCCESS
    entry_id = result.result

    # Read via recall
    result = agent.execute("memory_recall", query="Test knowledge", top_k=1)
    assert len(result.result) > 0

    result = agent.execute("memory_update", id=entry_id, new_text="Updated knowledge")
    assert result.result is True

    # Verify update
    result = agent.execute("memory_get", id=entry_id)
    assert "Updated" in result.result["text"]

    result = agent.execute("memory_list")
    assert len(result.result) >= 1

    result = agent.execute("memory_delete", id=entry_id)
    assert result.result is True

    result = agent.execute("memory_get", id=entry_id)
    assert result.result is None

    await agent.cleanup()
    print("PASSED")
    return True


async def test_convenience_methods():
    """Test store_knowledge and recall_knowledge."""
    print("test_convenience_methods")
    memory = FAISSMemory(dim=384)
    agent = create_minion("TestAgent", memory=memory)

    entry_id = agent.store_knowledge("Python is a programming language", metadata={"topic": "coding"})
    assert entry_id is not None

    results = agent.recall_knowledge("coding languages", top_k=1)
    assert len(results) > 0
    assert "Python" in results[0]["text"]

    await agent.cleanup()
    print("PASSED")
    return True


async def test_memory_context():
    """Test structured memory context retrieval."""
    print("test_memory_context")
    memory = FAISSMemory(dim=384)
    agent = create_minion("TestAgent", memory=memory)

    agent.store_knowledge("Fact about topic X")
    agent.store_knowledge("Another fact about topic X")

    context = agent.get_memory_context("topic X", top_k=2)
    
    assert isinstance(context, MemoryQueryResult)
    assert context.query == "topic X"
    assert context.count > 0
    assert all(isinstance(r, MemoryEntry) for r in context.results)

    await agent.cleanup()
    print("PASSED")
    return True


async def test_no_memory_handling():
    """Test graceful handling when no memory attached."""
    print("test_no_memory_handling")
    agent = create_minion("TestAgent")

    # get_memory_context returns empty result
    context = agent.get_memory_context("query")
    assert context.count == 0
    assert "No memory attached" in context.message

    # store_knowledge raises error
    try:
        agent.store_knowledge("test")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "No memory attached" in str(e)

    await agent.cleanup()
    print("PASSED")
    return True


async def main():
    print("Memory Tests")
    tests = [
        test_memory_attachment,
        test_memory_crud,
        test_convenience_methods,
        test_memory_context,
        test_no_memory_handling,
    ]
    
    passed = 0
    for test in tests:
        try:
            if await test():
                passed += 1
        except Exception as e:
            print(f"FAILED: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{passed}/{len(tests)} tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
