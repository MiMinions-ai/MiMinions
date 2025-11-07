"""
Memory Agent Test Suite

Tests for agent memory integration and CRUD operations.
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from miminions.agent.simple_agent import create_simple_agent
from miminions.memory.faiss import FAISSMemory


async def test_memory_crud():
    """Test basic CRUD operations through agent tools"""
    print("Testing memory CRUD operations")
    
    try:
        memory = FAISSMemory(dim=384)
        agent = create_simple_agent("TestAgent", memory=memory)
        
        # CREATE
        id1 = agent.execute_tool("memory_store", text="Test knowledge 1")
        assert id1 is not None, "Failed to create memory entry"
        
        # READ
        results = agent.execute_tool("memory_recall", query="Test knowledge", top_k=1)
        assert len(results) > 0, "Failed to recall memory"
        assert "Test knowledge 1" in results[0]["text"], "Recalled wrong content"
        
        # UPDATE
        success = agent.execute_tool("memory_update", id=id1, new_text="Updated test knowledge")
        assert success, "Failed to update memory"
        
        # Verify update
        updated = agent.execute_tool("memory_get", id=id1)
        assert updated is not None, "Failed to get updated entry"
        assert "Updated" in updated["text"], "Update not reflected"
        
        # DELETE
        success = agent.execute_tool("memory_delete", id=id1)
        assert success, "Failed to delete memory"
        
        # Verify deletion
        deleted = agent.execute_tool("memory_get", id=id1)
        assert deleted is None, "Entry not deleted"
        
        await agent.cleanup()
        print("Memory CRUD test passed")
        return True
        
    except Exception as e:
        print(f"Memory CRUD test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_memory_search():
    """Test semantic search functionality"""
    print("Testing memory search")
    
    try:
        memory = FAISSMemory(dim=384)
        agent = create_simple_agent("SearchAgent", memory=memory)
        
        agent.store_knowledge("Python is a programming language")
        agent.store_knowledge("Machine learning uses algorithms")
        agent.store_knowledge("Databases store structured data")
        
        results = agent.recall_knowledge("coding languages", top_k=1)
        assert len(results) > 0, "No search results"
        assert "Python" in results[0]["text"], "Wrong search result"
        
        results = agent.recall_knowledge("AI and algorithms", top_k=1)
        assert "learning" in results[0]["text"] or "algorithms" in results[0]["text"], "Semantic search failed"
        
        await agent.cleanup()
        print("Memory search test passed")
        return True
        
    except Exception as e:
        print(f"Memory search test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_memory_with_metadata():
    """Test memory storage with metadata"""
    print("Testing memory with metadata")
    
    try:
        memory = FAISSMemory(dim=384)
        agent = create_simple_agent("MetadataAgent", memory=memory)
        
        # Store with metadata
        id1 = agent.store_knowledge(
            "Important fact about AI",
            metadata={"category": "AI", "importance": "high"}
        )
        
        # Retrieve and verify metadata
        entry = agent.execute_tool("memory_get", id=id1)
        assert entry is not None, "Failed to retrieve entry"
        assert entry["meta"]["category"] == "AI", "Metadata not stored correctly"
        assert entry["meta"]["importance"] == "high", "Metadata incomplete"
        
        await agent.cleanup()
        print("Memory metadata test passed")
        return True
        
    except Exception as e:
        print(f"Memory metadata test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_context_generation():
    """Test context generation for LLM use"""
    print("Testing context generation")
    
    try:
        memory = FAISSMemory(dim=384)
        agent = create_simple_agent("ContextAgent", memory=memory)
        
        agent.store_knowledge("Fact A about topic X")
        agent.store_knowledge("Fact B about topic Y")
        agent.store_knowledge("Fact C about topic X")
        
        # Get formatted context
        context = agent.get_memory_context("topic X", top_k=2)
        
        # Test structure
        assert isinstance(context, dict), "Context should be a dictionary"
        assert "query" in context, "Context should have 'query' field"
        assert "results" in context, "Context should have 'results' field"
        assert "count" in context, "Context should have 'count' field"
        
        # Test content
        assert context["query"] == "topic X", "Query mismatch"
        assert context["count"] > 0, "Should have found results"
        assert len(context["results"]) <= 2, "Should respect top_k limit"
        
        # Test result structure
        for result in context["results"]:
            assert "text" in result, "Result should have 'text' field"
            assert "relevance" in result, "Result should have 'relevance' field"
            assert "metadata" in result, "Result should have 'metadata' field"
            assert "topic X" in result["text"], "Result should be about topic X"
        
        # Test relevance scoring
        first_result = context["results"][0]
        assert 0 <= first_result["relevance"] <= 1, "Relevance should be between 0 and 1"
        
        await agent.cleanup()
        print("Context generation test passed")
        return True
        
    except Exception as e:
        print(f"Context generation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all memory tests"""
    print("Memory Agent Test Suite")
    print("=" * 40)
    
    tests = [
        test_memory_crud,
        test_memory_search,
        test_memory_with_metadata,
        test_context_generation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if await test():
                passed += 1
        except Exception as e:
            print(f"Test {test.__name__} crashed: {e}")
    
    print("\n" + "=" * 40)
    print(f"Tests completed: {passed}/{total} passed")
    
    if passed == total:
        print("All tests passed")
        return 0
    else:
        print("Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
