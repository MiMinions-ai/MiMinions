"""
Example usage of MiMinions BaseAgent

This example demonstrates how to use the BaseAgent class with various tools.
"""

from miminions.agents import BaseAgent

# Example 1: Basic agent with custom tools
def example_basic_agent():
    """Demonstrate basic agent functionality"""
    print("=== Basic Agent Example ===")
    
    # Create an agent
    agent = BaseAgent(name="MyAgent")
    
    # Add a custom tool
    def calculator(operation, a, b):
        if operation == "add":
            return a + b
        elif operation == "multiply":
            return a * b
        else:
            return "Unknown operation"
    
    agent.add_tool("calculator", calculator)
    
    # Use the tool
    result = agent.execute_tool("calculator", "add", 5, 3)
    print(f"Calculator result: {result}")
    
    # List available tools
    print(f"Available tools: {agent.list_tools()}")
    
    agent.close()

# Example 2: Agent with database connection (would require actual database)
def example_database_agent():
    """Demonstrate database agent functionality"""
    print("\n=== Database Agent Example ===")
    
    # This would work with a real PostgreSQL connection string
    # connection_string = "postgresql://user:password@localhost/database"
    connection_string = None  # Not providing actual connection for demo
    
    agent = BaseAgent(
        name="DatabaseAgent",
        connection_string=connection_string,
        session_id="demo_session_123"
    )
    
    # These would work with actual database tools
    try:
        # Remember and recall examples (would work with real database)
        print("With a real database connection, you could:")
        print("- agent.remember('Python is great!', embedding=[0.1, 0.2, 0.3])")
        print("- agent.remember_search([0.1, 0.2, 0.3])")
        print("- agent.recall(limit=10)")
        print("- agent.recall_context([0.1, 0.2, 0.3])")
        print("")
        print("- agent.vector_search([1, 2, 3], 'embeddings_table')  # deprecated")
        print("- agent.concept_query('{ users { name email } }')")
        print(f"Current session: {agent.get_session()}")
        
        # Demonstrate session management
        agent.set_session("new_session_456")
        print(f"New session: {agent.get_session()}")
        
    except Exception as e:
        print(f"Database tools not available: {e}")
    
    agent.close()

# Example 3: Agent with search tools (would require search dependencies)
def example_search_agent():
    """Demonstrate search agent functionality"""
    print("\n=== Search Agent Example ===")
    
    agent = BaseAgent(name="SearchAgent")
    
    # These would work with proper search tool dependencies
    try:
        # results = agent.web_search("Python programming tutorial")
        # print(f"Search results: {results}")
        print("Search tools would be available with proper dependencies")
    except Exception as e:
        print(f"Search tools not available: {e}")
    
    agent.close()

# Example 4: Async agent usage
async def example_async_agent():
    """Demonstrate async agent functionality"""
    print("\n=== Async Agent Example ===")
    
    async def async_tool(message):
        import asyncio
        await asyncio.sleep(0.1)  # Simulate async work
        return f"Async result: {message}"
    
    agent = BaseAgent(name="AsyncAgent")
    agent.add_tool("async_task", async_tool)
    
    # Use async tool
    result = await agent.execute_tool_async("async_task", "Hello Async World")
    print(f"Async tool result: {result}")
    
    await agent.close_async()

# Example 5: Memory and session management (demonstrating new remember/recall features)
def example_memory_management():
    """Demonstrate remember and recall functionality"""
    print("\n=== Memory Management Example ===")
    
    # Create agent with session tracking
    agent = BaseAgent(
        name="MemoryAgent", 
        session_id="conversation_demo"
    )
    
    print(f"Agent session: {agent.get_session()}")
    print("Agent representation:", repr(agent))
    
    # Demonstrate session switching
    agent.set_session("new_conversation")
    print(f"Switched to session: {agent.get_session()}")
    
    # Show what would work with database connection
    print("\nWith database connection, you could:")
    print("1. Remember information:")
    print("   agent.remember('User likes Python', role='system')")
    print("   agent.remember('How do I install packages?', role='user')")
    print("   agent.remember('Use pip install <package>', role='assistant')")
    print("")
    print("2. Search remembered knowledge:")
    print("   agent.remember_search([0.1, 0.2, 0.3])  # vector similarity")
    print("")
    print("3. Recall conversation:")
    print("   agent.recall()  # get conversation history")
    print("   agent.recall_context([0.1, 0.2, 0.3])  # get relevant context")
    print("")
    print("4. Cross-session operations:")
    print("   agent.recall(session_id='other_conversation')")
    
    agent.close()

if __name__ == "__main__":
    # Run the examples
    example_basic_agent()
    example_database_agent()
    example_search_agent()
    example_memory_management()
    
    # Run async example
    import asyncio
    asyncio.run(example_async_agent())
    
    print("\n=== Examples completed ===")