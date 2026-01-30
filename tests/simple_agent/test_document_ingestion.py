"""Document ingestion tests for Simple Agent."""

import asyncio
from pathlib import Path
from miminions.agent.simple_agent import create_simple_agent
from miminions.memory.faiss import FAISSMemory


async def test_ingest_text():
    print("test_ingest_text")
    agent = create_simple_agent("ChunkAgent", memory=FAISSMemory())
    
    test_file = Path("test_chunked.txt")
    test_file.write_text("""Machine learning is a subset of artificial intelligence.
Deep learning uses neural networks with multiple layers.
Natural language processing enables computers to understand human language.""")
    
    try:
        result = agent.execute_tool("ingest_document", filepath=str(test_file))
        assert result['status'] == 'success'
        assert result['file_type'] == 'text'
        assert result['chunks_stored'] >= 1
        
        results = agent.recall_knowledge("machine learning", top_k=3)
        assert len(results) > 0
        print("PASSED")
    finally:
        test_file.unlink()
        await agent.cleanup()
    return True


async def test_ingest_pdf():
    print("test_ingest_pdf")
    pdf_path = Path(__file__).parent.parent.parent / "examples" / "example_files" / "resume.pdf"
    
    if not pdf_path.exists():
        print("SKIPPED (no PDF)")
        return True
    
    agent = create_simple_agent("PDFAgent", memory=FAISSMemory())
    
    try:
        result = agent.execute_tool("ingest_document", filepath=str(pdf_path))
        assert result['status'] == 'success'
        assert result['file_type'] == 'pdf'
        assert result['chunks_stored'] > 0
        print("PASSED")
    finally:
        await agent.cleanup()
    return True


async def main():
    print("Document Ingestion Tests")
    await test_ingest_text()
    await test_ingest_pdf()
    print("All tests passed")


if __name__ == "__main__":
    asyncio.run(main())
