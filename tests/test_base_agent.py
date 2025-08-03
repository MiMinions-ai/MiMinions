"""
Basic tests for MiMinions base agent module
"""

import pytest
import sys
import os

# Add src to path for importing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from miminions.agent import BaseAgent


class TestBaseAgent:
    """Test BaseAgent functionality"""
    
    def test_base_agent_init(self):
        """Test BaseAgent initialization"""
        agent = BaseAgent(name="test_agent")
        assert agent.name == "test_agent"
        assert len(agent.list_tools()) == 0
        agent.close()
    
    def test_tool_management(self):
        """Test custom tool management"""
        agent = BaseAgent(name="test_agent")
        
        # Test adding tool
        def test_tool(x, y):
            return x + y
        
        agent.add_tool("add", test_tool)
        assert agent.has_tool("add")
        assert "add" in agent.list_tools()
        
        # Test executing tool
        result = agent.execute_tool("add", 2, 3)
        assert result == 5
        
        # Test removing tool
        agent.remove_tool("add")
        assert not agent.has_tool("add")
        assert "add" not in agent.list_tools()
        
        agent.close()
    
    def test_agent_without_database(self):
        """Test agent functionality without database connection"""
        agent = BaseAgent(name="test_agent")
        
        # These should raise errors since no database connection
        with pytest.raises(ValueError, match="Database tools not initialized"):
            agent.vector_search([1, 2, 3], "test_table")
        
        with pytest.raises(ValueError, match="Database tools not initialized"):
            agent.concept_query("{ test }")
        
        # Test new remember/recall methods also raise errors
        with pytest.raises(ValueError, match="Database tools not initialized"):
            agent.remember("test content")
        
        with pytest.raises(ValueError, match="Database tools not initialized"):
            agent.recall()
        
        with pytest.raises(ValueError, match="Database tools not initialized"):
            agent.remember_search([1, 2, 3])
        
        with pytest.raises(ValueError, match="Database tools not initialized"):
            agent.recall_context([1, 2, 3])
        
        agent.close()
    
    def test_agent_without_search_tools(self):
        """Test agent functionality without search tools"""
        agent = BaseAgent(name="test_agent")
        
        # These should raise errors since search tools are not available
        with pytest.raises(ValueError, match="Search tools not initialized"):
            agent.web_search("test query")
        
        agent.close()
    
    def test_search_tools_initialization(self):
        """Test search tools initialization state"""
        agent = BaseAgent(name="test_agent")
        
        # Search tools should be None when dependencies are not available
        assert agent.search_tools is None
        
        agent.close()
    
    def test_agent_repr(self):
        """Test agent string representation"""
        agent = BaseAgent(name="test_agent")
        repr_str = repr(agent)
        assert "BaseAgent" in repr_str
        assert "test_agent" in repr_str
        assert "session" in repr_str
        agent.close()
    
    def test_session_management(self):
        """Test session ID management"""
        agent = BaseAgent(name="test_agent")
        
        # Test default session ID is set
        initial_session = agent.get_session()
        assert initial_session is not None
        assert len(initial_session) > 0
        
        # Test setting new session ID
        new_session = "test_session_123"
        agent.set_session(new_session)
        assert agent.get_session() == new_session
        
        agent.close()
    
    def test_agent_init_with_session(self):
        """Test BaseAgent initialization with session ID"""
        session_id = "test_session_456"
        agent = BaseAgent(name="test_agent", session_id=session_id)
        assert agent.get_session() == session_id
        agent.close()
    
    def test_remember_recall_without_database(self):
        """Test remember and recall methods without database connection"""
        agent = BaseAgent(name="test_agent")
        
        # Test remember method
        with pytest.raises(ValueError, match="Database tools not initialized"):
            agent.remember("test content", embedding=[0.1, 0.2, 0.3])
        
        # Test remember_search method
        with pytest.raises(ValueError, match="Database tools not initialized"):
            agent.remember_search([0.1, 0.2, 0.3])
        
        # Test recall method
        with pytest.raises(ValueError, match="Database tools not initialized"):
            agent.recall(limit=10)
        
        # Test recall_context method
        with pytest.raises(ValueError, match="Database tools not initialized"):
            agent.recall_context([0.1, 0.2, 0.3])
        
        agent.close()
    
    def test_async_remember_recall_without_database(self):
        """Test async remember and recall methods without database connection"""
        import asyncio
        
        async def test_async_methods():
            agent = BaseAgent(name="test_agent")
            
            # Test async remember method
            with pytest.raises(ValueError, match="Database tools not initialized"):
                await agent.remember_async("test content", embedding=[0.1, 0.2, 0.3])
            
            # Test async remember_search method
            with pytest.raises(ValueError, match="Database tools not initialized"):
                await agent.remember_search_async([0.1, 0.2, 0.3])
            
            # Test async recall method
            with pytest.raises(ValueError, match="Database tools not initialized"):
                await agent.recall_async(limit=10)
            
            # Test async recall_context method
            with pytest.raises(ValueError, match="Database tools not initialized"):
                await agent.recall_context_async([0.1, 0.2, 0.3])
            
            await agent.close_async()
        
        asyncio.run(test_async_methods())
    
    def test_deprecated_methods_without_database(self):
        """Test deprecated vector_search and concept_query methods"""
        agent = BaseAgent(name="test_agent")
        
        # Test deprecated vector_search method
        with pytest.raises(ValueError, match="Database tools not initialized"):
            agent.vector_search([0.1, 0.2, 0.3], "test_table")
        
        # Test concept_query method
        with pytest.raises(ValueError, match="Database tools not initialized"):
            agent.concept_query("{ test }")
        
        agent.close()
    
    def test_knowledge_search_without_tools(self):
        """Test knowledge_search method without proper tools"""
        agent = BaseAgent(name="test_agent")
        
        # Should return results but with error messages when tools are not available
        results = agent.knowledge_search("test query")
        assert "query" in results
        assert results["query"] == "test query"
        # Should not have successful vector or web results without tools
        assert "vector_results" not in results
        assert "web_results" not in results
        
        agent.close()
    
    def test_session_id_validation(self):
        """Test session ID validation and management"""
        agent = BaseAgent(name="test_agent")
        
        # Test getting current session
        current_session = agent.get_session()
        assert current_session is not None
        assert isinstance(current_session, str)
        assert len(current_session) > 0
        
        # Test setting a new session
        new_session = "custom_session_789"
        agent.set_session(new_session)
        assert agent.get_session() == new_session
        
        # Test setting empty string (allowed by implementation)
        agent.set_session("")
        assert agent.get_session() == ""
        
        # Test setting None (implementation allows this)
        agent.set_session(None)
        updated_session = agent.get_session()
        assert updated_session is None  # Implementation actually allows None
        
        agent.close()


if __name__ == "__main__":
    pytest.main([__file__])