#!/usr/bin/env python3
"""Minimal Document Ingestion Example"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.miminions.agent.simple_agent import create_simple_agent
from src.miminions.memory.faiss import FAISSMemory


async def main():
    agent = create_simple_agent("DocAgent", memory=FAISSMemory())
    
    # Create a test file
    test_file = Path("test_doc.txt")
    test_file.write_text("Python is a great programming language.")
    
    doc_id = agent.execute_tool("ingest_file", filepath=str(test_file))
    print(f"Ingested document: {doc_id}")
    
    results = agent.recall_knowledge("programming language")
    print(f"Found: {results[0]['text']}")
    
    test_file.unlink()
    await agent.cleanup()


if __name__ == "__main__":
    asyncio.run(main())