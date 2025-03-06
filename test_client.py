#!/usr/bin/env python
"""
Simple test client for MCP server.
"""
import os
import sys
import json
import asyncio
import subprocess
from pathlib import Path

try:
    from mcp.client import Client, Transport
except ImportError:
    print("MCP client not found. Please install with: pip install mcp")
    sys.exit(1)

async def main():
    """Run a simple test client."""
    print("Starting MCP server...")
    server_path = os.path.join(os.path.dirname(__file__), "server.py")
    
    print("Connecting to MCP server...")
    client = Client(Transport.subprocess([sys.executable, server_path]))
    
    # Initialize connection
    await client.initialize()
    
    # Get server info
    capabilities = client.capabilities
    print(f"Connected to: {capabilities.server_info.name}")
    
    # List tools
    tools = await client.list_tools()
    print(f"Available tools: {', '.join(t.name for t in tools)}")
    
    # Test the get_code tool with the server.py file itself
    print(f"\nTesting get_code tool on {server_path}...")
    try:
        result = await client.call_tool("get_code", {"target_file": server_path})
        print(f"Success! Found {len(result.get('referenced_files', []))} reference files")
        print(f"Token count: {result.get('token_count', 0)}/{result.get('token_limit', 0)}")
    except Exception as e:
        print(f"Error calling tool: {e}")
    
    # Clean up
    await client.shutdown()
    print("Test completed.")

if __name__ == "__main__":
    asyncio.run(main())
