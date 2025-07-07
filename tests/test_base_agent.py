"""
Basic tests for MiMinions base agent module
"""

import pytest
import sys
import os

# Add src to path for importing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from miminions.agents import BaseAgent


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
        agent.close()


if __name__ == "__main__":
    pytest.main([__file__])