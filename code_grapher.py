import ast
import os
import re
import importlib.util
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple

class CodeGrapher:
    """
    Extract and navigate Python code structure across files.
    
    This class parses Python code, follows imports and references,
    and extracts structured code snippets up to a token limit.
    
    Attributes:
        token_limit (int): Maximum number of tokens to include in output.
        visited_files (Set[str]): Set of file paths that have been processed.
        referenced_objects (List[Dict[str, Any]]): List of objects referenced in the code.
    """
    
    def __init__(self, token_limit: int = 8000) -> None:
        """
        Initialize the CodeGrapher.
        
        Args:
            token_limit: Maximum number of tokens to include in output.
        """
        self.token_limit: int = token_limit
        self.visited_files: Set[str] = set()
        self.referenced_objects: List[Dict[str, Any]] = []
    
    def extract_code(
        self, 
        target_file: str, 
        target_object: Optional[str] = None, 
        token_limit: Optional[int] = None,
        project_root: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract code from a file, optionally focusing on a specific object.
        
        This method parses the target file, extracts the specified object (or the
        entire file if no object is specified), and follows imports to build a
        comprehensive code representation up to the token limit.
        
        Args:
            target_file: Path to the Python file to analyze.
            target_object: Name of specific class or function to extract.
                If None, extracts the entire file.
            token_limit: Override the default token limit.
                If None, uses the limit specified during initialization.
            project_root: The root directory of the project. Used to determine if a file
                is within the project or an external library.
            
        Returns:
            A dictionary containing:
                - 'main_object': Information about the primary extracted object
                - 'referenced_objects': List of objects referenced by the main object
                - 'token_count': Total number of tokens in the extracted code
                - 'token_limit': The token limit used for extraction
                - 'error': Error message if extraction failed (only present on error)
        """
        # Reset state for new extraction
        self.visited_files = set()
        self.referenced_objects = []
        
        # Update token limit if specified
        if token_limit is not None:
            self.token_limit = token_limit
        
        # Convert to absolute path
        target_file = os.path.abspath(target_file)
        
        # Set project_root if not provided
        if project_root is None:
            project_root = os.path.dirname(target_file)
        project_root = os.path.abspath(os.path.normpath(project_root))
        
        # Parse the target file
        ast_tree, source_code = self._parse_file(target_file)
        if not ast_tree:
            return {"error": f"Failed to parse file: {target_file}"}
        
        # Extract the main object or whole file
        main_object = None
        if target_object:
            main_object = self._extract_object(ast_tree, source_code, target_object, target_file)
            if not main_object:
                return {"error": f"Object '{target_object}' not found in {target_file}"}
        else:
            # Extract the entire module as main object
            module_code = source_code
            main_object = {
                "name": os.path.basename(target_file).replace(".py", ""),
                "file": target_file,
                "type": "module",
                "code": module_code,
                "docstring": ast.get_docstring(ast_tree) or ""
            }
        
        # Mark the target file as visited
        self.visited_files.add(target_file)
        
        # Resolve and follow imports, but only within the project
        self._resolve_imports(ast_tree, target_file)
        
        # Filter out referenced objects from external libraries
        self.referenced_objects = [
            obj for obj in self.referenced_objects 
            if not self._is_external_library(obj["file"]) and os.path.abspath(obj["file"]).startswith(project_root)
        ]
        
        # Count tokens
        main_token_count = self._count_tokens(main_object["code"])
        
        # Create result structure
        result = {
            "main_object": main_object,
            "referenced_objects": self.referenced_objects.copy(),
            "token_count": main_token_count + sum(self._count_tokens(obj["code"]) for obj in self.referenced_objects),
            "token_limit": self.token_limit
        }
        
        # Prioritize and trim code if needed
        if result["token_count"] > self.token_limit:
            result = self._prioritize_code(result)
        
        return result
    
    def _parse_file(self, filepath: str) -> Tuple[Optional[ast.Module], Optional[str]]:
        """
        Parse a Python file into an AST.
        
        Reads the file content and parses it into an Abstract Syntax Tree for analysis.
        
        Args:
            filepath: Path to the Python file.
            
        Returns:
            A tuple containing:
                - The AST tree of the parsed file (or None if parsing failed)
                - The source code of the file (or None if parsing failed)
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                source_code = file.read()
            
            return ast.parse(source_code), source_code
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")
            return None, None
    
    def _extract_object(
        self, 
        ast_tree: ast.Module, 
        source_code: str, 
        object_name: str, 
        file_path: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extract a specific class or function from the AST.
        
        Traverses the AST to find the specified object and extracts its code,
        type, and docstring.
        
        Args:
            ast_tree: The AST of the module.
            source_code: Source code of the file.
            object_name: Name of the object to extract.
            file_path: Path to the file containing the object.
            
        Returns:
            A dictionary containing information about the extracted object with fields:
                - 'name': The name of the object
                - 'file': Path to the file containing the object
                - 'type': Type of the object ('class' or 'function')
                - 'code': The complete code of the object
                - 'docstring': The docstring of the object (or empty string)
            Returns None if the object is not found.
        """
        for node in ast.walk(ast_tree):
            if (isinstance(node, (ast.ClassDef, ast.FunctionDef)) and 
                node.name == object_name):
                # Get the code lines for this node
                if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
                    # Get line numbers (accounting for different Python versions)
                    start_line = node.lineno
                    # In some Python versions, end_lineno might not be available
                    end_line: Optional[int] = getattr(node, 'end_lineno', None)
                    
                    if end_line is None:
                        # If end_lineno is not available, estimate by counting lines in the source
                        lines = source_code.splitlines()
                        depth = 0
                        in_object = False
                        end_line = start_line
                        
                        for i, line in enumerate(lines[start_line-1:], start=start_line):
                            if not in_object and (line.strip().startswith(f"def {object_name}") or 
                                                 line.strip().startswith(f"class {object_name}")):
                                in_object = True
                            
                            if in_object:
                                # Count indentation to track when we exit the block
                                stripped = line.lstrip()
                                indent = len(line) - len(stripped)
                                
                                if stripped and indent == 0 and i > start_line:
                                    end_line = i - 1
                                    break
                                
                                end_line = i
                    
                    # Extract the code
                    lines = source_code.splitlines()
                    code_lines = lines[start_line-1:end_line]
                    code = "\n".join(code_lines)
                    
                    # Determine the type
                    obj_type = "class" if isinstance(node, ast.ClassDef) else "function"
                    
                    return {
                        "name": node.name,
                        "file": file_path,
                        "type": obj_type,
                        "code": code,
                        "docstring": ast.get_docstring(node) or ""
                    }
        
        return None
    
    def _resolve_imports(self, ast_tree: ast.Module, file_path: str, import_depth: int = 0, visited_in_call_stack: Optional[Set[str]] = None) -> None:
        """
        Resolve imports in the AST and follow references.
        
        Analyzes import statements in the code and processes the imported modules
        and objects to build a graph of code references.
        
        Args:
            ast_tree: The AST of the module.
            file_path: Path to the file containing the AST.
            import_depth: Current depth in the import resolution chain.
            visited_in_call_stack: Set of file paths that have been visited in the current call stack,
                                  used to detect import cycles.
        """
        # Initialize visited_in_call_stack if it's None
        if visited_in_call_stack is None:
            visited_in_call_stack = set()
            
        # Detect import cycles by checking if this file has been visited in this call stack
        if file_path in visited_in_call_stack:
            print(f"WARNING: Import cycle detected for {file_path}. Stopping import resolution.")
            return
            
        # Add this file to the call stack visited set
        visited_in_call_stack = visited_in_call_stack.union({file_path})
            
        # Guard against excessive recursion
        max_import_depth = 5  # Reduced limit for import depth
        if import_depth > max_import_depth:
            print(f"WARNING: Maximum import depth reached ({max_import_depth}) when processing {file_path}. Stopping import resolution.")
            return
            
        file_dir = os.path.dirname(file_path)
        
        # Get the project root directory (assuming it's a parent of file_path)
        project_root = file_dir
        while project_root and not os.path.exists(os.path.join(project_root, '.git')):
            parent = os.path.dirname(project_root)
            if parent == project_root:  # Reached root directory
                project_root = file_dir  # Fallback to file directory
                break
            project_root = parent
        
        # Track import statements
        for node in ast.walk(ast_tree):
            # Handle 'import module' statements
            if isinstance(node, ast.Import):
                for name in node.names:
                    module_name = name.name
                    self._process_imported_module(module_name, file_dir, import_depth + 1, visited_in_call_stack)
                    
                    # Try to find the module in the project directory
                    self._try_find_project_module(module_name, project_root, file_dir)
            
            # Handle 'from module import name' statements
            elif isinstance(node, ast.ImportFrom):
                if node.module:  # Skip relative imports without module
                    module_name = node.module
                    for name in node.names:
                        imported_name = name.name
                        self._process_imported_object(module_name, imported_name, file_dir, import_depth + 1, visited_in_call_stack)
                        
                    # Try to find the module in the project directory
                    self._try_find_project_module(module_name, project_root, file_dir)
    
    def _process_imported_module(self, module_name: str, file_dir: str, import_depth: int = 0, visited_in_call_stack: Optional[Set[str]] = None) -> None:
        """
        Process an imported module and extract its code.
        
        Attempts to locate the file for an imported module and extracts all
        classes and functions from it. Only processes files within the project directory.
        
        Args:
            module_name: Name of the imported module.
            file_dir: Directory of the file with the import.
            import_depth: Current depth in the import resolution chain.
            visited_in_call_stack: Set of file paths visited in the current call stack.
        """
        if visited_in_call_stack is None:
            visited_in_call_stack = set()
            
        # Try to find the module file
        try:
            # First try in the same directory
            local_module_path = os.path.join(file_dir, f"{module_name.split('.')[-1]}.py")
            
            if os.path.exists(local_module_path):
                module_path = local_module_path
            else:
                # Try to resolve using Python's import system
                spec = importlib.util.find_spec(module_name)
                if spec and spec.origin and spec.origin.endswith('.py'):
                    module_path = spec.origin
                else:
                    # Skip if we can't find the module
                    return
            
            # Skip if already visited - strict check to prevent recursion
            if module_path in self.visited_files:
                return
                
            # Skip system libraries and files outside the project
            if self._is_external_library(module_path):
                return
            
            # Parse the module
            ast_tree, source_code = self._parse_file(module_path)
            if ast_tree and source_code:
                # Add the module file to visited
                self.visited_files.add(module_path)
                
                # Extract each class and function from the module
                extracted_count = 0
                for node in ast.walk(ast_tree):
                    if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                        obj = self._extract_object(ast_tree, source_code, node.name, module_path)
                        if obj:
                            obj["reference_type"] = "import"
                            self.referenced_objects.append(obj)
                            extracted_count += 1
                
                # Recursively resolve imports in this module, but only if we're not exceeding depth limits
                if import_depth < 5:  # Hard limit on recursion depth
                    self._resolve_imports(ast_tree, module_path, import_depth, visited_in_call_stack)
        
        except Exception as e:
            print(f"Error processing import {module_name}: {e}")
    
    def _process_imported_object(self, module_name: str, object_name: str, file_dir: str, import_depth: int = 0) -> None:
        """
        Process a specific imported object and extract its code.
        
        Locates and extracts a specific object (class or function) from an imported module.
        Only processes files within the project directory.
        
        Args:
            module_name: Name of the module containing the object.
            object_name: Name of the imported object.
            file_dir: Directory of the file with the import.
            import_depth: Current depth in the import resolution chain.
        """
        print(f"DEBUG: Processing imported object: {module_name}.{object_name} from {file_dir}")
        # Similar to _process_imported_module but focusing on a specific object
        try:
            # First try in the same directory
            local_module_path = os.path.join(file_dir, f"{module_name.split('.')[-1]}.py")
            print(f"DEBUG: Checking local path: {local_module_path}")
            
            if os.path.exists(local_module_path):
                module_path = local_module_path
                print(f"DEBUG: Found module in local path: {module_path}")
            else:
                # Try to resolve using Python's import system
                print(f"DEBUG: Trying to resolve using importlib: {module_name}")
                spec = importlib.util.find_spec(module_name)
                if spec and spec.origin and spec.origin.endswith('.py'):
                    module_path = spec.origin
                    print(f"DEBUG: Found module using importlib: {module_path}")
                else:
                    # Skip if we can't find the module
                    print(f"DEBUG: Could not find module: {module_name}")
                    return
            
            # Skip already processed objects
            for obj in self.referenced_objects:
                if obj["name"] == object_name and obj["file"] == module_path:
                    print(f"DEBUG: Object already processed: {object_name} in {module_path}")
                    return
                    
            # Skip system libraries and files outside the project
            if self._is_external_library(module_path):
                print(f"DEBUG: Skipping external library: {module_path}")
                return
            
            # Parse the module
            print(f"DEBUG: Parsing module for object: {module_path}")
            ast_tree, source_code = self._parse_file(module_path)
            if ast_tree and source_code:
                # Add the module file to visited if not already
                if module_path not in self.visited_files:
                    self.visited_files.add(module_path)
                    
                    # Also process other imports in this module, but only if we're not exceeding depth limits
                    if import_depth < 5:  # Hard limit on recursion depth
                        self._resolve_imports(ast_tree, module_path, import_depth, visited_in_call_stack)
                
                # Extract the specific object
                print(f"DEBUG: Extracting object: {object_name} from {module_path}")
                obj = self._extract_object(ast_tree, source_code, object_name, module_path)
                if obj:
                    obj["reference_type"] = "import"
                    self.referenced_objects.append(obj)
                    print(f"DEBUG: Successfully extracted object: {object_name} from {module_path}")
                else:
                    print(f"DEBUG: Failed to extract object: {object_name} from {module_path}")
            else:
                print(f"DEBUG: Failed to parse module: {module_path}")
        
        except Exception as e:
            print(f"Error processing imported object {module_name}.{object_name}: {e}")
    
    def _count_tokens(self, code_string: str) -> int:
        """
        Count tokens in a code string.
        
        Provides an approximate token count by splitting on whitespace and punctuation.
        This is a simple approximation - for more accurate token counting, consider
        using the 'tokenize' module or a dedicated tokenizer for the target model.
        
        Args:
            code_string: The code string to count tokens for.
            
        Returns:
            Approximate token count.
        """
        # Simple approximation - split on whitespace and common punctuation
        # This is a rough estimate; a proper tokenizer would be more accurate
        token_pattern = r'[\s\(\)\[\]\{\}:;,\.\"\']+'
        tokens = re.split(token_pattern, code_string)
        return len([t for t in tokens if t])  # Count non-empty tokens
    
    def _prioritize_code(self, result_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prioritize code to fit within the token limit.
        
        When the total extracted code exceeds the token limit, this method
        intelligently selects which parts to keep, prioritizing:
        1. The main object (always kept)
        2. Classes over functions
        3. Shorter code over longer code
        
        For objects that can't be included in full, it preserves their signatures
        and docstrings while truncating the implementation.
        
        Args:
            result_dict: The result dictionary with code objects.
            
        Returns:
            Updated result dictionary with prioritized code.
        """
        # Always include the main object
        main_object = result_dict["main_object"]
        main_tokens = self._count_tokens(main_object["code"])
        
        # Sort referenced objects by importance
        # Prioritize classes over functions, shorter code over longer code
        def priority_key(obj: Dict[str, Any]) -> Tuple[int, int]:
            # Lower score means higher priority
            type_score = 0 if obj["type"] == "class" else 1
            size_score = self._count_tokens(obj["code"])
            return (type_score, size_score)
        
        sorted_refs = sorted(result_dict["referenced_objects"], key=priority_key)
        
        # Keep adding references until we hit the token limit
        kept_refs: List[Dict[str, Any]] = []
        current_tokens = main_tokens
        
        for ref in sorted_refs:
            ref_tokens = self._count_tokens(ref["code"])
            if current_tokens + ref_tokens <= self.token_limit:
                kept_refs.append(ref)
                current_tokens += ref_tokens
            else:
                # If the reference is too large, try to include just the signature
                # For classes, include class definition and docstring
                # For functions, include function signature and docstring
                if ref["type"] == "class":
                    # Extract class definition line and docstring
                    lines = ref["code"].splitlines()
                    class_def = next((l for l in lines if l.strip().startswith("class ")), "")
                    truncated_code = f"{class_def}\n    \"\"\"" + ref["docstring"] + "\"\"\"\n    # ... code truncated due to token limit"
                elif ref["type"] == "function":
                    # Extract function signature and docstring
                    lines = ref["code"].splitlines()
                    func_def = next((l for l in lines if l.strip().startswith("def ")), "")
                    truncated_code = f"{func_def}\n    \"\"\"" + ref["docstring"] + "\"\"\"\n    # ... code truncated due to token limit"
                else:
                    truncated_code = f"# {ref['name']} (truncated due to token limit)"
                
                truncated_ref = ref.copy()
                truncated_ref["code"] = truncated_code
                truncated_ref["truncated"] = True
                
                truncated_tokens = self._count_tokens(truncated_code)
                if current_tokens + truncated_tokens <= self.token_limit:
                    kept_refs.append(truncated_ref)
                    current_tokens += truncated_tokens
        
        # Update the result
        result_dict["referenced_objects"] = kept_refs
        result_dict["token_count"] = current_tokens
        result_dict["truncated"] = len(kept_refs) < len(sorted_refs)
        
        return result_dict

    def _try_find_project_module(self, module_name: str, project_root: str, file_dir: str, import_depth: int = 0, visited_in_call_stack: Optional[Set[str]] = None) -> None:
        """
        Try to find a module within the project directory structure.
        
        This method attempts to locate a Python module within the project by searching
        for files with matching names, regardless of their location in the project hierarchy.
        
        Args:
            module_name: Name of the module to find.
            project_root: Root directory of the project.
            file_dir: Directory of the file with the import.
        """
        if visited_in_call_stack is None:
            visited_in_call_stack = set()
        
        # Don't process if we're too deep to avoid excessive recursion
        if import_depth > 5:
            return
            
        # Extract the base module name (without submodules)
        base_module = module_name.split('.')[0]
        
        # Look for Python files with the module name, but limit search to avoid excessive traversal
        found_files = []
        for root, _, files in os.walk(project_root):
            # Skip external libraries and cache directories
            if self._is_external_library(root) or any(d in root for d in ['__pycache__', '.git']):
                continue
                
            # Limit the number of files we process to avoid excessive recursion
            if len(found_files) > 10:  # Only process a reasonable number of files
                break
                
            for file in files:
                if file == f"{base_module}.py":
                    module_path = os.path.join(root, file)
                    
                    # Skip if already visited
                    if module_path in self.visited_files:
                        print(f"DEBUG: Project module already visited: {module_path}")
                        continue
                        
                    print(f"DEBUG: Found project module: {module_path}")
                    
                    # Parse the module
                    ast_tree, source_code = self._parse_file(module_path)
                    if ast_tree and source_code:
                        # Add the module file to visited
                        self.visited_files.add(module_path)
                        print(f"DEBUG: Added project module to visited files: {module_path}")
                        
                        # Extract each class and function from the module
                        extracted_count = 0
                        for node in ast.walk(ast_tree):
                            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                                obj = self._extract_object(ast_tree, source_code, node.name, module_path)
                                if obj:
                                    obj["reference_type"] = "project_import"
                                    self.referenced_objects.append(obj)
                                    extracted_count += 1
                        
                        print(f"DEBUG: Extracted {extracted_count} objects from project module: {module_path}")
                        
                        # Recursively resolve imports in this module with depth tracking
                        self._resolve_imports(ast_tree, module_path, 0, set([module_path]))
                        
                        # We found the module, no need to continue searching
                        return
    
    def _is_external_library(self, file_path: str) -> bool:
        """
        Determines if a file path belongs to an external library or is outside the project.
        
        Args:
            file_path: The path to check
            
        Returns:
            True if the file is from an external library or outside the project, False otherwise
        """
        # Normalize the path
        file_path = os.path.abspath(os.path.normpath(file_path))
        
        # Check for common external library indicators in the path
        external_indicators = {
            '/usr/lib/', '/usr/local/lib/', 'site-packages/', 'dist-packages/',
            '.venv/', 'venv/', 'env/', '/lib/python', '/Lib/python'
        }
        
        # Check if the path contains any of the external indicators
        for indicator in external_indicators:
            if indicator in file_path:
                return True
                
        return False
        
    def find_all_python_files(self, root_path: str) -> List[str]:
        """
        Finds all Python files in the specified directory, strictly excluding:
        - External libraries (like system libraries or those in .venv)
        - Cache directories
        - Any files outside the project root
        
        Args:
            root_path: The root directory of the project
            
        Returns:
            List of absolute paths to Python files within the project
        """
        python_files = []
        
        # Convert root_path to absolute and normalized path
        root_path = os.path.abspath(os.path.normpath(root_path))
        print(f"DEBUG: Finding Python files in project root: {root_path}")
        
        # Directories to exclude (common patterns for virtual environments, caches, etc.)
        excluded_dirs = {
            '__pycache__', 'venv', 'env', '.venv', '.env', 'site-packages',
            'dist-packages', 'lib', 'Lib', 'node_modules', 'build', 'dist',
            '.git', '.github', '.pytest_cache', '.mypy_cache', '.tox', 'egg-info'
        }
        
        # Path segments that indicate external libraries
        excluded_path_segments = {
            'site-packages', 'dist-packages', 'lib/python', 'Lib/python'
        }
        
        for root, dirs, files in os.walk(root_path):
            # Filter out excluded directories
            original_dirs = set(dirs)
            dirs[:] = [d for d in dirs if d not in excluded_dirs and not d.startswith('.')]
            if len(original_dirs) != len(dirs):
                print(f"DEBUG: Excluded directories in {root}: {original_dirs - set(dirs)}")
            
            # Skip this directory if it contains excluded path segments
            if any(segment in root for segment in excluded_path_segments):
                print(f"DEBUG: Skipping directory with excluded path segment: {root}")
                continue
                
            # Ensure we're still within the project root (protects against symlinks)
            if not os.path.abspath(root).startswith(root_path):
                print(f"DEBUG: Skipping directory outside project root: {root}")
                continue
                
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    
                    # Final check to ensure the file is within the project
                    if os.path.abspath(file_path).startswith(root_path):
                        # Check if it's an external library
                        if self._is_external_library(file_path):
                            print(f"DEBUG: Skipping external library file: {file_path}")
                            continue
                            
                        python_files.append(file_path)
                        print(f"DEBUG: Found Python file: {file_path}")
        
        print(f"DEBUG: Found {len(python_files)} Python files in total")
        return python_files
