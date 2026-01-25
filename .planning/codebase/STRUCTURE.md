# Codebase Structure

**Analysis Date:** 2026-01-25

## Directory Layout

```
python-mcp-agent-workshop/
├── src/
│   └── workshop_mcp/           # Main package
│       ├── __init__.py         # Package metadata
│       ├── server.py           # MCP server (main entry point)
│       ├── keyword_search.py   # Keyword search tool implementation
│       └── performance_profiler/  # Performance analysis subpackage
│           ├── __init__.py
│           ├── ast_analyzer.py    # Astroid-based code parsing
│           ├── performance_checker.py  # Pattern detection orchestrator
│           └── patterns.py        # Pattern definitions and rules
├── tests/
│   ├── __init__.py
│   ├── test_mcp_server_integration.py  # End-to-end MCP tests
│   ├── test_mcp_server_protocol.py     # Message framing tests
│   ├── test_keyword_search.py          # Keyword search tests
│   ├── test_ast_analyzer.py            # AST parsing tests
│   ├── test_performance_checker.py     # Pattern detection tests
│   ├── test_agent_config.py            # Agent configuration tests
│   └── test_e2e_workflow.py            # Full workflow tests
├── test_fixtures/
│   ├── sample_bad_performance.py       # Test file with bad patterns
│   ├── sample_good_performance.py      # Test file with good patterns
│   ├── sample_mixed.py                 # Test file with mixed patterns
│   └── sample_syntax_error.py          # Test file for error handling
├── docs/                       # Documentation
├── examples/                   # Usage examples
├── agents/                     # Agent configurations
├── 00-introduction.md          # Learning path: Introduction
├── 01-transport.md             # Learning path: Content-Length framing
├── 02-jsonrpc.md               # Learning path: JSON-RPC validation
├── 03-initialize.md            # Learning path: Capability handshake
├── 04-tools.md                 # Learning path: Tool advertising
├── pyproject.toml              # Poetry project configuration
├── poetry.lock                 # Locked dependency versions
├── CLAUDE.md                   # Claude Code guidance
├── README.md                   # Project overview
└── verification.py             # Setup verification script
```

## Directory Purposes

**src/workshop_mcp:**
- Purpose: Main Python package containing MCP server and tools
- Contains: Server implementation, tool implementations, AST analysis
- Key files: `server.py` (orchestrator), `keyword_search.py`, `performance_profiler/`

**src/workshop_mcp/performance_profiler:**
- Purpose: Subpackage for performance analysis functionality
- Contains: AST parsing, pattern detection, issue reporting
- Key files: `ast_analyzer.py`, `performance_checker.py`, `patterns.py`

**tests:**
- Purpose: Test suite organized by component
- Contains: Unit tests (41 AST, 31 perf checker, 15 keyword search, 10 integration, 5 protocol)
- Pattern: Test classes per component with multiple test methods
- Key files: See structure above - 102 total tests

**test_fixtures:**
- Purpose: Python source files used as test inputs for performance checker
- Contains: Pre-written Python files with known performance issues/patterns
- Generated: No, checked into repository
- Committed: Yes

**docs:**
- Purpose: Additional documentation and guides
- Contains: Architecture diagrams, setup guides, usage documentation

**examples:**
- Purpose: Example usage scripts and integration patterns
- Contains: Demonstration code for using the MCP server

**agents:**
- Purpose: AI agent configurations for using this MCP server
- Contains: Configuration files for Gemini or other AI agents

## Key File Locations

**Entry Points:**
- `src/workshop_mcp/server.py`: Main MCP server - contains sync_main() entry point (line 524)
- `pyproject.toml`: Script entry point definition - maps `workshop-mcp-server` CLI command to sync_main()

**Configuration:**
- `pyproject.toml`: Poetry configuration, dependencies, pytest/black/isort/mypy settings
- `.env`: Environment variables (if needed)
- `pyproject.toml` [tool.pytest.ini_options]: pytest configured with asyncio_mode="auto"
- `pyproject.toml` [tool.black]: line-length=88, target Python 3.11
- `pyproject.toml` [tool.mypy]: strict mode with disallow_untyped_defs=true

**Core Logic:**

**MCP Protocol:**
- `src/workshop_mcp/server.py` (lines 1-140): Message I/O (reading/writing with Content-Length framing)
- `src/workshop_mcp/server.py` (lines 146-181): Request dispatcher and routing

**Keyword Search:**
- `src/workshop_mcp/keyword_search.py` (lines 21-176): KeywordSearchTool class and execute() method
- `src/workshop_mcp/keyword_search.py` (lines 178-305): File/directory traversal and search

**Performance Analysis:**
- `src/workshop_mcp/performance_profiler/ast_analyzer.py`: ASTAnalyzer class for semantic parsing
- `src/workshop_mcp/performance_profiler/performance_checker.py` (lines 42-70): check_all() orchestrator
- `src/workshop_mcp/performance_profiler/performance_checker.py` (lines 72-220): Individual check methods
- `src/workshop_mcp/performance_profiler/patterns.py`: Pattern definitions and helper functions

**Testing:**
- `tests/test_mcp_server_integration.py`: Full tool execution tests
- `tests/test_mcp_server_protocol.py`: Message framing and JSON-RPC protocol tests
- `tests/test_keyword_search.py`: KeywordSearchTool tests
- `tests/test_ast_analyzer.py`: ASTAnalyzer tests (41 tests)
- `tests/test_performance_checker.py`: Pattern detection tests (31 tests)
- `test_fixtures/`: Sample Python files for testing

## Naming Conventions

**Files:**
- Source: `snake_case.py` (e.g., `keyword_search.py`, `performance_checker.py`)
- Tests: `test_<component>.py` (e.g., `test_keyword_search.py`)
- Fixtures: `sample_<description>.py` (e.g., `sample_bad_performance.py`)

**Directories:**
- Package: `snake_case/` (e.g., `workshop_mcp/`, `performance_profiler/`)
- Test: `tests/`
- Documentation: `docs/`, `examples/`

**Classes:**
- PascalCase (e.g., `KeywordSearchTool`, `PerformanceChecker`, `ASTAnalyzer`)
- Dataclasses for value objects (e.g., `PerformanceIssue`, `CallInfo`, `FunctionInfo`)
- Exceptions inherit from Exception (e.g., `JsonRpcError` as dataclass, not Exception subclass)

**Functions/Methods:**
- snake_case (e.g., `check_all()`, `execute()`, `_read_message()`)
- Private methods prefixed with `_` (e.g., `_search_directory()`, `_handle_request()`)
- Public methods for tool API (e.g., `execute()`, `check_all()`)

**Variables/Constants:**
- UPPERCASE for constants (e.g., `JSONRPC_VERSION`, `DEFAULT_PROTOCOL_VERSION`, `TEXT_EXTENSIONS`)
- snake_case for instance/local variables
- Type hints on all function parameters and returns

## Where to Add New Code

**New Performance Check:**
1. Add pattern definition in `src/workshop_mcp/performance_profiler/patterns.py`:
   - Extend `IssueCategory` enum
   - Add pattern/rule constants
   - Add helper function if needed (e.g., `is_<pattern>()`)
2. Add detection method in `src/workshop_mcp/performance_profiler/performance_checker.py`:
   - Method name: `check_<issue_type>()`
   - Returns: `List[PerformanceIssue]`
   - Call from `check_all()` method (line 55-58)
3. Add tests in `tests/test_performance_checker.py`:
   - Test class: `Test<IssueType>Detection`
   - Test methods: `test_detect_<scenario>` pattern

**New Tool:**
1. Create tool class in `src/workshop_mcp/` or subpackage
   - Public method: `execute(**kwargs)` returning Dict[str, Any]
   - Implement error handling and logging
2. Update `src/workshop_mcp/server.py`:
   - Import new tool (line 16-17 area)
   - Instantiate in `__init__` (line 52 area)
   - Add to `_handle_list_tools()` response (line 202-259 area)
   - Add handler in `_handle_call_tool()` (line 290-310 area)
   - Implement execution method `_execute_<tool_name>()` (line 312+ area)
3. Add tests in `tests/test_<tool_name>.py`
4. Update documentation in README.md

**New Utility Function:**
- AST analysis helpers: `src/workshop_mcp/performance_profiler/ast_analyzer.py` or `patterns.py`
- String/regex utilities: `src/workshop_mcp/keyword_search.py` (private methods)
- MCP protocol helpers: `src/workshop_mcp/server.py` (private methods prefixed with `_`)

**Bug Fixes/Refactoring:**
- Preserve existing function signatures (public API)
- Update related tests when changing behavior
- Add regression tests if fixing a reported issue
- Update docstrings if logic changes

## Special Directories

**test_fixtures:**
- Purpose: Pre-written Python files used as test inputs
- Generated: No, manually authored
- Committed: Yes, version controlled
- Usage: Imported by tests via Path objects
  - Example: `Path("test_fixtures/sample_bad_performance.py")`

**docs/**
- Purpose: Architecture documentation and learning materials
- Generated: No, manually written
- Committed: Yes

**examples/**
- Purpose: Usage examples and integration demos
- Generated: Potentially (may include generated output)
- Committed: Yes, source examples committed

**.planning/codebase/**
- Purpose: GSD analysis documents (created by mapper agents)
- Generated: Yes, auto-generated by codebase analysis
- Committed: No (in .gitignore pattern)

**.claude/**
- Purpose: Claude Code session artifacts
- Generated: Yes, auto-generated
- Committed: No (git-ignored)

**src/workshop_mcp/__pycache__/ and tests/__pycache__/**
- Purpose: Python bytecode cache
- Generated: Yes, auto-generated by Python
- Committed: No (in .gitignore)

