import unittest
import os
import sys
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from code_grapher import CodeGrapher
from agent import get_python_code, handle_mcp_request


class TestCodeGrapher(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_dir = os.path.dirname(self.test_dir)
        self.test_file = os.path.join(self.project_dir, "code_grapher.py")
        self.token_limit = 8000
        self.grapher = CodeGrapher(token_limit=self.token_limit)

    def test_extract_code(self):
        # Replace with a real file path for testing
        result = self.grapher.extract_code(self.test_file)
        
        # Check that we got the expected structure
        self.assertIn("main_object", result)
        self.assertIn("referenced_objects", result)
        self.assertIn("token_count", result)
        self.assertIn("token_limit", result)
        
        # Check that the main object is properly extracted
        self.assertEqual(result["main_object"]["name"], "code_grapher")
        self.assertEqual(result["main_object"]["type"], "module")
        self.assertIsNotNone(result["main_object"]["code"])

    def test_find_all_python_files(self):
        files = self.grapher.find_all_python_files(self.project_dir)
        
        # Should find at least the test file and agent_tools.py
        self.assertGreater(len(files), 1)
        
        # Should include our test file
        self.assertTrue(any(f.endswith("code_grapher.py") for f in files))
        
        # Should not include any __pycache__ files
        self.assertFalse(any("__pycache__" in f for f in files))

    def test_count_tokens(self):
        code = "def hello():\n    print('Hello, world!')"
        token_count = self.grapher._count_tokens(code)
        # This is an approximation - adjust expected count as needed
        self.assertGreaterEqual(token_count, 5)  


class TestToolFunctions(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_dir = os.path.dirname(self.test_dir)
        self.test_file = os.path.join(self.project_dir, "code_grapher.py")

    def test_get_python_code(self):
        # Set up error capture to detect any issues during processing
        from io import StringIO
        import sys
        original_stdout = sys.stdout
        captured_output = StringIO()
        sys.stdout = captured_output
        
        try:
            # Direct test of the function
            result = get_python_code(self.test_file, self.project_dir)
            
            # Verify result structure
            self.assertIn("target_file", result)
            self.assertIn("referenced_files", result)
            self.assertIn("additional_files", result)
            
            # Verify target file data
            self.assertEqual(result["target_file"]["file_path"], os.path.relpath(self.test_file, self.project_dir))
            self.assertIn("code", result["target_file"])
            
            # Check if any errors were printed during execution
            output = captured_output.getvalue()
            self.assertNotIn("Error reading file", output, f"Errors detected during execution:\n{output}")
        finally:
            # Restore stdout
            sys.stdout = original_stdout
        
    def test_mcp_protocol(self):
        # Test the JSON-RPC handler with a tools/list request
        list_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list"
        }
        
        response = handle_mcp_request(list_request)
        
        # Verify response structure
        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["id"], 1)
        self.assertIn("result", response)
        self.assertIn("tools", response["result"])
        
        # Check that get_python_code tool is in the list
        tools = response["result"]["tools"]
        self.assertTrue(any(tool["name"] == "get_python_code" for tool in tools))


if __name__ == "__main__":
    unittest.main()