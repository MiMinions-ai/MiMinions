#!/usr/bin/env python3
"""Pydantic Agent Memory Test Suite"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from miminions.agent import (
    create_pydantic_agent,
    MemoryQueryResult,
    MemoryEntry,
    ExecutionStatus,
)
from miminions.memory.faiss import FAISSMemory


async def test_memory_attachment():
    """Test attaching memory to agent"""
    print("Testing memory attachment")
    
    try:
        agent = create_pydantic_agent("MemTestAgent")
        state1 = agent.get_state()
        assert state1.has_memory == False, "Should start without memory"
        
        # Attach memory
        memory = FAISSMemory(dim=384)
        agent.set_memory(memory)
        
        state2 = agent.get_state()
        assert state2.has_memory == True, "Should have memory after attachment"
        
        # Verify memory tools are registered
        tools = agent.list_tools()
        assert "memory_store" in tools, "memory_store tool should be registered"
        assert "memory_recall" in tools, "memory_recall tool should be registered"
        
        await agent.cleanup()
        print("Memory attachment test passed")
        return True
        
    except Exception as e:
        print(f"Memory attachment test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_memory_initialization():
    """Test creating agent with memory"""
    print("Testing memory initialization")
    
    try:
        memory = FAISSMemory(dim=384)
        agent = create_pydantic_agent("MemInitAgent", memory=memory)
        
        state = agent.get_state()
        assert state.has_memory == True, "Should have memory"
        
        # Verify memory tools
        tools = agent.list_tools()
        memory_tools = ["memory_store", "memory_recall", "memory_update", 
                       "memory_delete", "memory_get", "memory_list", "ingest_document"]
        for tool in memory_tools:
            assert tool in tools, f"{tool} should be registered"
        
        await agent.cleanup()
        print("Memory initialization test passed")
        return True
        
    except Exception as e:
        print(f"Memory initialization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_memory_store_and_recall():
    """Test storing and recalling from memory"""
    print("Testing memory store and recall")
    
    try:
        memory = FAISSMemory(dim=384)
        agent = create_pydantic_agent("StoreRecallAgent", memory=memory)
        
        result = agent.execute(
            "memory_store",
            text="Python is a programming language",
            metadata={"topic": "programming"}
        )
        
        assert result.status == ExecutionStatus.SUCCESS
        assert result.result is not None  # Should return ID
        stored_id = result.result
        
        recall_result = agent.execute("memory_recall", query="programming", top_k=1)
        assert recall_result.status == ExecutionStatus.SUCCESS
        assert len(recall_result.result) >= 1
        assert "Python" in recall_result.result[0]["text"]
        
        await agent.cleanup()
        print("Memory store and recall test passed")
        return True
        
    except Exception as e:
        print(f"Memory store and recall test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_memory_convenience_methods():
    """Test convenience methods for memory operations"""
    print("Testing memory convenience methods")
    
    try:
        memory = FAISSMemory(dim=384)
        agent = create_pydantic_agent("ConvenienceAgent", memory=memory)
        
        entry_id = agent.store_knowledge(
            "Machine learning is part of AI",
            metadata={"category": "AI"}
        )
        assert entry_id is not None
        
        results = agent.recall_knowledge("artificial intelligence", top_k=2)
        assert len(results) >= 1
        assert "Machine learning" in results[0]["text"]
        
        await agent.cleanup()
        print("Memory convenience methods test passed")
        return True
        
    except Exception as e:
        print(f"Memory convenience methods test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_memory_context_structured():
    """Test structured memory context retrieval"""
    print("Testing structured memory context")
    
    try:
        memory = FAISSMemory(dim=384)
        agent = create_pydantic_agent("ContextAgent", memory=memory)
        
        agent.store_knowledge("FAISS is a vector database library")
        agent.store_knowledge("Vectors can represent semantic meaning")
        
        # Get structured context
        context = agent.get_memory_context("vector database", top_k=2)
        
        # Verify it's a Pydantic model
        assert isinstance(context, MemoryQueryResult), "Should return MemoryQueryResult"
        assert context.query == "vector database", "Query should be preserved"
        assert context.count > 0, "Should have results"
        assert len(context.results) == context.count, "Count should match results"
        
        # Verify entries are MemoryEntry
        for entry in context.results:
            assert isinstance(entry, MemoryEntry), "Results should be MemoryEntry"
            assert hasattr(entry, "text"), "Entry should have text"
            assert hasattr(entry, "metadata"), "Entry should have metadata"
        
        await agent.cleanup()
        print("Structured memory context test passed")
        return True
        
    except Exception as e:
        print(f"Structured memory context test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_memory_context_empty():
    """Test memory context with no results"""
    print("Testing empty memory context")
    
    try:
        memory = FAISSMemory(dim=384)
        agent = create_pydantic_agent("EmptyContextAgent", memory=memory)
        
        # Get context without storing anything
        context = agent.get_memory_context("nonexistent query", top_k=5)
        
        assert isinstance(context, MemoryQueryResult)
        assert context.count == 0
        assert len(context.results) == 0
        assert context.message is not None
        
        await agent.cleanup()
        print("Empty memory context test passed")
        return True
        
    except Exception as e:
        print(f"Empty memory context test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_memory_context_no_memory():
    """Test memory context when no memory is attached"""
    print("Testing memory context without memory")
    
    try:
        agent = create_pydantic_agent("NoMemAgent")
        
        # Get context without memory attached
        context = agent.get_memory_context("any query")
        
        assert isinstance(context, MemoryQueryResult)
        assert context.count == 0
        assert "No memory attached" in context.message
        
        await agent.cleanup()
        print("Memory context without memory test passed")
        return True
        
    except Exception as e:
        print(f"Memory context without memory test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_memory_crud_operations():
    """Test full CRUD operations on memory"""
    print("Testing memory CRUD operations")
    
    try:
        memory = FAISSMemory(dim=384)
        agent = create_pydantic_agent("CRUDAgent", memory=memory)
        
        # Create
        create_result = agent.execute(
            "memory_store",
            text="Original text",
            metadata={"version": 1}
        )
        assert create_result.status == ExecutionStatus.SUCCESS
        entry_id = create_result.result
        
        # Read (via recall)
        recall_result = agent.execute("memory_recall", query="Original", top_k=1)
        assert recall_result.status == ExecutionStatus.SUCCESS
        assert len(recall_result.result) >= 1
        
        # Update
        update_result = agent.execute(
            "memory_update",
            id=entry_id,
            new_text="Updated text"
        )
        assert update_result.status == ExecutionStatus.SUCCESS
        assert update_result.result == True
        
        # Verify update
        recall_result2 = agent.execute("memory_recall", query="Updated", top_k=1)
        assert "Updated text" in recall_result2.result[0]["text"]
        
        # List
        list_result = agent.execute("memory_list")
        assert list_result.status == ExecutionStatus.SUCCESS
        assert len(list_result.result) >= 1
        
        # Delete
        delete_result = agent.execute("memory_delete", id=entry_id)
        assert delete_result.status == ExecutionStatus.SUCCESS
        
        await agent.cleanup()
        print("Memory CRUD operations test passed")
        return True
        
    except Exception as e:
        print(f"Memory CRUD operations test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_memory_error_without_attachment():
    """Test memory operations fail gracefully without memory"""
    print("Testing memory error handling")
    
    try:
        agent = create_pydantic_agent("NoMemErrorAgent")
        
        # Try to store without memory (using execute_tool which raises)
        try:
            agent.store_knowledge("test")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "No memory attached" in str(e)
        
        await agent.cleanup()
        print("Memory error handling test passed")
        return True
        
    except Exception as e:
        print(f"Memory error handling test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all memory tests"""
    print("Running Pydantic Agent Memory Tests")
    
    tests = [
        test_memory_attachment,
        test_memory_initialization,
        test_memory_store_and_recall,
        test_memory_convenience_methods,
        test_memory_context_structured,
        test_memory_context_empty,
        test_memory_context_no_memory,
        test_memory_crud_operations,
        test_memory_error_without_attachment,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if await test():
                passed += 1
        except Exception as e:
            print(f"Test {test.__name__} crashed: {e}")
    
    print(f"\nTests completed: {passed}/{total} passed")
    
    if passed == total:
        print("All tests passed")
        return 0
    else:
        print("Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
