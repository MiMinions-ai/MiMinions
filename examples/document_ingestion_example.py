#!/usr/bin/env python3
"""
Document Ingestion Example

This example demonstrates how to ingest documents (PDF and text files)
into an agent's memory using the chunking feature for better retrieval.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.miminions.agent.simple_agent import create_simple_agent
from src.miminions.memory.faiss import FAISSMemory


async def main():    
    print("="*60)
    print("Document Ingestion Example")
    print("="*60)
    
    # Create an agent with memory
    print("\nCreating agent with FAISS memory...")
    agent = create_simple_agent(
        name="DocumentAgent",
        description="An agent that can ingest and retrieve documents",
        memory=FAISSMemory()
    )
    
    print(f"   Created: {agent}")
    print(f"   Available tools: {len(agent.list_tools())}")
    
    # Ingest a PDF document
    pdf_path = Path(__file__).parent / "example_files" / "resume.pdf"
    
    if pdf_path.exists():
        print(f"\nIngesting PDF: {pdf_path.name}")
        
        result = agent.execute_tool("ingest_document", filepath=str(pdf_path))
        
        print(f"   Status: {result['status']}")
        print(f"   Message: {result['message']}")
        print(f"   File type: {result['file_type']}")
        print(f"   Total characters: {result['total_characters']:,}")
        print(f"   Chunks stored: {result['chunks_stored']}")
        print(f"   Chunk size: {result['chunk_size']}")
        print(f"   Overlap: {result['overlap']}")
        
        # 3. Query the ingested document
        print("\nQuerying the PDF document...")
        
        queries = [
            "experience",
            "education",
            "skills"
        ]
        
        for query in queries:
            print(f"\n   Query: '{query}'")
            results = agent.recall_knowledge(query, top_k=2)
            
            print(f"   Found {len(results)} relevant chunks:")
            for i, item in enumerate(results, 1):
                text_preview = item['text'][:120].replace('\n', ' ')
                print(f"     {i}. {text_preview}...")
                chunk_info = item.get('metadata', {})
                print(f"        (Chunk {chunk_info.get('chunk_index', '?')} of {chunk_info.get('total_chunks', '?')})")
    
    else:
        print(f"\nPDF not found at {pdf_path}")
        print("   Skipping PDF ingestion demo")
    
    # Ingest a text file
    print("\nCreating and ingesting a text file...")
    
    text_file = Path("sample_ai_document.txt")
    sample_content = """Artificial Intelligence and Machine Learning

Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed.

Deep Learning
Deep learning is a specialized form of machine learning that uses neural networks with multiple layers. These networks can learn hierarchical representations of data.

Natural Language Processing
NLP is a field of AI that focuses on the interaction between computers and human language. It enables machines to understand, interpret, and generate human language.

Computer Vision
Computer vision is an AI field that enables computers to derive meaningful information from digital images and videos. Applications include facial recognition, object detection, and autonomous vehicles.

Applications
Modern AI applications include healthcare diagnostics, financial fraud detection, autonomous vehicles, virtual assistants, and recommendation systems."""
    
    text_file.write_text(sample_content)
    
    result = agent.execute_tool("ingest_document", filepath=str(text_file))
    
    print(f"   Status: {result['status']}")
    print(f"   Message: {result['message']}")
    print(f"   Chunks stored: {result['chunks_stored']}")
    
    # 5. Query the text document
    print("\n5. Querying the text document...")
    query = "What is deep learning?"
    print(f"   Query: '{query}'")
    
    results = agent.recall_knowledge(query, top_k=2)
    print(f"   Found {len(results)} relevant chunks:\n")
    
    for i, item in enumerate(results, 1):
        print(f"   Chunk {i}:")
        print(f"   {item['text'][:200]}...\n")
        metadata = item.get('metadata', {})
        print(f"   Source: {metadata.get('filename')}")
        print(f"   Chunk: {metadata.get('chunk_index')}/{metadata.get('total_chunks')}")
        print()
    
    # 6. List all knowledge in memory
    print("\n6. Memory statistics...")
    all_knowledge = agent.execute_tool("memory_list")
    print(f"   Total entries in memory: {len(all_knowledge)}")
    
    # Cleanup
    print("\n7. Cleaning up...")
    text_file.unlink()
    await agent.cleanup()
    
    print("\n" + "="*60)
    print("Example completed successfully!")
    print("="*60)
    print("\nKey features demonstrated:")
    print(" - PDF and text file ingestion")
    print(" - Automatic text chunking for better retrieval")
    print(" - Semantic search across all chunks")
    print(" - Metadata preservation (source, chunk index, etc.)")


if __name__ == "__main__":
    asyncio.run(main())