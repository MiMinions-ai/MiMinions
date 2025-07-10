"""
Database Integration Example for MiMinions BaseAgent

This example shows how to use BaseAgent with database integration for
vector search, GraphQL queries, and knowledge management.

Note: This example requires actual PostgreSQL with pgvector and pg_graphql extensions.
"""

from miminions.agents import BaseAgent
import asyncio


def database_setup_example():
    """Show how to set up BaseAgent with database connection"""
    print("=== Database Setup Example ===")
    
    # Example connection string (replace with actual credentials)
    connection_string = "postgresql://username:password@localhost:5432/miminions_db"
    
    print("To use database features, you need:")
    print("1. PostgreSQL database with pgvector extension")
    print("2. pg_graphql extension for GraphQL queries")
    print("3. Proper connection string")
    print(f"\nExample connection string:")
    print(f"'{connection_string}'")
    
    # Create agent with database connection (would work with real database)
    print("\n# Create agent with database")
    print("agent = BaseAgent(")
    print("    name='DatabaseAgent',")
    print(f"    connection_string='{connection_string}',")
    print("    session_id='db_demo_session'")
    print(")")


def vector_search_example():
    """Demonstrate vector search capabilities"""
    print("\n=== Vector Search Example ===")
    
    # This would work with actual database
    print("With database connection, vector search would work like:")
    print()
    
    print("# Search for similar content using embeddings")
    print("query_vector = [0.1, 0.2, 0.3, ...]  # Your embedding vector")
    print("results = agent.vector_search(")
    print("    query_vector=query_vector,")
    print("    table='knowledge_base',")
    print("    limit=10,")
    print("    similarity_threshold=0.8")
    print(")")
    print()
    print("# Results would contain:")
    print("# [")
    print("#   {'id': 1, 'content': 'Similar content', 'similarity': 0.95},")
    print("#   {'id': 2, 'content': 'Another match', 'similarity': 0.87},")
    print("#   ...")
    print("# ]")


def remember_recall_example():
    """Demonstrate remember and recall functionality"""
    print("\n=== Remember/Recall Example ===")
    
    print("# Remember information with automatic embedding")
    print("agent.remember(")
    print("    content='User prefers Python over JavaScript',")
    print("    role='system',")
    print("    metadata={'topic': 'preferences', 'importance': 'high'}")
    print(")")
    print()
    
    print("# Remember with custom embedding")
    print("agent.remember(")
    print("    content='How to install Python packages?',")
    print("    embedding=[0.1, 0.2, 0.3, ...],")
    print("    role='user'")
    print(")")
    print()
    
    print("# Search remembered knowledge")
    print("query_embedding = get_embedding('Python installation')")
    print("knowledge = agent.remember_search(")
    print("    query_vector=query_embedding,")
    print("    limit=5,")
    print("    similarity_threshold=0.7")
    print(")")
    print()
    
    print("# Recall conversation history")
    print("history = agent.recall(limit=20)  # Last 20 messages")
    print("other_session = agent.recall(session_id='other_chat', limit=10)")
    print()
    
    print("# Find relevant context using vector similarity")
    print("context = agent.recall_context(")
    print("    query_vector=query_embedding,")
    print("    limit=5,")
    print("    session_id='current_session'")
    print(")")


def graphql_example():
    """Demonstrate GraphQL query capabilities"""
    print("\n=== GraphQL Query Example ===")
    
    print("# Query concepts and their relations")
    print("query = '''")
    print("{")
    print("  concepts(filter: {category: {eq: \"programming\"}}) {")
    print("    id")
    print("    name")
    print("    description")
    print("    relations {")
    print("      type")
    print("      target {")
    print("        name")
    print("      }")
    print("    }")
    print("  }")
    print("}")
    print("'''")
    print()
    print("results = agent.concept_query(query)")
    print()
    print("# Results would contain concept relationships:")
    print("# {")
    print("#   'concepts': [")
    print("#     {")
    print("#       'id': 1,")
    print("#       'name': 'Python',")
    print("#       'relations': [")
    print("#         {'type': 'similar_to', 'target': {'name': 'JavaScript'}},")
    print("#         {'type': 'used_for', 'target': {'name': 'Data Science'}}")
    print("#       ]")
    print("#     }")
    print("#   ]")
    print("# }")


def async_database_example():
    """Demonstrate async database operations"""
    print("\n=== Async Database Operations Example ===")
    
    print("# Async remember")
    print("await agent.remember_async(")
    print("    content='Async conversation message',")
    print("    role='user'")
    print(")")
    print()
    
    print("# Async recall")
    print("history = await agent.recall_async(limit=15)")
    print()
    
    print("# Async vector search")
    print("results = await agent.remember_search_async(")
    print("    query_vector=[0.1, 0.2, 0.3],")
    print("    limit=10")
    print(")")
    print()
    
    print("# Async context search")
    print("context = await agent.recall_context_async(")
    print("    query_vector=[0.1, 0.2, 0.3],")
    print("    limit=5")
    print(")")


def session_management_example():
    """Demonstrate session management with database"""
    print("\n=== Session Management with Database ===")
    
    print("# Create agent with specific session")
    print("agent = BaseAgent(")
    print("    name='SessionAgent',")
    print("    connection_string=connection_string,")
    print("    session_id='user_alice_conversation'")
    print(")")
    print()
    
    print("# Remember in current session")
    print("agent.remember('User Alice asked about machine learning')")
    print()
    
    print("# Switch to different session")
    print("agent.set_session('user_bob_conversation')")
    print("agent.remember('User Bob prefers deep learning')")
    print()
    
    print("# Recall from specific session")
    print("alice_history = agent.recall(session_id='user_alice_conversation')")
    print("bob_history = agent.recall(session_id='user_bob_conversation')")
    print()
    
    print("# Cross-session knowledge search")
    print("all_ml_content = agent.remember_search(")
    print("    query_vector=ml_embedding,")
    print("    # No session_id means search across all sessions")
    print(")")


def database_schema_example():
    """Show expected database schema"""
    print("\n=== Expected Database Schema ===")
    
    print("The BaseAgent expects these tables:")
    print()
    
    print("1. knowledge_base table for remember/recall:")
    print("   CREATE TABLE knowledge_base (")
    print("       id SERIAL PRIMARY KEY,")
    print("       session_id VARCHAR(255),")
    print("       content TEXT,")
    print("       embedding VECTOR(384),  -- or your embedding dimension")
    print("       role VARCHAR(50),")
    print("       metadata JSONB,")
    print("       created_at TIMESTAMP DEFAULT NOW()")
    print("   );")
    print()
    
    print("2. Vector similarity index:")
    print("   CREATE INDEX ON knowledge_base USING ivfflat (embedding vector_cosine_ops);")
    print()
    
    print("3. Session index:")
    print("   CREATE INDEX ON knowledge_base (session_id, created_at);")
    print()
    
    print("4. For GraphQL queries, install pg_graphql:")
    print("   CREATE EXTENSION IF NOT EXISTS pg_graphql;")


def complete_database_example():
    """Show a complete database usage example"""
    print("\n=== Complete Database Usage Example ===")
    
    example_code = '''
import asyncio
from miminions.agents import BaseAgent

async def main():
    # Initialize agent with database
    agent = BaseAgent(
        name="SmartAssistant",
        connection_string="postgresql://user:pass@localhost/db",
        session_id="user_123_session"
    )
    
    try:
        # Remember user information
        await agent.remember_async(
            content="User is interested in machine learning",
            role="system",
            metadata={"category": "preference"}
        )
        
        # Remember conversation
        await agent.remember_async(
            content="What's the best way to start learning ML?",
            role="user"
        )
        
        await agent.remember_async(
            content="I recommend starting with Python and scikit-learn",
            role="assistant"
        )
        
        # Later, search for relevant information
        query_embedding = get_embedding("machine learning tutorial")
        
        # Search remembered knowledge
        knowledge = await agent.remember_search_async(
            query_vector=query_embedding,
            limit=5
        )
        
        # Get conversation context
        context = await agent.recall_context_async(
            query_vector=query_embedding,
            limit=3
        )
        
        # Get recent conversation
        history = await agent.recall_async(limit=10)
        
        print(f"Found {len(knowledge)} knowledge items")
        print(f"Found {len(context)} context items")
        print(f"Found {len(history)} history items")
        
    finally:
        await agent.close_async()

# Run the example
# asyncio.run(main())
'''
    
    print("Complete example:")
    print(example_code)


if __name__ == "__main__":
    # Run all examples
    database_setup_example()
    vector_search_example()
    remember_recall_example()
    graphql_example()
    session_management_example()
    database_schema_example()
    complete_database_example()
    
    print("\n=== Database Integration Examples Completed ===")