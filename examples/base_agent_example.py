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
        connection_string=connection_string
    )
    
    # These would work with actual database tools
    try:
        # agent.vector_search([1, 2, 3], "embeddings_table")
        # agent.concept_query("{ users { name email } }")
        print("Database tools would be available with proper connection")
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

if __name__ == "__main__":
    # Run the examples
    example_basic_agent()
    example_database_agent()
    example_search_agent()
    
    # Run async example
    import asyncio
    asyncio.run(example_async_agent())
    
    print("\n=== Examples completed ===")