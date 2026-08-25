"""Document ingestion tests for Minion Agent."""

import asyncio
from pathlib import Path

import pytest

pytest.importorskip("sqlite_vec")

from miminions.agent import create_minion
from miminions.tools.schemas import ExecutionStatus
import pytest

pytest.importorskip("sqlite_vec")
from miminions.memory.sqlite import SQLiteMemory


async def test_ingest_text():
    print("test_ingest_text")
    agent = create_minion("ChunkAgent", memory=SQLiteMemory(db_path=":memory:"))
    
    test_file = Path("test_chunked.txt")
    test_file.write_text("""Machine learning is a subset of artificial intelligence.
Deep learning uses neural networks with multiple layers.
Natural language processing enables computers to understand human language.""")
    
    try:
        result = agent.execute("ingest_document", filepath=str(test_file))
        
        assert result.status == ExecutionStatus.SUCCESS, f"expect ExecutionStatus.SUCCESS as {ExecutionStatus.SUCCESS}, got {result.status}"
        assert result.result['status'] == 'success', f"expect ingest_document returns success status for valid text file input as 'success', got {result.result['status']}"
        assert result.result['file_type'] == 'text', f"expect ingest_document classifies plain text file input as file_type text as 'text', got {result.result['file_type']}"
        assert result.result['chunks_stored'] >= 1, f"expect result.result['chunks_stored'] >= 1, got {result.result['chunks_stored']}"
        assert result.execution_time_ms is not None, f"expect value is not None, got {result.execution_time_ms}"
        
        results = agent.recall_knowledge("machine learning", top_k=3)
        result_count = len(results)
        assert result_count > 0, f"expect len(results) > 0, got {result_count}"
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
    
    agent = create_minion("PDFAgent", memory=SQLiteMemory(db_path=":memory:"))
    
    try:
        result = agent.execute("ingest_document", filepath=str(pdf_path))
        
        assert result.status == ExecutionStatus.SUCCESS, f"expect ExecutionStatus.SUCCESS as {ExecutionStatus.SUCCESS}, got {result.status}"
        assert result.result['file_type'] == 'pdf', f"expect ingest_document classifies PDF input as file_type pdf as 'pdf', got {result.result['file_type']}"
        assert result.result['chunks_stored'] > 0, f"expect result.result['chunks_stored'] > 0, got {result.result['chunks_stored']}"
        print("PASSED")
    finally:
        await agent.cleanup()
    return True


async def test_ingest_error():
    print("test_ingest_error")
    agent = create_minion("ErrorAgent", memory=SQLiteMemory(db_path=":memory:"))
    
    result = agent.execute("ingest_document", filepath="nonexistent.pdf")
    
    assert result.status == ExecutionStatus.ERROR, f"expect ExecutionStatus.ERROR as {ExecutionStatus.ERROR}, got {result.status}"
    assert result.error is not None, f"expect value is not None, got {result.error}"
    error_text_lower = result.error.lower()
    assert "not found" in error_text_lower, f"expect contains 'not found', got {error_text_lower}"
    
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
