"""Document ingestion tests for Minion Agent."""

import asyncio
from pathlib import Path
from miminions.agent import create_minion, ExecutionStatus
from miminions.memory.faiss import FAISSMemory


async def test_ingest_text():
    print("test_ingest_text")
    agent = create_minion("ChunkAgent", memory=FAISSMemory())
    
    test_file = Path("test_chunked.txt")
    test_file.write_text("""Machine learning is a subset of artificial intelligence.
Deep learning uses neural networks with multiple layers.
Natural language processing enables computers to understand human language.""")
    
    try:
        result = agent.execute("ingest_document", filepath=str(test_file))
        
        assert result.status == ExecutionStatus.SUCCESS
        assert result.result['status'] == 'success'
        assert result.result['file_type'] == 'text'
        assert result.result['chunks_stored'] >= 1
        assert result.execution_time_ms is not None
        
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
    
    agent = create_minion("PDFAgent", memory=FAISSMemory())
    
    try:
        result = agent.execute("ingest_document", filepath=str(pdf_path))
        
        assert result.status == ExecutionStatus.SUCCESS
        assert result.result['file_type'] == 'pdf'
        assert result.result['chunks_stored'] > 0
        print("PASSED")
    finally:
        await agent.cleanup()
    return True


async def test_ingest_error():
    print("test_ingest_error")
    agent = create_minion("ErrorAgent", memory=FAISSMemory())
    
    result = agent.execute("ingest_document", filepath="nonexistent.pdf")
    
    assert result.status == ExecutionStatus.ERROR
    assert result.error is not None
    assert "not found" in result.error.lower()
    
    await agent.cleanup()
    print("PASSED")
    return True


async def main():
    print("Pydantic Agent Document Ingestion Tests")
    tests = [test_ingest_text, test_ingest_pdf, test_ingest_error]
    
    passed = 0
    for test in tests:
        try:
            if await test():
                passed += 1
        except Exception as e:
            print(f"FAILED: {e}")
    
    print(f"\n{passed}/{len(tests)} tests passed")


if __name__ == "__main__":
    asyncio.run(main())
