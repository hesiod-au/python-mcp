# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- The `get_python_code` tool now automatically includes README.md files (or variants) as additional files in the response, providing better project context and documentation.

### Fixed
- Fixed token counting in `agent.py` by consistently using `_count_tokens` method from `CodeGrapher` class.
- Enhanced test suite to fail when errors occur during code processing, improving error detection.

### Changed
- Renamed `agent_tools.py` to `code_grapher.py` for better code organization and clarity.
- Renamed the MCP tool from `get_code` to `get_python_code` for improved naming consistency.
- Improved file prioritization: when adding related files to the response, the system now:
  - Begins by adding the target file and README (if present) token size to the count
  - Proceeds with files imported by the target, from smallest to largest
  - Continues with files that import the target, from smallest to largest
  - Respects the overall token limit throughout the process

## [1.0.0] - Initial Release

### Added
- Initial implementation of the Python Code Explorer MCP server.
- Code relationship discovery for Python files.
- Smart code extraction with token limits.
- Directory context inclusion.
- LLM-friendly code formatting.
- MCP Protocol support.
