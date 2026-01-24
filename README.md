# Python MCP Agent Workshop

A workshop for building AI agents using the Model Context Protocol (MCP) in Python.
This project walks through implementing MCP server fundamentals (JSON-RPC framing,
tool discovery, and tool execution) and ships two fully working tools:

1. **Performance Profiler** - Semantic Python code analysis using Astroid AST parsing to detect performance anti-patterns (N+1 queries, blocking I/O in async, inefficient loops, memory issues)
2. **Keyword Search** - Async file system search with statistical analysis

## Link to Presentation Slides

[Presentation Slides](https://docs.google.com/presentation/d/1YBX8Vsso5QMDNduMP6S4g6pYUjCSisZCq69wvY4IL1c/edit?slide=id.g371d7545128_0_130#slide=id.g371d7545128_0_130)


## Features

### Performance Profiler
The performance profiler uses Astroid for semantic AST analysis, detecting:

- **N+1 Query Detection** - Identifies Django and SQLAlchemy ORM queries inside loops
- **Blocking I/O in Async** - Finds synchronous operations (open, time.sleep, requests) in async functions
- **Inefficient Loop Patterns** - Detects string concatenation in loops, deep nesting
- **Memory Inefficiency Detection** - Flags loading entire files into memory (read(), json.load, pickle.load)

### Keyword Search
- Asynchronous file system search across multiple directories
- Multi-format text file support
- Statistical analysis and reporting

### Why Astroid over Standard AST?

Unlike general linters (Pylint, Flake8), the performance profiler uses **Astroid** for semantic analysis:

- **Type Inference**: Understands what types variables hold, not just their names
- **Call Resolution**: Knows which function is actually being called (e.g., Django ORM vs. regular method)
- **Cross-module Analysis**: Can resolve imports and understand relationships
- **Pattern Context**: Detects patterns like "ORM query inside a loop" that require understanding code structure

## Quick Start

```bash
# Clone and install
git clone <repository-url>
cd python-mcp-agent-workshop
poetry install

# Verify setup
python verification.py

# Start the MCP server
poetry run workshop-mcp-server

# Run tests (102 tests)
poetry run pytest

# Use the performance profiler agent (requires Qodo)
qodo performance_analysis --set file_path="path/to/code.py"

# Use the keyword search agent (requires Qodo)
qodo keyword_analysis --set keyword="{KEYWORD_HERE}"
```

### Testing the Performance Profiler via MCP

```bash
# Start the server and send a JSON-RPC request
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"performance_check","arguments":{"file_path":"src/workshop_mcp/server.py"}}}' | poetry run python -m workshop_mcp.server
```

## Learning Path (From-Scratch MCP Server)

Start with the protocol fundamentals and build up the server step by step:

1. [00 - Introduction](00-introduction.md)
2. [01 - Transport: Framing MCP Messages Over stdio](01-transport.md)
3. [02 - JSON-RPC 2.0: Validating and Routing Requests](02-jsonrpc.md)
4. [03 - Initialize: Capability Handshake](03-initialize.md)
5. [04 - Tools: Advertising and Invoking Capabilities](04-tools.md)

## Prerequisites

Before starting the workshop, ensure you have the following installed:

### Required Software

1. **Python 3.11+**
   - Download from [python.org](https://www.python.org/downloads/)
   - Verify: `python --version`

2. **Poetry** (Python dependency management)
   - Install: `curl -sSL https://install.python-poetry.org | python3 -`
   - Or via pip: `pip install poetry`
   - Verify: `poetry --version`

### Key Dependencies

The project uses these core libraries (installed via `poetry install`):

- **Astroid** - Advanced AST analysis for semantic Python parsing (powers performance profiler)
- **aiofiles** - Async file I/O operations

### Optional Tools

- **Git** for version control
- **VS Code** or your preferred IDE
- **Docker** (for containerized deployment)
- **Qodo Command** (optional, for agent execution)
  - Install: `npm install -g @qodo/command`
  - Log in: `qodo login`
  - Verify: `qodo --version`
  - Docs: [docs.qodo.ai/qodo-documentation/qodo-command](https://docs.qodo.ai/qodo-documentation/qodo-command)

## Architecture Overview

This workshop demonstrates a complete MCP ecosystem implemented from scratch:

```
┌─────────────────────────────────────────────────────────────────────┐
│                           AI Agents                                  │
│  ┌─────────────────────┐       ┌─────────────────────┐              │
│  │ performance_profiler│       │  keyword_analysis   │              │
│  │       .toml         │       │       .toml         │              │
│  └──────────┬──────────┘       └──────────┬──────────┘              │
└─────────────┼─────────────────────────────┼─────────────────────────┘
              │                             │
              ▼                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        MCP Server (server.py)                        │
│                     JSON-RPC 2.0 over stdio                          │
├─────────────────────────────────────────────────────────────────────┤
│  Tools:                                                              │
│  ┌─────────────────────┐       ┌─────────────────────┐              │
│  │  performance_check  │       │   keyword_search    │              │
│  └──────────┬──────────┘       └──────────┬──────────┘              │
└─────────────┼─────────────────────────────┼─────────────────────────┘
              │                             │
              ▼                             ▼
┌─────────────────────────┐    ┌─────────────────────────┐
│  Performance Profiler   │    │    Keyword Search       │
│  ├─ AST Analyzer        │    │    (Async File I/O)     │
│  │  (Astroid-powered)   │    │                         │
│  ├─ Performance Checker │    │                         │
│  └─ Pattern Detection   │    │                         │
└─────────────────────────┘    └─────────────────────────┘
```

### Components

1. **MCP Server** (`src/workshop_mcp/server.py`)
   - Implements MCP protocol over stdio (Content-Length framing)
   - Exposes `performance_check` and `keyword_search` tools
   - Handles JSON-RPC request routing and error handling

2. **Performance Profiler** (`src/workshop_mcp/performance_profiler/`)
   - `ast_analyzer.py` - Astroid-based semantic AST analysis
   - `performance_checker.py` - Issue detection and reporting
   - `patterns.py` - Anti-pattern definitions (ORM queries, blocking I/O, etc.)

3. **Keyword Search Tool** (`src/workshop_mcp/keyword_search.py`)
   - Asynchronous file system search
   - Multi-format text file support
   - Statistical analysis and reporting

4. **AI Agents** (`agents/`)
   - `performance_profiler.toml` - Performance analysis agent (Gemini 2.5 Pro)
   - `keyword_analysis.toml` - Keyword search agent

## Usage Examples

### Performance Profiler (Programmatic)

```python
from workshop_mcp.performance_profiler import PerformanceChecker

# Analyze a file
checker = PerformanceChecker(file_path="path/to/code.py")
issues = checker.check_all()

for issue in issues:
    print(f"[{issue.severity.value}] {issue.category.value}")
    print(f"  Line {issue.line_number}: {issue.description}")
    print(f"  Suggestion: {issue.suggestion}")

# Get summary
summary = checker.get_summary()
print(f"Total issues: {summary['total_issues']}")
print(f"Critical: {summary['by_severity']['critical']}")

# Analyze source code directly
checker = PerformanceChecker(source_code="""
async def fetch_users():
    with open('data.json') as f:  # Blocking I/O in async!
        return json.load(f)
""")
issues = checker.check_all()
```

### Basic Keyword Search

```python
from workshop_mcp.keyword_search import KeywordSearchTool

tool = KeywordSearchTool()
result = await tool.execute("async", ["/path/to/codebase"])

print(f"Found {result['summary']['total_occurrences']} occurrences")
print(f"Most frequent file: {result['summary']['most_frequent_file']}")
```

### Running the MCP Server

```bash
# Start server (listens on stdin/stdout)
poetry run workshop-mcp-server

# Or use the script entry point
poetry run python -m workshop_mcp.server
```

### Agent Analysis

```bash
# Run performance analysis agent
qodo performance_analysis --set file_path="src/workshop_mcp/server.py"

# Run keyword analysis agent
qodo keyword_analysis --set keyword="{KEYWORD_HERE}"
```

### Understanding Performance Profiler Output

The performance profiler returns issues with severity levels:

| Severity | Description |
|----------|-------------|
| CRITICAL | Blocking I/O in async functions - blocks entire event loop |
| HIGH | N+1 queries, memory inefficiencies - significant performance impact |
| MEDIUM | Inefficient loops, string concatenation - moderate impact |
| LOW | Minor optimizations, style suggestions |

Example output structure:
```json
{
  "summary": {
    "total_issues": 3,
    "by_severity": {"critical": 1, "high": 1, "medium": 1, "low": 0},
    "by_category": {"blocking_io_in_async": 1, "n_plus_one_query": 1, "inefficient_loop": 1}
  },
  "issues": [
    {
      "category": "blocking_io_in_async",
      "severity": "critical",
      "line_number": 15,
      "description": "Blocking I/O operation 'open' in async function",
      "suggestion": "Use aiofiles.open for async file operations",
      "function_name": "fetch_data"
    }
  ]
}
```

## Development Setup

### Environment Setup

1. **Clone and Install**
   ```bash
   git clone <repository-url>
   cd python-mcp-agent-workshop
   poetry install
   ```

2. **Verify Installation**
   ```bash
   python verification.py
   ```

3. **Development Dependencies**
   ```bash
   poetry install --with dev
   ```

### Code Quality Tools

```bash
# Format code
poetry run black src/ tests/

# Sort imports
poetry run isort src/ tests/

# Type checking
poetry run mypy src/

```

### Running in Development Mode

```bash
# Install in editable mode
poetry install

# Run server with debug logging
PYTHONPATH=src poetry run python -m workshop_mcp.server

# Run tests with verbose output
poetry run pytest -v -s
```

## Project Structure

```
python-mcp-agent-workshop/
├── pyproject.toml              # Poetry configuration
├── README.md                   # This file
├── verification.py             # Setup verification script
├── agent.toml                  # Top-level agent configuration
├── mcp.json                    # MCP configuration metadata
│
├── src/workshop_mcp/           # Main package
│   ├── __init__.py             # Package initialization
│   ├── server.py               # MCP server implementation
│   ├── keyword_search.py       # Keyword search tool
│   └── performance_profiler/   # Performance analysis module
│       ├── __init__.py         # Module exports
│       ├── ast_analyzer.py     # Astroid-based AST analysis
│       ├── patterns.py         # Anti-pattern definitions
│       └── performance_checker.py  # Issue detection
│
├── agents/                     # Agent configurations
│   ├── keyword_analysis.toml   # Keyword search agent
│   └── performance_profiler.toml   # Performance analysis agent
│
├── tests/                      # Test suite (102 tests)
│   ├── test_keyword_search.py      # Keyword search tests (15)
│   ├── test_ast_analyzer.py        # AST analyzer tests (41)
│   ├── test_performance_checker.py # Performance checker tests (31)
│   ├── test_mcp_server_integration.py  # MCP integration tests (10)
│   ├── test_mcp_server_protocol.py # Protocol tests (5)
│   ├── test_agent_config.py        # Agent config validation
│   └── test_e2e_workflow.py        # End-to-end workflow tests
│
└── spec/                       # Project specifications
    ├── documentation-plan.md
    ├── e2e-testing-plan.md
    └── project-completion-plan.md
```

## Testing Strategy

The project includes **102 tests** covering:

### Test Suites
- **AST Analyzer** (41 tests): Function extraction, loop detection, import analysis, call tracking
- **Performance Checker** (31 tests): N+1 queries, blocking I/O, inefficient loops, memory issues
- **Keyword Search** (15 tests): File search, edge cases, concurrency
- **MCP Integration** (10 tests): Tool registration, JSON-RPC handling, error responses
- **Protocol Tests** (5 tests): Message framing, content-length parsing
- **E2E Workflow**: Complete agent workflow validation
- **Agent Config**: TOML validation, output schema verification

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with verbose output
poetry run pytest -v

# Run specific test file
poetry run pytest tests/test_performance_checker.py -v

# Run with coverage
poetry run pytest --cov=workshop_mcp
```

## Troubleshooting

### Common Issues

1. **Python Version Error**
   ```
   Error: Python 3.11+ required
   Solution: Upgrade Python or use pyenv
   ```

2. **Poetry Not Found**
   ```
   Error: poetry: command not found
   Solution: Install Poetry from python-poetry.org
   ```

3. **Permission Denied**
   ```
   Error: Permission denied accessing files
   Solution: Check file permissions and user access
   ```

4. **Agent Configuration Error**
   ```
   Error: Invalid TOML configuration
   Solution: Validate TOML syntax in agents/keyword_analysis.toml
   ```

### Debug Mode

Enable detailed logging:

```bash
export LOG_LEVEL=DEBUG
poetry run workshop-mcp-server
```

### Verification Script

Run the comprehensive verification (use `python3.12` if it is installed; otherwise
use your default `python` that meets the 3.11+ requirement):

```bash
python3.12 verification.py
# or
python verification.py
```

This checks:
- Python version compatibility
- Poetry installation and configuration
- Project structure completeness
- Dependency installation success
- MCP server functionality
- Unit test execution
- Agent configuration validity


## Learning Resources

### MCP Protocol
- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [MCP Examples](https://github.com/modelcontextprotocol/servers)

### Python Async Programming
- [AsyncIO Documentation](https://docs.python.org/3/library/asyncio.html)
- [Real Python Async Guide](https://realpython.com/async-io-python/)

### Agent Development
- [Qodo Documentation](https://docs.qodo.ai/)
- [Agent Configuration Guide](https://docs.qodo.ai/qodo-documentation/qodo-command/features/creating-and-managing-agents)

## Contributing

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Make changes and test**: `poetry run pytest`
4. **Commit changes**: `git commit -m 'Add amazing feature'`
5. **Push to branch**: `git push origin feature/amazing-feature`
6. **Open Pull Request**

### Development Guidelines

- Follow PEP 8 style guidelines
- Add type hints to all functions
- Write comprehensive docstrings
- **Test-driven development**: Write tests before implementing features
- Include unit tests for new features (maintain 102+ test count)
- Update documentation as needed

### Adding New Performance Checks

1. Define the pattern in `src/workshop_mcp/performance_profiler/patterns.py`
2. Add detection logic in `performance_checker.py`
3. Write tests in `tests/test_performance_checker.py`
4. Update documentation

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- **Model Context Protocol** team for the excellent protocol specification
- **Poetry** team for dependency management
- **Qodo** team for agent development platform
- **Python** community for async/await support

## Support

- **Issues**: Use your fork's issue tracker
- **Discussions**: Use your fork's discussions board

---

**Happy coding!**

*This workshop provides a solid foundation for building production-ready MCP agents in Python. Extend and customize it for your specific use cases.*
