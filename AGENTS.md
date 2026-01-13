# Repository Guidelines

## Project Structure & Module Organization

The project follows a standard Python package structure with Poetry dependency management:
- `src/workshop_mcp/` - Main package containing MCP server and keyword search tool
- `agents/` - Agent configuration files (TOML format)
- `tests/` - Comprehensive test suite with async testing support
- `00-*.md` - Step-by-step workshop guides for building the MCP server
- `pyproject.toml` - Poetry configuration with dependencies and build settings
- `verification.py` - Environment verification and health checks
- `mcp.json` - MCP server launch configuration

## Build, Test, and Development Commands

```bash
# Install dependencies
poetry install

# Verify setup
poetry run python verification.py

# Start the MCP server
poetry run workshop-mcp-server

# Run all tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=workshop_mcp

# Format code
poetry run black src/ tests/

# Sort imports
poetry run isort src/ tests/

# Type checking
poetry run mypy src/
```

## Coding Style & Naming Conventions

- **Indentation**: 4 spaces (configured in pyproject.toml)
- **File naming**: Snake_case for Python files, lowercase for directories
- **Function/variable naming**: Snake_case following PEP 8 conventions
- **Class naming**: PascalCase (e.g., `KeywordSearchTool`, `WorkshopMCPServer`)
- **Linting**: Black formatter with 88-character line length, isort for imports

## Testing Guidelines

- **Framework**: pytest with asyncio support
- **Test files**: Located in `tests/` directory, prefixed with `test_`
- **Running tests**: `poetry run pytest` for all tests, `poetry run pytest -v` for verbose output
- **Coverage**: Use `--cov=workshop_mcp` flag for coverage reporting
- **Async testing**: Uses `@pytest.mark.asyncio` decorator for async test functions

## Commit & Pull Request Guidelines

- **Commit format**: Conventional commits with descriptive messages
- **Recent examples**: "fix: MCP synchronous call entrypoint", "add agent.toml file and QC instructions"
- **PR process**: Standard GitHub workflow with comprehensive testing
- **Branch naming**: Feature branches with descriptive names

---

# Repository Tour

## 🎯 What This Repository Does

Python MCP Agent Workshop is a comprehensive educational project demonstrating how to build AI agents using the Model Context Protocol (MCP) in Python. It provides a complete MCP server implementation with keyword search functionality and intelligent agent configuration for code analysis.

**Key responsibilities:**
- Implement MCP protocol server with JSON-RPC communication
- Provide asynchronous keyword search across directory trees
- Enable AI agent integration for intelligent code analysis

---

## 🏗️ Architecture Overview

### System Context
```
[AI Agent] → [MCP Server] → [Keyword Search Tool] → [File System]
     ↓            ↓               ↓                    ↓
[Analysis]   [JSON-RPC]    [Async Processing]   [Text Files]
[Results]    [Protocol]    [Statistics]        [Multiple Formats]
```

### Key Components
- **MCP Server** (`src/workshop_mcp/server.py`) - Implements MCP protocol with JSON-RPC communication, exposes keyword search tool to AI agents
- **Keyword Search Tool** (`src/workshop_mcp/keyword_search.py`) - Asynchronous file system search with multi-format support and statistical analysis
- **AI Agent Configuration** (`agents/keyword_analysis.toml`) - Intelligent keyword analysis agent with pattern recognition and refactoring recommendations

### Data Flow
1. **Agent Request**: AI agent sends keyword search request via MCP protocol
2. **Server Processing**: MCP server validates request and delegates to keyword search tool
3. **File System Search**: Tool recursively searches directories for keyword occurrences
4. **Statistical Analysis**: Results are aggregated with summary statistics and file distribution
5. **Response Delivery**: Structured JSON response returned to agent with actionable insights

---

## 📁 Project Structure [Partial Directory Tree]

```
python-mcp-agent-workshop/
├── src/workshop_mcp/           # Main package implementation
│   ├── __init__.py             # Package initialization
│   ├── server.py               # MCP server with JSON-RPC protocol
│   └── keyword_search.py       # Async keyword search tool
├── 00-setup.md                 # Workshop setup and environment verification
├── 00-introduction.md          # Workshop introduction
├── 01-transport.md             # Transport fundamentals
├── 02-jsonrpc.md               # JSON-RPC validation and routing
├── 03-initialize.md            # Capability handshake walkthrough
├── 04-tools.md                 # Tool advertising and invocation
├── agents/                     # Agent configurations
│   └── keyword_analysis.toml   # Intelligent analysis agent
├── tests/                      # Comprehensive test suite
│   ├── __init__.py             # Test package initialization
│   └── test_keyword_search.py  # Async testing with fixtures
│   └── test_mcp_server_protocol.py # MCP server protocol validation
├── pyproject.toml              # Poetry configuration and dependencies
├── agent.toml                  # Main agent configuration
├── demo.py                     # Project demonstration script
├── verification.py             # Setup verification and health checks
├── mcp.json                    # MCP server launch configuration
└── README.md                   # Comprehensive documentation
```

### Key Files to Know

| File | Purpose | When You'd Touch It |
|------|---------|---------------------|
| `src/workshop_mcp/server.py` | MCP protocol implementation | Adding new tools or modifying protocol handling |
| `src/workshop_mcp/keyword_search.py` | Core search functionality | Enhancing search algorithms or file type support |
| `agents/keyword_analysis.toml` | Agent behavior configuration | Customizing analysis instructions or output format |
| `mcp.json` | MCP launch config | Adjusting server startup command |
| `pyproject.toml` | Dependencies and build config | Adding libraries or changing project metadata |
| `tests/test_keyword_search.py` | Comprehensive test suite | Adding tests for new features or edge cases |
| `tests/test_mcp_server_protocol.py` | Server protocol tests | Extending JSON-RPC/server behavior checks |

---

## 🔧 Technology Stack

### Core Technologies
- **Language:** Python (3.11+) - Chosen for async/await support and rich ecosystem
- **Framework:** MCP (Model Context Protocol) - Enables standardized AI agent communication
- **Async Library:** asyncio with aiofiles - Provides non-blocking file system operations
- **Dependency Management:** Poetry - Modern Python packaging and dependency resolution

### Key Libraries
- **mcp** (^1.0.0) - Model Context Protocol implementation for agent communication
- **aiofiles** (^23.2.0) - Asynchronous file operations for performance
- **pytest** (^7.4.0) - Testing framework with async support

### Development Tools
- **pytest-asyncio** - Async test execution and fixtures
- **black** - Code formatting with 88-character line length
- **isort** - Import sorting and organization
- **mypy** - Static type checking for code quality

---

## 🌐 External Dependencies

### Required Services
- **File System** - Local directory access for keyword searching, critical for core functionality
- **Python Runtime** - 3.11+ required for modern async features and type hints

### Optional Integrations
- **Qodo Command** - AI agent execution platform for running keyword analysis
- **Git** - Version control for development workflow and commit tracking

---

## 🔄 Common Workflows

### Keyword Search Execution
1. **Agent Request**: AI agent calls keyword_search tool via MCP protocol
2. **Validation**: Server validates keyword and root paths parameters
3. **Async Search**: Tool recursively searches directories with concurrent file processing
4. **Statistical Analysis**: Results aggregated with occurrence counts and file distribution
5. **Response**: Structured JSON returned with actionable insights

**Code path:** `agents/keyword_analysis.toml` → `server.py` → `keyword_search.py` → `file system`

### Development Workflow
1. **Setup**: Install dependencies with `poetry install`
2. **Development**: Make changes to source code in `src/workshop_mcp/`
3. **Testing**: Run `poetry run pytest` for comprehensive test validation
4. **Quality**: Use `poetry run black` and `poetry run mypy` for code quality
5. **Integration**: Test with `poetry run workshop-mcp-server`

**Code path:** `development` → `testing` → `quality checks` → `integration testing`

---

## 📈 Performance & Scale

### Performance Considerations
- **Async Processing:** Concurrent file operations with configurable batch sizes (50 files per batch)
- **Memory Management:** Streaming file reads to handle large codebases efficiently
- **File Type Filtering:** Supports 20+ text file extensions (.py, .java, .js, .ts, .html, .css, .json, .xml, .md, .txt, .yml, .yaml, .c, .cpp, .h, .hpp, .go, .rs, .php, .rb, .swift, .kt, .scala)

### Monitoring
- **Metrics:** File count, occurrence statistics, processing time, error rates
- **Logging:** Structured logging with configurable levels for debugging and monitoring

---

## 🚨 Things to Be Careful About

### 🔒 Security Considerations
- **File Access:** Tool respects file system permissions and handles permission errors gracefully
- **Path Validation:** Root paths are validated and resolved to prevent directory traversal
- **Error Handling:** Comprehensive exception handling prevents information leakage

### ⚠️ Development Considerations
- **Async Context:** All file operations must use async/await patterns for proper concurrency
- **Error Propagation:** MCP server returns structured error responses for debugging
- **Resource Management:** File handles are properly closed using async context managers
- **Testing:** Async tests require `@pytest.mark.asyncio` decorator and proper fixture management

*Updated at: 2026-01-13 UTC*
