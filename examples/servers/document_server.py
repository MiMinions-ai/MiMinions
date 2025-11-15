#!/usr/bin/env python3
"""Minimal Document MCP Server"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("DocumentServer")

@mcp.tool()
def ingest_document(filepath: str) -> str:
    """Ingest a text file and return its content"""
    with open(filepath, 'r') as f:
        return f.read()

if __name__ == "__main__":
    mcp.run(transport="stdio")