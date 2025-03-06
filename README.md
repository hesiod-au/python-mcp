# Python MCP Server for Code Graph Extraction

This MCP (Model Context Protocol) server provides tools for extracting and analyzing Python code structures, focusing on import/export relationships between files. This is a lightweight implementation that doesn't require an agent system, making it easy to integrate into any Python application.

## Features

- **Code Relationship Discovery**: Analyze import relationships between Python files
- **Smart Code Extraction**: Extract only the most relevant code sections to stay within token limits
- **Directory Context**: Include files from the same directory to provide better context
- **Documentation Inclusion**: Always include README.md files (or variants) to provide project documentation
- **LLM-Friendly Formatting**: Format code with proper metadata for language models
- **MCP Protocol Support**: Fully compatible with the Model Context Protocol JSON-RPC standard

## The `get_python_code` Tool

The server exposes a powerful code extraction tool that:

- Analyzes a target Python file and discovers all imported modules, classes, and functions
- Returns the complete code of the target file
- Includes code for all referenced objects from other files
- Adds additional contextual files from the same directory
- Respects token limits to avoid overwhelming language models

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/python-mcp-new.git
cd python-mcp-new

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Environment Variables

Create a `.env` file based on the provided `.env.example`:

```
# Token limit for extraction
TOKEN_LIMIT=8000
```

## Usage

### Configuring for MCP Clients

To configure this MCP server for use in MCP-compatible clients (like Codeium Windsurf), add the following configuration to your client's MCP config file:

```json
{
  "mcpServers": {
    "python-code-explorer": {
      "command": "python",
      "args": [
        "/path/to/python-mcp-new/server.py"
      ],
      "env": {
        "TOKEN_LIMIT": "8000"
      }
    }
  }
}
```

Replace `/path/to/python-mcp-new/server.py` with the absolute path to the server.py file on your system.

You can also customize the environment variables:
- `TOKEN_LIMIT`: Maximum token limit for code extraction (default: 8000)

## Usage Examples

### Direct Function Call

```python
from agent import get_python_code

# Get Python code structure for a specific file
result = get_python_code(
    target_file="/home/user/project/main.py",
    root_repo_path="/home/user/project"  # Optional, defaults to target file directory
)

# Process the result
target_file = result["target_file"]
print(f"Main file: {target_file['file_path']}")
print(f"Docstring: {target_file['docstring']}")

# Display related files
for ref_file in result["referenced_files"]:
    print(f"Related file: {ref_file['file_path']}")
    print(f"Object: {ref_file['object_name']}")
    print(f"Type: {ref_file['object_type']}")

# See if we're close to the token limit
print(f"Token usage: {result['token_count']}/{result['token_limit']}")
```

#### Example Response (Direct Function Call)

```python
{
    "target_file": {
        "file_path": "main.py",
        "code": "import os\nimport sys\nfrom utils.helpers import format_output\n\ndef main():\n    args = sys.argv[1:]\n    if not args:\n        print('No arguments provided')\n        return\n    \n    result = format_output(args[0])\n    print(result)\n\nif __name__ == '__main__':\n    main()",
        "type": "target",
        "docstring": ""
    },
    "referenced_files": [
        {
            "file_path": "utils/helpers.py",
            "object_name": "format_output",
            "object_type": "function",
            "code": "def format_output(text):\n    \"\"\"Format the input text for display.\"\"\"\n    if not text:\n        return ''\n    return f'Output: {text.upper()}'\n",
            "docstring": "Format the input text for display.",
            "truncated": false
        }
    ],
    "additional_files": [
        {
            "file_path": "config.py",
            "code": "# Configuration settings\n\nDEBUG = True\nVERSION = '1.0.0'\nMAX_RETRIES = 3\n",
            "type": "related_by_directory",
            "docstring": "Configuration settings for the application."
        }
    ],
    "total_files": 3,
    "token_count": 450,
    "token_limit": 8000
}
```

### Using the MCP Protocol

#### Listing Available Tools

```python
from agent import handle_mcp_request
import json

# List available tools
list_request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
}

response = handle_mcp_request(list_request)
print(json.dumps(response, indent=2))
```

#### Example Response (tools/list)

```json
{
  "jsonrpc": "2.0",
  "id": 1,
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
```

#### Calling get_python_code Tool

```python
from agent import handle_mcp_request
import json

# Call the get_python_code tool
tool_request = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
        "name": "get_python_code",
        "arguments": {
            "target_file": "/home/user/project/main.py",
            "root_repo_path": "/home/user/project"  # Optional
        }
    }
}

response = handle_mcp_request(tool_request)
print(json.dumps(response, indent=2))
```

#### Example Response (tools/call)

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Python code analysis for /home/user/project/main.py"
      },
      {
        "type": "resource",
        "resource": {
          "uri": "resource://python-code/main.py",
          "mimeType": "application/json",
          "data": {
            "target_file": {
              "file_path": "main.py",
              "code": "import os\nimport sys\nfrom utils.helpers import format_output\n\ndef main():\n    args = sys.argv[1:]\n    if not args:\n        print('No arguments provided')\n        return\n    \n    result = format_output(args[0])\n    print(result)\n\nif __name__ == '__main__':\n    main()",
              "type": "target",
              "docstring": ""
            },
            "referenced_files": [
              {
                "file_path": "utils/helpers.py",
                "object_name": "format_output",
                "object_type": "function",
                "code": "def format_output(text):\n    \"\"\"Format the input text for display.\"\"\"\n    if not text:\n        return ''\n    return f'Output: {text.upper()}'\n",
                "docstring": "Format the input text for display.",
                "truncated": false
              }
            ],
            "additional_files": [
              {
                "file_path": "config.py",
                "code": "# Configuration settings\n\nDEBUG = True\nVERSION = '1.0.0'\nMAX_RETRIES = 3\n",
                "type": "related_by_directory",
                "docstring": "Configuration settings for the application."
              }
            ],
            "total_files": 3,
            "token_count": 450,
            "token_limit": 8000
          }
        }
      }
    ],
    "isError": false
  }
}
```

### Handling Errors

```python
from agent import handle_mcp_request

# Call with invalid file path
faulty_request = {
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
        "name": "get_python_code",
        "arguments": {
            "target_file": "/path/to/nonexistent.py"
        }
    }
}

response = handle_mcp_request(faulty_request)
print(json.dumps(response, indent=2))
```

#### Example Error Response

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Error processing Python code: No such file or directory: '/path/to/nonexistent.py'"
      }
    ],
    "isError": true
  }
}
```

## Testing

Run the tests to verify functionality:

```bash
python -m unittest discover tests
```

## Key Components

- **agent.py**: Contains the `get_python_code` function and custom MCP protocol handlers
- **code_grapher.py**: Implements the `CodeGrapher` class for Python code analysis
- **server.py**: Full MCP server implementation using the MCP Python SDK
- **run_server.py**: CLI tool for running the MCP server
- **examples/**: Example scripts showing how to use the MCP server and client
- **tests/**: Comprehensive test cases for all functionality

## Response Format Details

The `get_python_code` tool returns a structured JSON object with the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `target_file` | Object | Information about the target Python file |
| `referenced_files` | Array | List of objects imported by the target file |
| `additional_files` | Array | Additional context files from the same directory |
| `total_files` | Number | Total number of files included in the response |
| `token_count` | Number | Approximate count of tokens in all included code |
| `token_limit` | Number | Maximum token limit configured for extraction |

### Target File Object

| Field | Type | Description |
|-------|------|-------------|
| `file_path` | String | Relative path to the file from the repository root |
| `code` | String | Complete source code of the file |
| `type` | String | Always "target" |
| `docstring` | String | Module-level docstring if available |

### Referenced File Object

| Field | Type | Description |
|-------|------|-------------|
| `file_path` | String | Relative path to the file |
| `object_name` | String | Name of the imported object (class, function, etc.) |
| `object_type` | String | Type of the object ("class", "function", etc.) |
| `code` | String | Source code of the specific object |
| `docstring` | String | Docstring of the object if available |
| `truncated` | Boolean | Whether the code was truncated due to token limits |

### Additional File Object

| Field | Type | Description |
|-------|------|-------------|
| `file_path` | String | Relative path to the file |
| `code` | String | Complete source code of the file |
| `type` | String | Type of relation (e.g., "related_by_directory") |
| `docstring` | String | Module-level docstring if available |

## Using the MCP SDK Server

This project now includes a full-featured Model Context Protocol (MCP) server built with the official [Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk). The server exposes our code extraction functionality in a standardized way that can be used with any MCP client, including Claude Desktop.

### Starting the Server

```bash
# Start the server with default settings
python run_server.py

# Specify a custom name
python run_server.py --name "My Code Explorer"

# Use a specific .env file
python run_server.py --env-file .env.production
```

### Using the MCP Development Mode

With the MCP SDK installed, you can run the server in development mode using the MCP CLI:

```bash
# Install the MCP CLI
pip install "mcp[cli]"

# Start the server in development mode with the Inspector UI
mcp dev server.py
```

This will start the MCP Inspector, a web interface for testing and debugging your server.

### Claude Desktop Integration

You can install the server into Claude Desktop to access your code exploration tools directly from Claude:

```bash
# Install the server in Claude Desktop
mcp install server.py

# With custom configuration
mcp install server.py --name "Python Code Explorer" -f .env
```

### Custom Server Deployment

For custom deployments, you can use the MCP server directly:

```python
from server import mcp

# Configure the server
mcp.name = "Custom Code Explorer"

# Run the server
mcp.run()
```

### Using the MCP Client

You can use the MCP Python SDK to connect to the server programmatically. See the provided example in `examples/mcp_client_example.py`:

```python
from mcp.client import Client, Transport

# Connect to the server
client = Client(Transport.subprocess(["python", "server.py"]))
client.initialize()

# List available tools
for tool in client.tools:
    print(f"Tool: {tool.name}")

# Use the get_code tool
result = client.tools.get_code(target_file="path/to/your/file.py")
print(f"Found {len(result['referenced_files'])} referenced files")

# Clean up
client.shutdown()
```

Run the example:

```bash
python examples/mcp_client_example.py [optional_target_file.py]
```

### Adding Additional Tools

You can add additional tools to the MCP server by decorating functions with the `@mcp.tool()` decorator in `server.py`:

```python
@mcp.tool()
def analyze_imports(target_file: str) -> Dict[str, Any]:
    """Analyze all imports in a Python file."""
    # Implementation code here
    return {
        "file": target_file,
        "imports": [],  # List of imports found
        "analysis": ""  # Analysis of the imports
    }
    
@mcp.tool()
def find_python_files(directory: str, pattern: str = "*.py") -> list[str]:
    """Find Python files matching a pattern in a directory."""
    from pathlib import Path
    return [str(p) for p in Path(directory).glob(pattern) if p.is_file()]
```

You can also add resource endpoints to provide data directly:

```python
@mcp.resource("python_stats://{directory}")
def get_stats(directory: str) -> Dict[str, Any]:
    """Get statistics about Python files in a directory."""
    from pathlib import Path
    stats = {
        "directory": directory,
        "file_count": 0,
        "total_lines": 0,
        "average_lines": 0
    }
    
    files = list(Path(directory).glob("**/*.py"))
    stats["file_count"] = len(files)
    
    if files:
        total_lines = 0
        for file in files:
            with open(file, "r") as f:
                total_lines += len(f.readlines())
        stats["total_lines"] = total_lines
        stats["average_lines"] = total_lines / len(files)
    
    return stats
```

## Model Context Protocol Integration

This project fully embraces the Model Context Protocol (MCP) standard, providing two implementation options:

1. **Native MCP Integration**: The original implementation in `agent.py` provides a direct JSON-RPC interface compatible with MCP.

2. **MCP SDK Integration**: The new implementation in `server.py` leverages the official MCP Python SDK for a more robust and feature-rich experience.

### Benefits of MCP Integration

- **Standardized Interface**: Makes your tools available to any MCP-compatible client
- **Enhanced Security**: Built-in permissions model and resource controls
- **Better LLM Integration**: Seamless integration with Claude Desktop and other LLM platforms
- **Improved Developer Experience**: Comprehensive tooling like the MCP Inspector

### MCP Protocol Version

This implementation supports MCP Protocol version 0.7.0.

For more information about MCP, refer to the [official documentation](https://modelcontextprotocol.io).
