# Python MCP Agent Workshop

A comprehensive workshop for building AI agents using the Model Context Protocol (MCP) in Python. This project demonstrates how to create MCP servers, implement custom tools, and configure intelligent agents for code analysis.

## Link to Presentation Slides

[Presentation Slides](https://github.com/nnennandukwe/python-mcp-agent-workshop/)


## 🚀 Quick Start


```bash

# Install the repository
git clone <repository-url>
cd agent-mcp-workshop-python

# Install dependencies
poetry install

# Verify setup
python3.12 verification.py

# Start the MCP server
poetry run workshop-mcp-server

# Run tests
poetry run pytest

# Use the agent (requires Qodo)
qodo keyword_analysis --set keyword="{KEYWORD_HERE}"
```

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

3. **Qodo Command** (for agent execution)
   - Install by running command `npm install -g @qodo/command`
   - Log in with the command `qodo login`
   - Verify: `qodo --version`
   - Additional resources: [docs.qodo.ai/qodo-documentation/qodo-command](https://docs.qodo.ai/qodo-documentation/qodo-command)

### Optional Tools

- **Git** for version control
- **VS Code** or your preferred IDE
- **Docker** (for containerized deployment)

## 🏗️ Architecture Overview

This workshop demonstrates a complete MCP ecosystem:

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
   - Implements MCP protocol
   - Exposes keyword search tool
   - Handles JSON-RPC communication

2. **Keyword Search Tool** (`src/workshop_mcp/keyword_search.py`)
   - Asynchronous file system search
   - Multi-format text file support
   - Statistical analysis and reporting

3. **AI Agent** (`agents/keyword_analysis.toml`)
   - Intelligent keyword analysis
   - Pattern recognition
   - Refactoring recommendations

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
   cd agent-mcp-workshop-python
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

# Linting
poetry run flake8 src/ tests/
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
agent-mcp-workshop-python/
├── pyproject.toml              # Poetry configuration
├── README.md                   # This file
├── verification.py             # Setup verification script
├── .gitignore                  # Git ignore rules
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

The project includes comprehensive tests covering:

### Unit Tests
- **Basic functionality**: Keyword search across files
- **Edge cases**: Empty files, binary files, permission errors
- **Concurrency**: Async operations and performance
- **Error handling**: Invalid inputs and system errors

### Integration Tests
- **MCP protocol**: Server startup and tool execution
- **File system**: Real directory traversal
- **Agent configuration**: TOML parsing and validation

### Performance Tests
- **Large codebases**: Scalability testing
- **Concurrent searches**: Multi-directory operations
- **Memory usage**: Resource consumption monitoring

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

3. **MCP Import Error**
   ```
   Error: No module named 'mcp'
   Solution: Run 'poetry install' to install dependencies
   ```

4. **Permission Denied**
   ```
   Error: Permission denied accessing files
   Solution: Check file permissions and user access
   ```

5. **Agent Configuration Error**
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

Run the comprehensive verification:

```bash
python3.12 verification.py
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
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
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

- **Issues**: [GitHub Issues](https://github.com/workshop/mcp-python-agent/issues)
- **Discussions**: [GitHub Discussions](https://github.com/workshop/mcp-python-agent/discussions)
- **Email**: nnenna.n@qodo.ai
- **Discord**:

---

**Happy coding! 🎉**

*This workshop provides a solid foundation for building production-ready MCP agents in Python. Extend and customize it for your specific use cases.*