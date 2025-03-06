from __future__ import annotations
import os
import re
import ast
from typing import Any, Dict, List, Optional
from pathlib import Path
from code_grapher import CodeGrapher

# Load token limit from environment variable or use default
import os
default_token_limit = 8000
try:
    import dotenv
    dotenv.load_dotenv()
    token_limit = int(os.getenv('TOKEN_LIMIT', default_token_limit))
except (ImportError, ValueError):
    token_limit = default_token_limit


def get_python_code(target_file: str, root_repo_path: Optional[str] = None) -> Dict[str, Any]:
    """Return the code of the target file and related Python files.
    
    Analyzes the target file and its imports to find the most relevant Python files
    in the codebase. Returns the code in an LLM-friendly format with proper context.
    Always includes README.md files (or variants) as additional files.
    
    Args:
        target_file: Path to the Python file to analyze.
        root_repo_path: Root directory of the repository. If None, will use the
                      directory of the target file.
        
    Returns:
        A dictionary containing the target file's code and related files.
    """
    # Initialize CodeGrapher with token limit
    token_limit = 8000  # Default token limit
    code_grapher = CodeGrapher(token_limit=token_limit)
    
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
    
    # Make sure it's a Python file
    if not target_file.endswith('.py'):
        raise ValueError(f"The target file must be a Python file (.py): {target_file}")
    
    # Find and include README files
    readme_files = find_readme_files(root_repo_path)
    
    # Extract the code graph for the target file
    result = code_grapher.extract_code(target_file, project_root=root_repo_path)
    
    if "error" in result:
        raise ValueError(result["error"])
    
    # Format the target file code
    target_file_rel = os.path.relpath(target_file, root_repo_path)
    target_code = {
        "file_path": target_file_rel,
        "code": result["main_object"]["code"],
        "type": "target",
        "docstring": result["main_object"]["docstring"] or ""
    }
    
    # Calculate token count for target file
    target_token_count = code_grapher._count_tokens(result["main_object"]["code"])
    current_token_count = target_token_count
    token_limit = code_grapher.token_limit
    
    # Format the related files
    related_files = []
    # Create a list to hold files that import the target
    files_importing_target = []
    # Create a list to hold files that are imported by the target
    files_imported_by_target = []
    
    for obj in result["referenced_objects"]:
        # Get relative path for better readability
        rel_path = os.path.relpath(obj["file"], root_repo_path)
        file_token_count = code_grapher._count_tokens(obj["code"])
        file_data = {
            "file_path": rel_path,
            "object_name": obj["name"],
            "object_type": obj["type"],
            "code": obj["code"],
            "docstring": obj["docstring"] or "",
            "truncated": obj.get("truncated", False),
            "token_count": file_token_count
        }
        
        # Categorize if this file is imported by the target or imports the target
        # We'll determine this based on the reference type or relationship
        # This is a placeholder logic that should be adapted based on your actual data structure
        if "referenced_from" in obj and obj["referenced_from"] == target_file:
            # This file is imported by the target
            files_imported_by_target.append(file_data)
        else:
            # This file imports the target
            files_importing_target.append(file_data)
    
    # Find additional Python files in the same directory and related modules
    target_dir = os.path.dirname(target_file)
    additional_files = []
    
    # Get all Python files from the directory structure
    all_python_files = code_grapher.find_all_python_files(root_repo_path)
    
    # Add files from the same directory first (if not already included)
    included_paths = {target_file} | {obj["file"] for obj in result["referenced_objects"]}
    
    # Find potential imports in the target file that weren't resolved
    potential_imports = set()
    try:
        with open(target_file, 'r', encoding='utf-8') as f:
            content = f.read()
        tree = ast.parse(content)
        
        # Extract import names
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    potential_imports.add(name.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    potential_imports.add(node.module.split('.')[0])
        
        print(f"Potential imports found in {target_file}: {potential_imports}")
    except Exception as e:
        print(f"Error analyzing imports in {target_file}: {e}")
    
    # Process files by relevance
    for py_file in all_python_files:
        if py_file not in included_paths:
            # Skip if we've already included enough files
            if len(additional_files) >= 5:  # Increased limit for more context
                break
                
            # Calculate relevance score (higher is more relevant)
            relevance = 0
            
            # Files in same directory are highly relevant
            if os.path.dirname(py_file) == target_dir:
                relevance += 3
            
            # Files that match potential import names are relevant
            basename = os.path.basename(py_file).replace('.py', '')
            if basename in potential_imports:
                relevance += 4
                print(f"Found matching import: {basename} in {py_file}")
            
            # Only include files with some relevance
            if relevance > 0:
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Parse the file to get docstring
                    try:
                        tree = ast.parse(content)
                        docstring = ast.get_docstring(tree) or ""
                    except:
                        docstring = ""
                    
                    rel_path = os.path.relpath(py_file, root_repo_path)
                    additional_files.append({
                        "file_path": rel_path,
                        "code": content,
                        "type": "related_by_directory" if os.path.dirname(py_file) == target_dir else "related_by_import",
                        "docstring": docstring,
                        "relevance": relevance,
                        "token_count": code_grapher._count_tokens(content)
                    })
                    print(f"Added related file: {rel_path} (relevance: {relevance})")
                except Exception as e:
                    print(f"Error reading file {py_file}: {e}")
    
    # Sort additional files by relevance (but we'll use token count later when adding files)
    additional_files.sort(key=lambda x: x.pop('relevance', 0), reverse=True)
    
    # Add README files to additional files and track token count
    readme_files_data = []
    for readme_path in readme_files:
        try:
            with open(readme_path, 'r', encoding='utf-8') as f:
                readme_content = f.read()
            
            rel_path = os.path.relpath(readme_path, root_repo_path)
            readme_token_count = code_grapher._count_tokens(readme_content)
            readme_files_data.append({
                "file_path": rel_path,
                "code": readme_content,
                "type": "readme",
                "docstring": "Project documentation",
                "token_count": readme_token_count
            })
            print(f"Added README file: {rel_path} (tokens: {readme_token_count})")
            # Add README token count to current count
            current_token_count += readme_token_count
        except Exception as e:
            print(f"Error reading README file {readme_path}: {e}")
    
    # Begin building the final list of referenced files with target file already counted
    final_referenced_files = []
    
    # Sort imported files by size (smallest to largest)
    files_imported_by_target.sort(key=lambda x: x["token_count"])
    
    # Sort files that import the target by size (smallest to largest)
    files_importing_target.sort(key=lambda x: x["token_count"])
    
    # Add files that the target imports, from smallest to largest
    for file_data in files_imported_by_target:
        # Check if we have enough token budget
        if current_token_count + file_data["token_count"] <= token_limit:
            final_referenced_files.append({
                "file_path": file_data["file_path"],
                "object_name": file_data["object_name"],
                "object_type": file_data["object_type"],
                "code": file_data["code"],
                "docstring": file_data["docstring"],
                "truncated": file_data["truncated"]
            })
            current_token_count += file_data["token_count"]
            print(f"Added imported file: {file_data['file_path']} (tokens: {file_data['token_count']})")
    
    # Add files that import the target, from smallest to largest
    for file_data in files_importing_target:
        # Check if we have enough token budget
        if current_token_count + file_data["token_count"] <= token_limit:
            final_referenced_files.append({
                "file_path": file_data["file_path"],
                "object_name": file_data["object_name"],
                "object_type": file_data["object_type"],
                "code": file_data["code"],
                "docstring": file_data["docstring"],
                "truncated": file_data["truncated"]
            })
            current_token_count += file_data["token_count"]
            print(f"Added file importing target: {file_data['file_path']} (tokens: {file_data['token_count']})")
    
    # Format the additional files without the token counts
    final_additional_files = []
    for readme_file in readme_files_data:
        final_additional_files.append({
            "file_path": readme_file["file_path"],
            "code": readme_file["code"],
            "type": readme_file["type"],
            "docstring": readme_file["docstring"]
        })
    
    # Add other additional files if there's token budget left
    for file_data in additional_files:
        # Check if we have enough token budget
        if current_token_count + file_data["token_count"] <= token_limit:
            final_additional_files.append({
                "file_path": file_data["file_path"],
                "code": file_data["code"],
                "type": file_data["type"],
                "docstring": file_data["docstring"]
            })
            current_token_count += file_data["token_count"]
    
    # Format the response as LLM-friendly content
    llm_friendly_format = {
        "target_file": target_code,
        "referenced_files": final_referenced_files,
        "additional_files": final_additional_files,
        "total_files": 1 + len(final_referenced_files) + len(final_additional_files),
        "token_count": current_token_count,
        "token_limit": token_limit
    }
    
    return llm_friendly_format


def find_readme_files(root_path: str) -> List[str]:
    """Find README files in the repository.
    
    Searches for README.md and variants in the repository root and subdirectories.
    
    Args:
        root_path: Root directory of the repository.
        
    Returns:
        List of paths to README files.
    """
    readme_files = []
    readme_patterns = ['README.md', 'README.txt', 'README', 'readme.md', 'Readme.md']
    
    # Check for README in the root directory first
    for pattern in readme_patterns:
        readme_path = os.path.join(root_path, pattern)
        if os.path.isfile(readme_path):
            readme_files.append(readme_path)
            print(f"Found README file in root: {readme_path}")
            break  # Only include one README from the root directory
    
    return readme_files


# Simple JSON-RPC handler to expose the tool
def handle_mcp_request(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle MCP protocol JSON-RPC requests.
    
    This function implements a minimal MCP server that can list and call tools.
    
    Args:
        request_data: A JSON-RPC request following the MCP protocol.
        
    Returns:
        A JSON-RPC response following the MCP protocol.
    """
    # Extract the method and params from the request
    method = request_data.get("method", "")
    params = request_data.get("params", {})
    req_id = request_data.get("id")
    
    # Handle tool listing
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "get_python_code",
                        "description": "Return the code of a target Python file and related files based on import/export proximity.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "target_file": {
                                    "type": "string",
                                    "description": "Path to the Python file to analyze."
                                },
                                "root_repo_path": {
                                    "type": "string",
                                    "description": "Root directory of the repository. If not provided, the directory of the target file will be used."
                                }
                            },
                            "required": ["target_file"]
                        }
                    }
                ]
            }
        }
    
    # Handle tool calling
    elif method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})
        
        if tool_name == "get_python_code":
            try:
                target_file = args.get("target_file")
                root_repo_path = args.get("root_repo_path")
                
                if not target_file:
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {
                            "code": -32602,
                            "message": "Missing required argument: target_file"
                        }
                    }
                
                result = get_python_code(target_file, root_repo_path)
                
                # Convert to MCP-friendly format
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Python code analysis for {target_file}"
                            },
                            {
                                "type": "resource",
                                "resource": {
                                    "uri": f"resource://python-code/{os.path.basename(target_file)}",
                                    "mimeType": "application/json",
                                    "data": result
                                }
                            }
                        ],
                        "isError": False
                    }
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Error processing Python code: {str(e)}"
                            }
                        ],
                        "isError": True
                    }
                }
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Unknown tool: {tool_name}"
                }
            }
    
    # Handle capability negotiation
    elif method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "capabilities": {
                    "tools": {
                        "listChanged": False  # We don't support dynamic tool changes
                    }
                }
            }
        }
    
    # Handle unknown methods
    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }