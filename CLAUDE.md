# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python MCP Agent Workshop is an educational project demonstrating how to build AI agents using the Model Context Protocol (MCP). It implements an MCP server from scratch (no SDK) with two tools:

1. **Performance Profiler** - Semantic Python code analysis using Astroid AST parsing to detect performance anti-patterns
2. **Keyword Search** - Async file system search with statistical analysis

## Build and Development Commands

```bash
# Install dependencies
poetry install

# Verify setup
python verification.py

# Start the MCP server
poetry run workshop-mcp-server

# Run all tests (122 tests)
poetry run pytest

# Run specific test file
poetry run pytest tests/test_performance_checker.py -v

# Run with coverage
poetry run pytest --cov=workshop_mcp

# Lint and format code
poetry run ruff check --fix src/ tests/
poetry run ruff format src/ tests/

# Type checking
poetry run mypy src/
```

## Architecture

```
AI Agents (Gemini 2.5 Pro)
    │
    ▼
MCP Server (server.py) ─── JSON-RPC 2.0 over stdio
    │
    ├── Tool: keyword_search ────► KeywordSearchTool (async file search)
    │
    └── Tool: performance_check ─► Performance Profiler
                                    ├── ASTAnalyzer (Astroid-powered)
                                    ├── PerformanceChecker
                                    └── Pattern Definitions
```

### Key Components

- **MCP Server** (`src/workshop_mcp/server.py`) - Implements MCP protocol with Content-Length framing over stdio, JSON-RPC 2.0 compliant
- **Keyword Search** (`src/workshop_mcp/keyword_search.py`) - Async file search with regex support, ReDoS protection, batched processing (50 files/batch)
- **Performance Profiler** (`src/workshop_mcp/performance_profiler/`) - Detects N+1 queries, blocking I/O in async, inefficient loops, memory issues

### Why Astroid over Standard AST?

The performance profiler uses Astroid for semantic analysis because it provides type inference, call resolution, and cross-module understanding that standard AST lacks. This enables detecting patterns like "ORM query inside a loop" that require semantic context.

## Code Style

- Python 3.11+ required
- Ruff for linting and formatting with 100-character line length
- Type hints required on all functions
- Google-style docstrings
- Snake_case for files/functions, PascalCase for classes
- Async tests require `@pytest.mark.asyncio` decorator
- Pre-commit hooks enforce formatting and linting on commit

## Testing

Tests are organized by component:
- `test_ast_analyzer.py` (41 tests) - AST analysis
- `test_performance_checker.py` (31 tests) - Pattern detection
- `test_keyword_search.py` (15 tests) - File search
- `test_mcp_server_integration.py` (10 tests) - Tool registration
- `test_mcp_server_protocol.py` (5 tests) - Message framing

Use `source_code` parameter instead of file I/O in tests.

## Adding New Performance Checks

1. Define the pattern in `src/workshop_mcp/performance_profiler/patterns.py`
2. Add detection logic in `performance_checker.py`
3. Write tests in `tests/test_performance_checker.py`

## Workshop Learning Path

The numbered markdown files (00-04) walk through building the MCP server:
1. `00-introduction.md` - Introduction
2. `01-transport.md` - Content-Length framing over stdio
3. `02-jsonrpc.md` - JSON-RPC validation and routing
4. `03-initialize.md` - Capability handshake
5. `04-tools.md` - Tool advertising and invocation
