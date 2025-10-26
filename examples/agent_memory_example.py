"""
Memory-Enabled Agent Example

Demonstrates how to use an agent with FAISS memory for knowledge storage and retrieval.
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from miminions.agent.simple_agent import create_simple_agent
from miminions.memory.faiss import FAISSMemory


async def basic_memory_demo():
    """Demonstrate basic memory operations"""
    print("=== Basic Memory Demo ===\n")
    
    memory = FAISSMemory(dim=384)
    agent = create_simple_agent("MemoryAgent", "Agent with long-term memory", memory=memory)
    
    print(f"Agent created: {agent}")
    print(f"Available tools: {agent.list_tools()}\n")
    
    print("Storing knowledge...")
    id1 = agent.execute_tool("memory_store", 
                            text="Python is a high-level programming language",
                            metadata={"category": "programming", "topic": "python"})
    
    id2 = agent.execute_tool("memory_store",
                            text="Machine learning is a subset of artificial intelligence",
                            metadata={"category": "AI", "topic": "ML"})
    
    id3 = agent.execute_tool("memory_store",
                            text="FAISS is a library for efficient similarity search",
                            metadata={"category": "libraries", "topic": "search"})
    
    print(f"Stored 3 knowledge entries: {id1[:10]}..., {id2[:10]}..., {id3[:10]}...\n")
    
    print("Recalling knowledge about 'programming languages'...")
    results = agent.execute_tool("memory_recall", query="programming languages", top_k=2)
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['text']}")
        print(f"   Distance: {result.get('distance', 'N/A')}")
        print(f"   Metadata: {result.get('meta', {})}\n")
    
    print("Updating knowledge...")
    success = agent.execute_tool("memory_update", 
                                 id=id1, 
                                 new_text="Python is a popular high-level programming language known for its simplicity")
    print(f"Update successful: {success}\n")
    
    print("Retrieving updated entry...")
    updated = agent.execute_tool("memory_get", id=id1)
    if updated:
        print(f"Updated text: {updated['text']}\n")
    
    print("Listing all knowledge entries...")
    all_entries = agent.execute_tool("memory_list")
    print(f"Total entries: {len(all_entries)}")
    for entry in all_entries:
        print(f"- {entry['text'][:50]}...")
    
    await agent.cleanup()
    print("\nBasic memory demo completed!")


async def context_retrieval_demo():
    """Demonstrate using memory for context in conversations"""
    print("\n=== Context Retrieval Demo ===\n")
    
    memory = FAISSMemory(dim=384)
    agent = create_simple_agent("ContextAgent", memory=memory)
    
    print("Building knowledge base...")
    knowledge = [
        "The Model Context Protocol (MCP) allows AI agents to interact with external tools",
        "FAISS enables fast similarity search in high-dimensional vector spaces",
        "Agents can use memory to maintain context across conversations",
        "Vector databases store embeddings for semantic search",
        "Python's asyncio library supports asynchronous programming"
    ]
    
    for text in knowledge:
        agent.store_knowledge(text, metadata={"source": "documentation"})
    
    print(f"Stored {len(knowledge)} knowledge entries\n")
    
    queries = [
        "How do agents interact with tools?",
        "What is used for similarity search?",
        "How can agents remember information?"
    ]
    
    for query in queries:
        print(f"Query: {query}")
        context = agent.get_memory_context(query, top_k=2)
        print(context + '\n')
    
    await agent.cleanup()
    print("Context retrieval demo completed!")


async def memory_with_tools_demo():
    """Demonstrate memory alongside other tools"""
    print("\n=== Memory with Tools Demo ===\n")
    
    memory = FAISSMemory(dim=384)
    agent = create_simple_agent("HybridAgent", memory=memory)
    
    def calculate_area(width: float, height: float) -> float:
        """Calculate area of a rectangle"""
        return width * height
    
    def greet(name: str) -> str:
        """Generate a greeting"""
        return f"Hello, {name}!"
    
    agent.add_function_as_tool("calculate_area", "Calculate rectangle area", calculate_area)
    agent.add_function_as_tool("greet", "Generate greeting", greet)
    
    print(f"Available tools: {agent.list_tools()}\n")
    
    print("Using calculation tool...")
    area = agent.execute_tool("calculate_area", width=5.0, height=3.0)
    print(f"Area of 5x3 rectangle: {area}\n")
    
    print("Storing calculation in memory...")
    agent.store_knowledge(
        f"Calculated area of a 5x3 rectangle: {area} square units",
        metadata={"type": "calculation", "operation": "area"}
    )
    
    print("Recalling calculation...")
    results = agent.recall_knowledge("rectangle area calculation", top_k=1)
    if results:
        print(f"Found: {results[0]['text']}\n")
    
    greeting = agent.execute_tool("greet", name="User")
    print(f"Greeting: {greeting}")
    
    agent.store_knowledge(
        f"Greeted user with: {greeting}",
        metadata={"type": "interaction", "action": "greeting"}
    )
    
    print("\nSearching for past interactions...")
    interactions = agent.recall_knowledge("user interactions", top_k=2)
    for interaction in interactions:
        print(f"- {interaction['text']}")
    
    await agent.cleanup()
    print("\nMemory with tools demo completed!")


async def main():
    """Run all memory demonstrations"""
    print("Agent Memory System Demonstration")
    print("=" * 60)
    
    await basic_memory_demo()
    await context_retrieval_demo()
    await memory_with_tools_demo()
    
    print("\n" + "=" * 60)
    print("All demonstrations completed!")


if __name__ == "__main__":
    asyncio.run(main())
