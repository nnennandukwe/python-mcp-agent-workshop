# Python MCP Agent Workshop

A workshop for building AI agents using the Model Context Protocol (MCP) in Python.
This project walks through implementing MCP server fundamentals (JSON-RPC framing,
tool discovery, and tool execution) and ships a fully working keyword search tool
backed by async file I/O.

## Link to Presentation Slides

[Presentation Slides](https://docs.google.com/presentation/d/1YBX8Vsso5QMDNduMP6S4g6pYUjCSisZCq69wvY4IL1c/edit?slide=id.g371d7545128_0_130#slide=id.g371d7545128_0_130)


## 🚀 Quick Start


```bash
# Install the repository
git clone <repository-url>
cd python-mcp-agent-workshop

# Install dependencies
poetry install

# Verify setup
python verification.py

# Start the MCP server
poetry run workshop-mcp-server

# Run tests
poetry run pytest

# Use the agent (optional, requires Qodo)
qodo keyword_analysis --set keyword="{KEYWORD_HERE}"
```

## 🧭 Learning Path (From-Scratch MCP Server)

Start with the protocol fundamentals and build up the server step by step:

1. [00 - Introduction](00-introduction.md)
2. [01 - Transport: Framing MCP Messages Over stdio](01-transport.md)
3. [02 - JSON-RPC 2.0: Validating and Routing Requests](02-jsonrpc.md)
4. [03 - Initialize: Capability Handshake](03-initialize.md)
5. [04 - Tools: Advertising and Invoking Capabilities](04-tools.md)

## 📋 Prerequisites

Before starting the workshop, ensure you have the following installed:

### Required Software

1. **Python 3.11+**
   - Download from [python.org](https://www.python.org/downloads/)
   - Verify: `python --version`

2. **Poetry** (Python dependency management)
   - Install: `curl -sSL https://install.python-poetry.org | python3 -`
   - Or via pip: `pip install poetry`
   - Verify: `poetry --version`

### Optional Tools

- **Git** for version control
- **VS Code** or your preferred IDE
- **Docker** (for containerized deployment)
- **Qodo Command** (optional, for agent execution)
  - Install: `npm install -g @qodo/command`
  - Log in: `qodo login`
  - Verify: `qodo --version`
  - Docs: [docs.qodo.ai/qodo-documentation/qodo-command](https://docs.qodo.ai/qodo-documentation/qodo-command)

## 🏗️ Architecture Overview

This workshop demonstrates a complete MCP ecosystem implemented from scratch:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   AI Agent      │───▶│   MCP Server    │───▶│  Keyword Tool   │
│(keyword_analysis│    │   (server.py)   │    │(keyword_search) │
│     .toml)      │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       ▼
         │                       │              ┌─────────────────┐
         │                       │              │   File System   │
         │                       │              │   (Search)      │
         │                       │              └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│   Analysis      │    │   JSON-RPC      │
│   Results       │    │   Protocol      │
└─────────────────┘    └─────────────────┘
```

### Components

1. **MCP Server** (`src/workshop_mcp/server.py`)
   - Implements MCP protocol over stdio (Content-Length framing)
   - Exposes keyword search tool
   - Handles JSON-RPC request routing

2. **Keyword Search Tool** (`src/workshop_mcp/keyword_search.py`)
   - Asynchronous file system search
   - Multi-format text file support
   - Statistical analysis and reporting

3. **AI Agent** (`agents/keyword_analysis.toml`)
   - Keyword analysis prompt and configuration for Qodo Command

## 🛠️ Usage Examples

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
# Run keyword analysis agent
qodo keyword_analysis --set keyword="{KEYWORD_HERE}"
```

### Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=workshop_mcp

# Run specific test file
poetry run pytest tests/test_keyword_search.py -v

# Run with detailed output
poetry run pytest -v --tb=long
```

## 🔧 Development Setup

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

## 📁 Project Structure

```
python-mcp-agent-workshop/
├── pyproject.toml              # Poetry configuration
├── README.md                   # This file
├── verification.py             # Setup verification script
├── agent.toml                  # Top-level agent configuration
├── mcp.json                    # MCP configuration metadata
├── demo.py                     # Demo script
│
├── src/workshop_mcp/           # Main package
│   ├── __init__.py             # Package initialization
│   ├── server.py               # MCP server implementation
│   └── keyword_search.py       # Keyword search tool
│
├── agents/                     # Agent configurations
│   └── keyword_analysis.toml   # Keyword analysis agent
│
└── tests/                      # Test suite
    ├── __init__.py             # Test package init
    └── test_keyword_search.py  # Comprehensive tests
```

## 🧪 Testing Strategy

The project includes tests covering:

### Unit Tests
- **Basic functionality**: Keyword search across files
- **Edge cases**: Empty files, binary files, and invalid input handling
- **Concurrency**: Async operations and multi-directory searches

## 🚨 Troubleshooting

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


## 📚 Learning Resources

### MCP Protocol
- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [MCP Examples](https://github.com/modelcontextprotocol/servers)

### Python Async Programming
- [AsyncIO Documentation](https://docs.python.org/3/library/asyncio.html)
- [Real Python Async Guide](https://realpython.com/async-io-python/)

### Agent Development
- [Qodo Documentation](https://docs.qodo.ai/)
- [Agent Configuration Guide](https://docs.qodo.ai/qodo-documentation/qodo-command/features/creating-and-managing-agents)

## 🤝 Contributing

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
- Include unit tests for new features
- Update documentation as needed

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Model Context Protocol** team for the excellent protocol specification
- **Poetry** team for dependency management
- **Qodo** team for agent development platform
- **Python** community for async/await support

## 📞 Support

- **Issues**: Use your fork's issue tracker
- **Discussions**: Use your fork's discussions board

---

**Happy coding! 🎉**

*This workshop provides a solid foundation for building production-ready MCP agents in Python. Extend and customize it for your specific use cases.*
