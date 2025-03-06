#!/usr/bin/env python
"""
Test script for the MCP server implementation.
"""
import asyncio
from server import mcp

async def test_server():
    """Test the MCP server functionality."""
    print(f"MCP Server Name: {mcp.name}")
    
    # List available tools
    tools = await mcp.list_tools()
    print(f"Available tools: {[t.name for t in tools]}")
    
    # List available resources
    resources = await mcp.list_resources()
    print(f"Available resources: {[r.pattern for r in resources]}")
    
    print("Server initialized successfully!")

if __name__ == "__main__":
    asyncio.run(test_server())
