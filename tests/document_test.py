#!/usr/bin/env python3
"""Document Ingestion Test - Testing PDF and text file ingestion with chunking"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.miminions.agent.simple_agent import create_simple_agent
from src.miminions.memory.faiss import FAISSMemory

async def test_ingest_document_text():
    """Test document ingestion with chunking for text files"""
    agent = create_simple_agent("ChunkAgent", memory=FAISSMemory())
    
    test_file = Path("test_chunked.txt")
    # Create longer text to test chunking
    test_content = """This is a test document for chunking.

Machine learning is a subset of artificial intelligence that focuses on the development of algorithms.
Deep learning is a specialized subset of machine learning that uses neural networks.

Natural language processing enables computers to understand human language.
Computer vision allows machines to interpret visual information from the world.

These technologies are transforming industries worldwide."""
    
    test_file.write_text(test_content)
    
    try:
        # Ingest with chunking
        result = agent.execute_tool("ingest_document", filepath=str(test_file))
        
        print(f"\n  Status: {result['status']}")
        print(f"  File type: {result['file_type']}")
        print(f"  Chunks stored: {result['chunks_stored']}")
        print(f"  Total characters: {result['total_characters']}")
        
        assert result['status'] == 'success'
        assert result['file_type'] == 'text'
        assert result['chunks_stored'] >= 1
        
        # Test retrieval
        results = agent.recall_knowledge("machine learning", top_k=3)
        assert len(results) > 0, "Should find matching chunks"
        
        print("✓ Document ingestion with chunking test passed")
        
    finally:
        test_file.unlink()
        await agent.cleanup()
    
    return True


async def test_ingest_pdf():
    """Test PDF ingestion"""
    # Check if PDF exists
    pdf_path = Path(__file__).parent.parent / "examples" / "example_files" / "resume.pdf"
    
    if not pdf_path.exists():
        print("⚠ PDF file not found, skipping PDF test")
        return True
    
    agent = create_simple_agent("PDFAgent", memory=FAISSMemory())
    
    try:
        # Ingest PDF
        result = agent.execute_tool("ingest_document", filepath=str(pdf_path))
        
        print(f"\n  Status: {result['status']}")
        print(f"  File: {result['filepath']}")
        print(f"  File type: {result['file_type']}")
        print(f"  Chunks stored: {result['chunks_stored']}")
        print(f"  Total characters: {result['total_characters']}")
        print(f"  Chunk size: {result['chunk_size']}")
        
        assert result['status'] == 'success'
        assert result['file_type'] == 'pdf'
        assert result['chunks_stored'] > 0
        
        # Test retrieval
        results = agent.recall_knowledge("experience", top_k=3)
        print(f"\n  Found {len(results)} relevant chunks for query 'experience'")
        
        if results:
            print(f"  Top result preview: {results[0]['text'][:100]}...")
        
        print("✓ PDF ingestion test passed")
        
    finally:
        await agent.cleanup()
    
    return True


async def main():
    print("Starting document ingestion tests...\n")
    
    try:
        await test_ingest_document_text()
        await test_ingest_pdf()
        
        print("\n" + "="*50)
        print("All tests passed! ✓")
        print("="*50)
        return 0
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))