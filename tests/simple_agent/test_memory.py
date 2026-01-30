"""Memory Agent Test Suite for Simple Agent."""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from miminions.agent.simple_agent import create_simple_agent
from miminions.memory.faiss import FAISSMemory


async def test_memory_crud():
    """Test CRUD operations through agent tools."""
    print("Testing memory CRUD...")
    memory = FAISSMemory(dim=384)
    agent = create_simple_agent("TestAgent", memory=memory)

    # CREATE
    id1 = agent.execute_tool("memory_store", text="Test knowledge 1")
    assert id1 is not None

    # READ
    results = agent.execute_tool("memory_recall", query="Test knowledge", top_k=1)
    assert len(results) > 0
    assert "Test knowledge 1" in results[0]["text"]

    # UPDATE
    success = agent.execute_tool("memory_update", id=id1, new_text="Updated test knowledge")
    assert success
    updated = agent.execute_tool("memory_get", id=id1)
    assert "Updated" in updated["text"]

    # DELETE
    success = agent.execute_tool("memory_delete", id=id1)
    assert success
    deleted = agent.execute_tool("memory_get", id=id1)
    assert deleted is None

    await agent.cleanup()
    print("PASSED")
    return True


async def test_memory_search():
    """Test semantic search."""
    print("Testing memory search...")
    memory = FAISSMemory(dim=384)
    agent = create_simple_agent("SearchAgent", memory=memory)

    agent.store_knowledge("Python is a programming language")
    agent.store_knowledge("Machine learning uses algorithms")
    agent.store_knowledge("Databases store structured data")

    results = agent.recall_knowledge("coding languages", top_k=1)
    assert len(results) > 0
    assert "Python" in results[0]["text"]

    await agent.cleanup()
    print("PASSED")
    return True


async def test_memory_with_metadata():
    """Test memory with metadata."""
    print("Testing memory metadata...")
    memory = FAISSMemory(dim=384)
    agent = create_simple_agent("MetadataAgent", memory=memory)

    id1 = agent.store_knowledge("Important fact about AI", metadata={"category": "AI", "importance": "high"})
    entry = agent.execute_tool("memory_get", id=id1)
    
    assert entry is not None
    assert entry["meta"]["category"] == "AI"
    assert entry["meta"]["importance"] == "high"

    await agent.cleanup()
    print("PASSED")
    return True


async def test_context_generation():
    """Test context generation for LLM use."""
    print("Testing context generation...")
    memory = FAISSMemory(dim=384)
    agent = create_simple_agent("ContextAgent", memory=memory)

    agent.store_knowledge("Fact A about topic X")
    agent.store_knowledge("Fact B about topic Y")
    agent.store_knowledge("Fact C about topic X")

    context = agent.get_memory_context("topic X", top_k=2)
    
    assert isinstance(context, dict)
    assert "query" in context
    assert "results" in context
    assert context["query"] == "topic X"
    assert context["count"] > 0

    await agent.cleanup()
    print("PASSED")
    return True


async def main():
    print("Simple Agent Memory Tests\n" + "=" * 40)
    tests = [test_memory_crud, test_memory_search, test_memory_with_metadata, test_context_generation]
    
    passed = 0
    for test in tests:
        try:
            if await test():
                passed += 1
        except Exception as e:
            print(f"FAILED: {e}")
    
    print(f"\n{passed}/{len(tests)} tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
