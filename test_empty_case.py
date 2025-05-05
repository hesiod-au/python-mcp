#!/usr/bin/env python3
"""
Test script to run the CodeGrapher on a simple file with no project-specific imports.
This tests the edge case handling when few or no files are found by the analyzer.
"""
import os
import json
import time
from pathlib import Path
import sys

# Add the current directory to the path to import local modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    # Import the modules here to avoid import issues
    from agent import get_python_code
    from code_grapher import CodeGrapher
    
    # Create a simple test file with minimal imports
    test_file = "/tmp/test_simple.py"
    
    # Write a simple Python file with only stdlib imports
    with open(test_file, "w") as f:
        f.write("""
import os
import sys
import time

def hello():
    \"\"\"A simple test function.\"\"\"
    print("Hello, world!")
    print(f"Current time: {time.time()}")
    return os.path.join(os.getcwd(), "test")

if __name__ == "__main__":
    hello()
""")
    
    # Root repository path (same as file in this case)
    root_repo_path = os.path.dirname(test_file)
    
    print(f"Testing CodeGrapher with simple file: {test_file}")
    
    # Start timer
    start_time = time.time()
    
    try:
        # Run get_python_code
        result = get_python_code(test_file, root_repo_path)
        
        # Print summary of the result
        print("\n=== Analysis Results ===")
        print(f"Target file: {os.path.basename(test_file)}")
        print(f"Number of referenced files: {len(result['referenced_files'])}")
        print(f"Number of additional files: {len(result['additional_files'])}")
        
        print("\n=== Referenced Files ===")
        for i, file_data in enumerate(result["referenced_files"], 1):
            object_name = file_data.get("object_name", "")
            object_type = file_data.get("object_type", "")
            print(f"{i}. {file_data['file_path']} - {object_type}: {object_name}")
        
        print("\n=== Additional Files ===")
        for i, file_data in enumerate(result["additional_files"], 1):
            file_type = file_data.get("type", "")
            print(f"{i}. {file_data['file_path']} - Type: {file_type}")
            
        print("\n=== Metadata ===")
        if "metadata" in result:
            for key, value in result["metadata"].items():
                print(f"{key}: {value}")
        
        # Save the detailed result to a file
        with open("empty_case_result.json", "w") as f:
            json.dump(result, f, indent=2)
        
        print(f"\nDetailed analysis saved to: empty_case_result.json")
        
    except Exception as e:
        print(f"Error analyzing file: {e}")
    
    # Clean up the test file
    try:
        os.remove(test_file)
        print(f"Removed temporary test file: {test_file}")
    except:
        pass
        
    # Print the elapsed time
    elapsed_time = time.time() - start_time
    print(f"\nAnalysis completed in {elapsed_time:.2f} seconds")

if __name__ == "__main__":
    main()
