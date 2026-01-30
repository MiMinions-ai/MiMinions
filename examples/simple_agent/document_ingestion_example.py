"""Document Ingestion Example for Simple Agent."""

import asyncio
from pathlib import Path
from miminions.agent.simple_agent import create_simple_agent
from miminions.memory.faiss import FAISSMemory


async def main():
    print("Document Ingestion Example")
    
    agent = create_simple_agent(name="DocumentAgent", memory=FAISSMemory())
    print(f"Created: {agent}")
    
    pdf_path = Path(__file__).parent.parent / "example_files" / "resume.pdf"
    if pdf_path.exists():
        print(f"Ingesting PDF: {pdf_path.name}")
        result = agent.execute_tool("ingest_document", filepath=str(pdf_path))
        print(f"  Status: {result['status']}")
        print(f"  Chunks: {result['chunks_stored']}")
        print(f"  Characters: {result['total_characters']:,}")
        
        print("Querying PDF")
        for query in ["experience", "education", "skills"]:
            results = agent.recall_knowledge(query, top_k=1)
            if results:
                print(f"  '{query}': {results[0]['text'][:80]}")
    
    print("Ingesting text file")
    text_file = Path("sample_doc.txt")
    text_file.write_text("""Artificial Intelligence and Machine Learning

Machine learning enables systems to learn from experience without explicit programming.
Deep learning uses neural networks with multiple layers.
Natural language processing helps machines understand human language.
Computer vision enables computers to interpret visual information.""")
    
    result = agent.execute_tool("ingest_document", filepath=str(text_file))
    print(f"  Status: {result['status']}")
    print(f"  Chunks: {result['chunks_stored']}")
    
    print("Querying text")
    results = agent.recall_knowledge("What is deep learning?", top_k=2)
    for i, r in enumerate(results, 1):
        print(f"  {i}. {r['text'][:100]}")
    
    all_knowledge = agent.execute_tool("memory_list")
    print(f"Total entries: {len(all_knowledge)}")
    
    text_file.unlink()
    await agent.cleanup()
    print("Done")


if __name__ == "__main__":
    asyncio.run(main())
