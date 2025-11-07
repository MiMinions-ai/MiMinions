#!/usr/bin/env python3
"""Minimal Document Ingestion Test"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.miminions.agent.simple_agent import create_simple_agent
from src.miminions.memory.faiss import FAISSMemory


async def test_ingest_file():
    """Test file ingestion"""
    agent = create_simple_agent("TestAgent", memory=FAISSMemory())
    
    test_file = Path("test.txt")
    test_file.write_text("Machine learning is awesome.")
    
    # Ingest
    doc_id = agent.execute_tool("ingest_file", filepath=str(test_file))
    assert doc_id, "Should return doc ID"
    
    # Query
    results = agent.recall_knowledge("machine learning")
    assert len(results) > 0, "Should find results"
    assert "learning" in results[0]["text"], "Should match content"
    
    test_file.unlink()
    await agent.cleanup()
    print("File ingestion test passed")
    return True


async def main():
    try:
        await test_ingest_file()
        return 0
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))