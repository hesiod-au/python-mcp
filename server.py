#!/usr/bin/env python
"""
Python MCP Server for Code Graph Extraction

This server exposes Python code extraction functionality through the Model
Context Protocol (MCP).
"""
from __future__ import annotations
import os
import sys
import json
from typing import Optional, List, Union
from pathlib import Path
from pydantic import BaseModel, Field

from mcp.server.fastmcp import FastMCP
from agent import get_python_code

# Create an MCP server with a descriptive name
mcp = FastMCP("Python Code Explorer")

# Set dependencies for deployment
mcp.dependencies = ["python-dotenv>=0.20.0"]


# Define Pydantic models for the response structure
class CodeFile(BaseModel):
    file_path: str = Field(..., description="Path to the file")
    code: str = Field(..., description="File content")
    imports: List[str] = Field(default_factory=list, description="List of imports")
    docstring: Optional[str] = Field(None, description="Module docstring")

class CodeRelation(BaseModel):
    file_path: str = Field(..., description="Path to the related file")
    type: str = Field(..., description="Relationship type")
    docstring: Optional[str] = Field(None, description="Module docstring")

class CodeResponse(BaseModel):
    target_file: CodeFile = Field(..., description="Target file content")
    referenced_files: List[CodeFile] = Field(default_factory=list, description="Referenced files")
    additional_files: List[CodeRelation] = Field(default_factory=list, description="Additional related files")
    token_count: int = Field(..., description="Approximate token count")
    token_limit: int = Field(..., description="Token limit for extraction")

@mcp.tool()
def get_python_code(target_file: str, root_repo_path: Optional[str] = None) -> dict:
    """
    Extract Python code from a target file, along with related imported files.
    
    This tool analyzes a Python file's imports and returns the most relevant
    code in a structured format suitable for LLMs. It always includes README.md
    (or variants) as additional files to provide project context.
    
    Args:
        target_file: Path to the Python file to analyze.
        root_repo_path: Root directory of the repository. If not provided,
                      the directory of the target file will be used.
    
    Returns:
        A dictionary containing the target file, related code files, and README files.
    """
    # Delegate to the implementation in agent.py
    result = get_python_code(target_file=target_file, root_repo_path=root_repo_path)
    # Convert to JSON and back to ensure consistent structure
    return json.loads(json.dumps(result))


@mcp.resource("python_code://{target_file}")
def get_python_code_resource(target_file: str) -> dict:
    """
    Access Python code as a resource.
    
    This resource provides Python code from a specified file along with
    its dependencies.
    
    Args:
        target_file: Path to the Python file to analyze.
    
    Returns:
        A dictionary containing the target file and related code files.
    """
    # Get absolute path if provided as relative
    if not os.path.isabs(target_file):
        target_file = os.path.abspath(target_file)
    
    # Delegate to the implementation and convert to JSON and back for consistency
    result = get_python_code(target_file=target_file)
    return json.loads(json.dumps(result))


@mcp.prompt()
def analyze_code(target_file: str) -> str:
    """
    Create a prompt for analyzing Python code.
    
    Args:
        target_file: Path to the Python file to analyze.
    
    Returns:
        A prompt for LLMs to analyze the provided code.
    """
    return f"""
    Please analyze the Python code from {target_file} and provide a detailed review.
    
    Focus on:
    1. Code structure and organization
    2. Potential bugs or issues
    3. Performance considerations
    4. Best practices and style improvements
    
    Present your analysis in a comprehensive, well-structured format.
    """


# Run the server if executed directly
if __name__ == "__main__":
    mcp.run()
