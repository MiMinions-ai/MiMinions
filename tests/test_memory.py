"""Memory Agent Test Suite for Pydantic Agent."""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from miminions.agent import create_pydantic_agent, ExecutionStatus
from miminions.memory.faiss import FAISSMemory


async def test_memory_crud():
    print("test_memory_crud")
    memory = FAISSMemory(dim=384)
    agent = create_pydantic_agent("TestAgent", memory=memory)

    result = agent.execute("memory_store", text="Test knowledge 1")
    assert result.status == ExecutionStatus.SUCCESS
    id1 = result.result

    result = agent.execute("memory_recall", query="Test knowledge", top_k=1)
    assert result.status == ExecutionStatus.SUCCESS
    assert len(result.result) > 0
    assert "Test knowledge 1" in result.result[0]["text"]

    result = agent.execute("memory_update", id=id1, new_text="Updated test knowledge")
    assert result.status == ExecutionStatus.SUCCESS
    assert result.result is True

    result = agent.execute("memory_get", id=id1)
    assert "Updated" in result.result["text"]

    result = agent.execute("memory_delete", id=id1)
    assert result.result is True

    result = agent.execute("memory_get", id=id1)
    assert result.result is None

    await agent.cleanup()
    print("PASSED")
    return True


async def test_memory_search():
    print("test_memory_search")
    memory = FAISSMemory(dim=384)
    agent = create_pydantic_agent("SearchAgent", memory=memory)

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
    print("test_memory_with_metadata")
    memory = FAISSMemory(dim=384)
    agent = create_pydantic_agent("MetadataAgent", memory=memory)

    agent.store_knowledge("Important fact about AI", metadata={"category": "AI", "importance": "high"})
    
    result = agent.execute("memory_list")
    entries = result.result
    assert len(entries) > 0
    assert entries[0]["meta"]["category"] == "AI"

    await agent.cleanup()
    print("PASSED")
    return True


async def test_context_generation():
    print("test_context_generation")
    memory = FAISSMemory(dim=384)
    agent = create_pydantic_agent("ContextAgent", memory=memory)

    agent.store_knowledge("Fact A about topic X")
    agent.store_knowledge("Fact B about topic Y")
    agent.store_knowledge("Fact C about topic X")

    context = agent.get_memory_context("topic X", top_k=2)
    
    assert context.query == "topic X"
    assert context.count > 0
    assert len(context.results) <= 2
    assert all(hasattr(r, 'id') and hasattr(r, 'text') for r in context.results)

    await agent.cleanup()
    print("PASSED")
    return True


async def test_execution_result():
    print("test_execution_result")
    memory = FAISSMemory(dim=384)
    agent = create_pydantic_agent("ResultAgent", memory=memory)

    result = agent.execute("memory_store", text="Test")
    
    assert result.tool_name == "memory_store"
    assert result.status == ExecutionStatus.SUCCESS
    assert result.result is not None
    assert result.execution_time_ms is not None

    await agent.cleanup()
    print("PASSED")
    return True


async def main():
    print("Pydantic Agent Memory Tests")
    tests = [
        test_memory_crud, 
        test_memory_search, 
        test_memory_with_metadata, 
        test_context_generation,
        test_execution_result,
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
