#!/usr/bin/env python
"""
MCP Server Runner

Command-line interface to run the Python Code Explorer MCP server.
"""
import sys
import os
import argparse
from pathlib import Path
from server import mcp

def main():
    """Run the MCP server with command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run the Python Code Explorer MCP server"
    )
    parser.add_argument(
        "--name", 
        default="Python Code Explorer",
        help="Name for the MCP server"
    )
    parser.add_argument(
        "--env-file", 
        "-f", 
        default=".env",
        help="Path to .env file for configuration"
    )
    
    args = parser.parse_args()
    
    # Set server name if provided
    if args.name != "Python Code Explorer":
        mcp.name = args.name
    
    # Load environment variables from specified file
    if os.path.exists(args.env_file):
        try:
            import dotenv
            dotenv.load_dotenv(args.env_file)
            print(f"Loaded environment from {args.env_file}", file=sys.stderr)
        except ImportError:
            print("Warning: python-dotenv not installed, skipping env file loading", file=sys.stderr)
    
    # Run the server
    print(f"Starting {mcp.name} MCP server...", file=sys.stderr)
    mcp.run()

if __name__ == "__main__":
    main()
