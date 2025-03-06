#!/usr/bin/env python
"""
Example MCP client for the Python Code Explorer server.

This script demonstrates how to use the MCP Python SDK to communicate with
the Python Code Explorer server.
"""
import os
import sys
import json
from pathlib import Path

# Ensure parent directory is in sys.path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# Import the MCP client from the SDK
try:
    from mcp.client import Client, Transport
except ImportError:
    print("Please install the MCP SDK: pip install mcp")
    sys.exit(1)

def print_formatted_json(data):
    """Print data as formatted JSON."""
    print(json.dumps(data, indent=2))

def main():
    """Run the MCP client example."""
    # Start a subprocess transport to the server
    server_path = os.path.join(parent_dir, "server.py")
    print(f"Connecting to server at: {server_path}")
    
    # Create an MCP client that connects to our server
    client = Client(Transport.subprocess([sys.executable, server_path]))
    
    # Initialize the connection
    client.initialize()
    
    print("\n=== Server Information ===")
    capabilities = client.capabilities
    print(f"Server name: {capabilities.server_info.name}")
    
    # List available tools
    print("\n=== Available Tools ===")
    tools = list(client.tools)
    for tool in tools:
        print(f"Tool: {tool.name}")
        print(f"  Description: {tool.description}")
        print(f"  Schema: {tool.schema}")
        print()
    
    # Example: Call the get_code tool
    if len(sys.argv) > 1:
        target_file = sys.argv[1]
    else:
        # Use the server.py file as an example
        target_file = server_path
    
    print(f"\n=== Analyzing Python Code: {target_file} ===")
    result = client.tools.get_code(target_file=target_file)
    
    # Print summary of the result
    print("\n=== Analysis Results ===")
    print(f"Target file: {result['target_file']['file_path']}")
    print(f"Referenced files: {len(result['referenced_files'])}")
    print(f"Additional files: {len(result['additional_files'])}")
    print(f"Token usage: {result['token_count']}/{result['token_limit']}")
    
    # Print the first few lines of the target file's code
    code_lines = result['target_file']['code'].split('\n')[:5]
    print("\n=== Target File Preview ===")
    for line in code_lines:
        print(line)
    print("...")
    
    # Clean up
    client.shutdown()
    
if __name__ == "__main__":
    main()
