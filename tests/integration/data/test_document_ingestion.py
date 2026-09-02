"""Document ingestion tests for Minion Agent."""

from pathlib import Path

import pytest

pytest.importorskip("sqlite_vec")

from miminions.agent import create_minion
from miminions.memory.sqlite import SQLiteMemory
from miminions.tools.schemas import ExecutionStatus


async def test_ingest_text(tmp_path):
    print("test_ingest_text")
    agent = create_minion("ChunkAgent", memory=SQLiteMemory(db_path=":memory:"))
    
    test_file = tmp_path / "test_chunked.txt"
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
        await agent.cleanup()


async def test_ingest_pdf():
    print("test_ingest_pdf")
    pdf_path = Path(__file__).parents[3] / "examples" / "example_files" / "resume.pdf"

    assert pdf_path.exists(), f"expect PDF fixture at {pdf_path}, got missing"
    
    agent = create_minion("PDFAgent", memory=SQLiteMemory(db_path=":memory:"))
    
    try:
        result = agent.execute("ingest_document", filepath=str(pdf_path))
        
        assert result.status == ExecutionStatus.SUCCESS, f"expect ExecutionStatus.SUCCESS as {ExecutionStatus.SUCCESS}, got {result.status}"
        assert result.result['file_type'] == 'pdf', f"expect ingest_document classifies PDF input as file_type pdf as 'pdf', got {result.result['file_type']}"
        assert result.result['chunks_stored'] > 0, f"expect result.result['chunks_stored'] > 0, got {result.result['chunks_stored']}"
        print("PASSED")
    finally:
        await agent.cleanup()


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
