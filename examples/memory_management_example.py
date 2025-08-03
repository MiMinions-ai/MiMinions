"""
Memory Management Example for MiMinions BaseAgent

This example demonstrates the remember/recall functionality for knowledge management
and conversation session tracking.
"""

from miminions.agent import BaseAgent
import asyncio


def basic_memory_example():
    """Demonstrate basic memory management without database"""
    print("=== Basic Memory Management Example ===")
    
    # Create agent with specific session
    agent = BaseAgent(name="MemoryAgent", session_id="demo_session")
    print(f"Agent: {agent.name}")
    print(f"Current session: {agent.get_session()}")
    
    # Demonstrate session management
    agent.set_session("conversation_1")
    print(f"Switched to session: {agent.get_session()}")
    
    # Show what the remember/recall methods would do with a database
    print("\n--- What you could do with a database connection ---")
    print("1. Remember information with vector embeddings:")
    print("   agent.remember('User asked about Python basics', role='user')")
    print("   agent.remember('Explained variables and data types', role='assistant')")
    
    print("\n2. Search remembered knowledge:")
    print("   # Find similar content using vector similarity")
    print("   results = agent.remember_search([0.1, 0.2, 0.3], limit=5)")
    
    print("\n3. Recall conversation history:")
    print("   # Get recent conversation from current session")
    print("   history = agent.recall(limit=20)")
    print("   # Get conversation from specific session")
    print("   other_history = agent.recall(session_id='other_conversation')")
    
    print("\n4. Find relevant context:")
    print("   # Find relevant context using vector similarity within session")
    print("   context = agent.recall_context([0.1, 0.2, 0.3], limit=10)")
    
    # Demonstrate error handling
    try:
        agent.remember("This will fail without database")
    except ValueError as e:
        print(f"\nExpected error without database: {e}")
    
    agent.close()


async def async_memory_example():
    """Demonstrate async memory management"""
    print("\n=== Async Memory Management Example ===")
    
    agent = BaseAgent(name="AsyncMemoryAgent", session_id="async_demo")
    
    print("Async operations would work like this with a database:")
    print("1. await agent.remember_async('Async content', embedding=[0.1, 0.2])")
    print("2. results = await agent.remember_search_async([0.1, 0.2, 0.3])")
    print("3. history = await agent.recall_async(limit=10)")
    print("4. context = await agent.recall_context_async([0.1, 0.2, 0.3])")
    
    # Test error handling for async methods
    try:
        await agent.remember_async("This will fail")
    except ValueError as e:
        print(f"Expected async error: {e}")
    
    await agent.close_async()


def conversation_session_example():
    """Demonstrate conversation session management"""
    print("\n=== Conversation Session Example ===")
    
    # Simulate multiple conversation sessions
    sessions = ["user_alice_chat", "user_bob_chat", "group_discussion"]
    
    for session_id in sessions:
        agent = BaseAgent(name="ConversationAgent", session_id=session_id)
        print(f"\nAgent in session '{session_id}':")
        print(f"  Session ID: {agent.get_session()}")
        print(f"  Agent repr: {repr(agent)}")
        
        # Simulate what would happen with database
        print(f"  Would store: conversation data for {session_id}")
        print(f"  Would recall: previous messages from {session_id}")
        
        agent.close()


def cross_session_example():
    """Demonstrate cross-session operations"""
    print("\n=== Cross-Session Operations Example ===")
    
    agent = BaseAgent(name="CrossSessionAgent")
    
    # Switch between sessions
    sessions = ["work_discussion", "personal_chat", "technical_support"]
    
    for session in sessions:
        agent.set_session(session)
        print(f"Session: {agent.get_session()}")
        
        # Show what cross-session operations would look like
        print(f"  - Remember in {session}: agent.remember('content for {session}')")
        print(f"  - Recall from {session}: agent.recall(session_id='{session}')")
        print(f"  - Search across sessions: agent.remember_search([0.1, 0.2, 0.3])")
    
    # Show recall from specific session while in different session
    agent.set_session("current_session")
    print(f"\nCurrent session: {agent.get_session()}")
    print("Can still recall from other sessions:")
    for session in sessions:
        print(f"  - agent.recall(session_id='{session}')")
    
    agent.close()


def knowledge_search_example():
    """Demonstrate knowledge search capabilities"""
    print("\n=== Knowledge Search Example ===")
    
    agent = BaseAgent(name="KnowledgeAgent")
    
    # Show what knowledge search would do
    print("Knowledge search combines vector search and web search:")
    print("1. First searches remembered knowledge (vector similarity)")
    print("2. Then performs web search if needed")
    print("3. Returns combined results")
    
    # Test error handling
    try:
        agent.knowledge_search("Python programming tutorial")
    except ValueError as e:
        print(f"Expected error without tools: {e}")
    
    agent.close()


if __name__ == "__main__":
    # Run all examples
    basic_memory_example()
    conversation_session_example() 
    cross_session_example()
    knowledge_search_example()
    
    # Run async example
    asyncio.run(async_memory_example())
    
    print("\n=== Memory Management Examples Completed ===")