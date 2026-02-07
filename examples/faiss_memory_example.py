"""Memory-Enabled Pydantic AI Agent Example"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from miminions.agent import create_pydantic_agent, MemoryQueryResult
from miminions.memory.faiss import FAISSMemory


async def basic_memory_demo():
    """Demonstrate basic memory operations with Pydantic models"""
    print("Basic Memory Demo (Pydantic)")
    
    memory = FAISSMemory(dim=384)
    agent = create_pydantic_agent("MemoryAgent", "Agent with long-term memory", memory=memory)
    
    print(f"Agent: {agent}")
    print(f"Agent state: {agent.get_state()}")
    print(f"Available tools: {agent.list_tools()}")
    
    print("Storing knowledge")
    result1 = agent.execute("memory_store",
                           text="Python is a high-level programming language",
                           metadata={"category": "programming", "topic": "python"})
    print(f"Store result: {result1.status}, ID: {result1.result[:10]}")
    
    result2 = agent.execute("memory_store",
                           text="Machine learning is a subset of artificial intelligence",
                           metadata={"category": "AI", "topic": "ML"})
    print(f"Store result: {result2.status}, ID: {result2.result[:10]}")
    
    result3 = agent.execute("memory_store",
                           text="FAISS is a library for efficient similarity search",
                           metadata={"category": "libraries", "topic": "search"})
    print(f"Store result: {result3.status}, ID: {result3.result[:10]}")
    
    print("Recalling knowledge about 'programming languages'")
    recall_result = agent.execute("memory_recall", query="programming languages", top_k=2)
    
    if recall_result.status.value == "success":
        for i, item in enumerate(recall_result.result, 1):
            print(f"{i}. {item['text']}")
            print(f"   Distance: {item.get('distance', 'N/A')}")
    
    await agent.cleanup()
    print("Done")


async def structured_context_demo():
    """Demonstrate structured memory context retrieval"""
    print("\nStructured Context Demo")
    
    memory = FAISSMemory(dim=384)
    agent = create_pydantic_agent("ContextAgent", memory=memory)
    
    # Build knowledge base
    knowledge = [
        "The Model Context Protocol (MCP) allows AI agents to interact with external tools",
        "FAISS enables fast similarity search in high-dimensional vector spaces",
        "Agents can use memory to maintain context across conversations",
        "Vector databases store embeddings for semantic search",
        "Python's asyncio library supports asynchronous programming"
    ]
    
    print("Building knowledge base")
    for text in knowledge:
        agent.store_knowledge(text, metadata={"source": "documentation"})
    
    print(f"Stored {len(knowledge)} knowledge entries")
    
    queries = [
        "How do agents interact with tools?",
        "What is used for similarity search?",
        "How can agents remember information?"
    ]
    
    for query in queries:
        print(f"Query: {query}")
        
        # get_memory_context returns a MemoryQueryResult Pydantic model
        context: MemoryQueryResult = agent.get_memory_context(query, top_k=2)
        
        print(f"- Results: {context.count}")
        print(f"- Message: {context.message or 'None'}")
        
        for entry in context.results:
            print(f"  - {entry.text[:60]}")
            print(f"    - ID: {entry.id[:10]}" if entry.id else "  ID: None")
        print()
    
    await agent.cleanup()
    print("Done")


async def memory_with_tools_demo():
    """Demonstrate memory alongside other tools"""
    print("\nMemory with Tools Demo")
    
    memory = FAISSMemory(dim=384)
    agent = create_pydantic_agent("HybridAgent", memory=memory)
    
    # Add custom tools
    def calculate_area(width: float, height: float) -> float:
        """Calculate area of a rectangle"""
        return width * height
    
    def format_result(value: float, unit: str = "units") -> str:
        """Format a numeric result with units"""
        return f"{value:.2f} {unit}"
    
    agent.register_tool("calculate_area", "Calculate rectangle area", calculate_area)
    agent.register_tool("format_result", "Format numeric result", format_result)
    
    print(f"Available tools: {agent.list_tools()}")
    
    print("Performing calculation")
    area_result = agent.execute("calculate_area", width=5.0, height=3.0)
    print(f"Area calculation: {area_result.status}, Result: {area_result.result}")
    print(f"Execution time: {area_result.execution_time_ms:.2f}ms")
    
    format_result = agent.execute("format_result", value=area_result.result, unit="square meters")
    print(f"Formatted: {format_result.result}")
    
    print("Storing calculation in memory")
    agent.store_knowledge(
        f"Calculated area of a 5x3 rectangle: {format_result.result}",
        metadata={"type": "calculation", "operation": "area", "dimensions": "5x3"}
    )
    
    print("Recalling calculation")
    context = agent.get_memory_context("rectangle area calculation", top_k=1)
    
    if context.count > 0:
        print(f"Found: {context.results[0].text}")
        print(f"Metadata: {context.results[0].metadata}")
    
    await agent.cleanup()
    print("Done")


async def compare_execution_styles():
    """Compare structured vs raw execution styles with memory"""
    print("\nComparing Execution Styles")
    
    memory = FAISSMemory(dim=384)
    agent = create_pydantic_agent("CompareAgent", memory=memory)
    
    agent.store_knowledge("The Pydantic Agent provides strong typing")
    agent.store_knowledge("The agent is lightweight and flexible")
    
    # Structured: Returns ToolExecutionResult
    print("Structured execution (execute):")
    result = agent.execute("memory_recall", query="agent typing", top_k=1)
    print(f"- Type: {type(result).__name__}")
    print(f"- Status: {result.status}")
    print(f"- Has timing: {result.execution_time_ms is not None}")
    print(f"- Result type: {type(result.result).__name__}")
    
    # Raw: Returns raw value
    print("Raw execution (execute_tool):")
    raw_result = agent.execute_tool("memory_recall", query="agent typing", top_k=1)
    print(f"- Type: {type(raw_result).__name__}")
    print(f"- Value: {raw_result[0]['text'][:40]}")
    
    print("Structured context retrieval:")
    context = agent.get_memory_context("agent comparison", top_k=2)
    print(f"- Type: {type(context).__name__}")
    print(f"- Query: {context.query}")
    print(f"- Count: {context.count}")
    print(f"- Results type: {type(context.results).__name__}")
    
    await agent.cleanup()
    print("Done")


async def main():
    """Run all memory demonstrations"""
    print("Pydantic Agent Memory System Demonstration")
    
    await basic_memory_demo()
    await structured_context_demo()
    await memory_with_tools_demo()
    await compare_execution_styles()
    
    print("\nAll demonstrations completed")


if __name__ == "__main__":
    asyncio.run(main())
