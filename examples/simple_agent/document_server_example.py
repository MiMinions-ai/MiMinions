#!/usr/bin/env python3
"""Example using Document MCP Server"""

import asyncio
import sys
from pathlib import Path
from mcp import StdioServerParameters

sys.path.insert(0, str(Path(__file__).parent.parent))

from miminions.agent.simple_agent import create_simple_agent


async def main():
    agent = create_simple_agent("DocServerAgent")
    
    server_params = StdioServerParameters(
        command="python3",
        args=["examples/servers/document_server.py"]
    )
    
    await agent.connect_mcp_server("doc_server", server_params)
    await agent.load_tools_from_mcp_server("doc_server")
    
    print(f"Available tools: {agent.list_tools()}")
    
    test_file = Path("test_mcp.txt")
    test_file.write_text("MCP document server is working!")
    
    content = await agent.execute_tool_async("ingest_document", filepath=str(test_file))
    print(f"Ingested content: {content}")
    
    test_file.unlink()
    await agent.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
