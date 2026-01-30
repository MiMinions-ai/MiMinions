"""Document Ingestion Example for Pydantic Agent."""

import asyncio
from pathlib import Path
from miminions.agent.pydantic_agent import create_pydantic_agent
from miminions.agent.pydantic_agent.models import ExecutionStatus
from miminions.memory.faiss import FAISSMemory


async def main():
    print("Pydantic Agent Document Ingestion Example\n" + "=" * 50)
    
    agent = create_pydantic_agent(name="DocumentAgent", memory=FAISSMemory())
    print(f"Created: {agent}")
    
    # Try PDF if available
    pdf_path = Path(__file__).parent.parent / "example_files" / "resume.pdf"
    if pdf_path.exists():
        print(f"\nIngesting PDF: {pdf_path.name}")
        result = agent.execute("ingest_document", filepath=str(pdf_path))
        
        print(f"  Status: {result.status.value}")
        print(f"  Time: {result.execution_time_ms:.2f}ms")
        print(f"  Chunks: {result.result['chunks_stored']}")
        print(f"  Characters: {result.result['total_characters']:,}")
        
        print("\nQuerying PDF...")
        for query in ["experience", "education", "skills"]:
            results = agent.recall_knowledge(query, top_k=1)
            if results:
                print(f"  '{query}': {results[0]['text'][:80]}...")
    
    # Create and ingest text file
    print("\nIngesting text file...")
    text_file = Path("sample_doc.txt")
    text_file.write_text("""Artificial Intelligence and Machine Learning

Machine learning enables systems to learn from experience without explicit programming.
Deep learning uses neural networks with multiple layers.
Natural language processing helps machines understand human language.
Computer vision enables computers to interpret visual information.""")
    
    result = agent.execute("ingest_document", filepath=str(text_file))
    print(f"  Status: {result.status.value}")
    print(f"  Time: {result.execution_time_ms:.2f}ms")
    print(f"  Chunks: {result.result['chunks_stored']}")
    
    # Query with structured result
    print("\nQuerying with get_memory_context (Pydantic model):")
    context = agent.get_memory_context("What is deep learning?", top_k=2)
    print(f"  Query: {context.query}")
    print(f"  Results: {context.count}")
    for entry in context.results:
        print(f"    - {entry.text[:80]}...")
    
    # Stats
    list_result = agent.execute("memory_list")
    print(f"\nTotal entries: {len(list_result.result)}")
    
    # Cleanup
    text_file.unlink()
    await agent.cleanup()
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
