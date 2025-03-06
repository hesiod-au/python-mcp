#!/usr/bin/env python3
"""
Test script for the CodeGrapher class to debug why it's not finding related files.
"""
import os
import sys
from pathlib import Path
from code_grapher import CodeGrapher
from pprint import pprint

def test_codegrapher(target_file: str, root_repo_path: str = None):
    """
    Test the CodeGrapher with debug print statements to diagnose issues.
    
    Args:
        target_file: Path to the Python file to analyze
        root_repo_path: Root directory of the repository
    """
    print(f"=== Testing CodeGrapher with target_file: {target_file} ===")
    
    # Set root_repo_path if not provided
    if root_repo_path is None:
        if os.path.isabs(target_file):
            root_repo_path = os.path.dirname(target_file)
        else:
            root_repo_path = os.path.dirname(os.path.abspath(target_file))
    
    # Ensure absolute path for target file
    if not os.path.isabs(target_file):
        target_file = os.path.join(root_repo_path, target_file)
    
    target_file = os.path.abspath(target_file)
    root_repo_path = os.path.abspath(root_repo_path)
    
    print(f"Absolute target_file: {target_file}")
    print(f"Absolute root_repo_path: {root_repo_path}")
    
    # Initialize CodeGrapher
    code_grapher = CodeGrapher(token_limit=8000)
    
    # Find all Python files in the repository
    print("\n=== All Python files in repository ===")
    python_files = code_grapher.find_all_python_files(root_repo_path)
    print(f"Found {len(python_files)} Python files in repository")
    for file in python_files:
        print(f"  - {file}")
    
    # Extract code
    print("\n=== Extracting code ===")
    result = code_grapher.extract_code(target_file, project_root=root_repo_path)
    
    if "error" in result:
        print(f"Error: {result['error']}")
        return
    
    # Print visited files
    print("\n=== Visited files ===")
    print(f"Visited {len(code_grapher.visited_files)} files:")
    for file in code_grapher.visited_files:
        print(f"  - {file}")
    
    # Print referenced objects
    print("\n=== Referenced objects ===")
    print(f"Found {len(result['referenced_objects'])} referenced objects:")
    for obj in result['referenced_objects']:
        print(f"  - {obj['name']} ({obj['type']}) from {obj['file']}")
    
    # Print main object info
    print("\n=== Main object info ===")
    print(f"Name: {result['main_object']['name']}")
    print(f"Type: {result['main_object']['type']}")
    print(f"File: {result['main_object']['file']}")
    print(f"Docstring: {result['main_object']['docstring'][:100]}...")
    
    # Print token counts
    print(f"\nToken count: {result['token_count']}")
    print(f"Token limit: {result['token_limit']}")
    
    # Debug _is_external_library function
    print("\n=== Testing _is_external_library function ===")
    test_paths = [
        "/usr/lib/python3.10/py_compile.py",
        "/usr/lib/python3.10/plistlib.py",
        f"{root_repo_path}/.venv/lib/python3.10/site-packages/dotenv/parser.py",
        "/usr/lib/python3.10/csv.py",
        "/usr/lib/python3.10/encodings/mbcs.py",
        "/usr/lib/python3.10/shutil.py",
        "/usr/lib/python3.10/contextlib.py",
        f"{root_repo_path}/agent.py",
        f"{root_repo_path}/code_grapher.py",
        f"{root_repo_path}/server.py"
    ]
    
    for path in test_paths:
        is_external = code_grapher._is_external_library(path)
        print(f"  - {path}: {'EXTERNAL' if is_external else 'PROJECT'}")
    
    # Debug import resolution
    print("\n=== Debugging import resolution ===")
    # Parse the target file
    ast_tree, source_code = code_grapher._parse_file(target_file)
    if ast_tree:
        print("Successfully parsed target file")
        print("Imports found:")
        import ast
        for node in ast.walk(ast_tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    print(f"  - import {name.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for name in node.names:
                        print(f"  - from {node.module} import {name.name}")
    else:
        print("Failed to parse target file")

if __name__ == "__main__":
    # Use the first argument as the target file, or default to agent.py
    target_file = sys.argv[1] if len(sys.argv) > 1 else "agent.py"
    
    # Use the second argument as the root repo path, or default to current directory
    root_repo_path = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(os.path.abspath(__file__))
    
    test_codegrapher(target_file, root_repo_path)
