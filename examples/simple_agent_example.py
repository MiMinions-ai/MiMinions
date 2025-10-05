"""
Example usage of MiMinions BaseAgent

This example demonstrates how to use the BaseAgent class with various tools.
"""

from examples.base_agent_example import example_async_agent
from miminions.agent.simple_agent import Agent

# Example 1: Basic agent with custom tools
def example_basic_agent():
    """Demonstrate basic agent functionality"""
    print("=== Basic Agent Example ===")
    
    # Create an agent
    agent = Agent(name="MyAgent")
    
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

if __name__ == "__main__":
    # Run the examples
    example_basic_agent()
    
    print("\n=== Examples completed ===")