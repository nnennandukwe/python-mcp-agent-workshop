# Architecture

**Analysis Date:** 2026-01-25

## Pattern Overview

**Overall:** Layered MCP Protocol Server with two specialized analysis tools

**Key Characteristics:**
- Implements MCP (Model Context Protocol) over stdio with Content-Length framing
- Request-response model built on JSON-RPC 2.0
- Decoupled tool implementations: keyword search and performance analysis
- Event loop integration for async operations within synchronous MCP server
- Semantic code analysis using Astroid AST (not standard Python AST)

## Layers

**Protocol Layer:**
- Purpose: Handle JSON-RPC 2.0 message framing, validation, and error responses
- Location: `src/workshop_mcp/server.py` (lines 104-144 for message I/O)
- Contains: Message reading/writing with Content-Length headers, JSON-RPC error handling
- Depends on: Python stdlib (sys, json, logging)
- Used by: Request dispatcher

**Request Dispatcher Layer:**
- Purpose: Route incoming JSON-RPC requests to appropriate handlers
- Location: `src/workshop_mcp/server.py` (_handle_request method, lines 146-181)
- Contains: Method routing (initialize, list_tools, call_tool), request validation
- Depends on: Protocol layer
- Used by: Server main loop

**Tool Handler Layer:**
- Purpose: Execute tools and format responses
- Location: `src/workshop_mcp/server.py` (_execute_keyword_search, _execute_performance_check)
- Contains: Tool invocation, parameter validation, result formatting
- Depends on: Tool implementations
- Used by: Request dispatcher

**Tool Implementation Layer:**

**Keyword Search Tool:**
- Purpose: Async file system search with regex support and statistical analysis
- Location: `src/workshop_mcp/keyword_search.py`
- Contains: KeywordSearchTool class with async execute() method
- Pattern: AsyncIO-based concurrent file I/O with batched processing
- Entry: async execute(keyword, root_paths, case_insensitive, use_regex, include_patterns, exclude_patterns)

**Performance Profiler Tool:**
- Purpose: Semantic code analysis for performance anti-patterns
- Location: `src/workshop_mcp/performance_profiler/`
- Contains:
  - `performance_checker.py`: PerformanceChecker class (orchestrator)
  - `ast_analyzer.py`: ASTAnalyzer class (Astroid-based semantic analysis)
  - `patterns.py`: Pattern definitions and detection rules
- Pattern: Visitor pattern over Astroid AST with pattern matching
- Entry: PerformanceChecker.check_all() returns List[PerformanceIssue]

## Data Flow

**Keyword Search Flow:**

1. Client sends JSON-RPC request: `{"method": "call_tool", "params": {"name": "keyword_search", "arguments": {...}}}`
2. Server receives on stdin, parses Content-Length framing
3. _handle_request routes to _execute_keyword_search
4. KeywordSearchTool.execute() runs async in event loop
   - Walks directory tree using os.walk (efficient with pruning)
   - Spawns async tasks for file reading via aiofiles (non-blocking I/O)
   - Batches 50 files at a time via asyncio.gather()
   - Counts occurrences using regex or string search
   - Accumulates statistics (match count, distribution)
5. Results serialized to JSON, wrapped in MCP response
6. Server writes Content-Length header + JSON payload to stdout

**Performance Check Flow:**

1. Client sends JSON-RPC request with source_code or file_path parameter
2. Server receives and validates exactly one of source_code/file_path is provided
3. _execute_performance_check instantiates PerformanceChecker
4. PerformanceChecker.check_all() orchestrates all checks:
   - ASTAnalyzer.parse() builds Astroid module tree
   - check_n_plus_one_queries() - finds ORM calls in loops
   - check_blocking_io_in_async() - finds blocking I/O in async functions
   - check_inefficient_loops() - detects redundant operations
   - check_memory_inefficiencies() - identifies memory waste
5. Issues sorted by severity then line number
6. Results formatted with code snippets and suggestions
7. Wrapped in MCP response content object
8. Server writes to stdout

**State Management:**

- **MCP Server State:** Single WorkshopMCPServer instance per process with one event loop (created in __init__)
- **Keyword Search State:** Shared result dictionary mutated by concurrent tasks (thread-safe via asyncio single-threaded event loop)
- **Performance Checker State:** PerformanceChecker caches results in _issues after first check_all() call
- **AST Analysis State:** Immutable Astroid tree built once during initialization, cached in self.tree

## Key Abstractions

**JsonRpcError:**
- Purpose: Structured error responses with JSON-RPC error codes
- Location: `src/workshop_mcp/server.py` (dataclass, lines 32-39)
- Pattern: Dataclass with code/message/data fields
- Used by: Error response generation

**CallInfo (and LoopInfo, FunctionInfo, ImportInfo):**
- Purpose: Structured representation of code artifacts extracted from AST
- Location: `src/workshop_mcp/performance_profiler/ast_analyzer.py` (dataclasses, lines 9-57)
- Pattern: Dataclass with semantic metadata (is_async, is_in_loop, inferred_callable, etc.)
- Usage: Enables pattern detection without direct AST traversal

**PerformanceIssue:**
- Purpose: Unified representation of detected performance problems
- Location: `src/workshop_mcp/performance_profiler/patterns.py` (dataclass, lines 28-39)
- Fields: category, severity, line_number, description, suggestion, code_snippet, function_name
- Pattern: Immutable issue object created during analysis, serialized to JSON for response

**ASTAnalyzer:**
- Purpose: Semantic code understanding using Astroid
- Location: `src/workshop_mcp/performance_profiler/ast_analyzer.py`
- Pattern: Single-pass analysis with lazy-evaluated cached properties (get_calls(), get_functions(), get_loops(), get_imports())
- Why Astroid: Provides type inference, call resolution, and cross-module understanding that standard AST lacks

## Entry Points

**MCP Server Entry:**
- Location: `src/workshop_mcp/server.py` (sync_main function, lines 524-538)
- Triggers: Invoked via pyproject.toml script entry: `workshop-mcp-server = "workshop_mcp.server:sync_main"`
- Responsibilities:
  - Create WorkshopMCPServer instance
  - Call serve() to start message loop
  - Handle KeyboardInterrupt and fatal errors

**Server Message Loop:**
- Location: WorkshopMCPServer.serve() (lines 56-68)
- Triggers: Entry point or testing
- Responsibilities:
  - Read JSON-RPC messages from stdin with Content-Length framing
  - Route to _handle_request()
  - Write response to stdout
  - Continue until EOF or error

**Request Handler:**
- Location: WorkshopMCPServer._handle_request() (lines 146-181)
- Triggers: Message loop calls for each request
- Responsibilities:
  - Validate JSON-RPC structure
  - Route by method name (initialize, list_tools, call_tool)
  - Return response or None for notifications

## Error Handling

**Strategy:** Structured JSON-RPC error codes with optional data payloads for debugging

**Patterns:**

**Protocol Level (Content-Length, JSON parse):**
- Missing/invalid Content-Length → JsonRpcError(-32600, "Missing/Invalid Content-Length header")
- JSON parse failure → JsonRpcError(-32700, "Parse error")
- Framing EOF → returns False to end server loop
- Location: _read_message() (lines 104-136)

**Request Validation:**
- Invalid JSON-RPC structure → JsonRpcError(-32600, "Invalid Request")
- Unknown method → JsonRpcError(-32601, "Method not found")
- Invalid params type → JsonRpcError(-32602, "Invalid params")
- Location: _handle_request() (lines 146-181)

**Tool Execution:**
- Missing required argument → JsonRpcError(-32602, "Missing required argument")
- Invalid argument type → JsonRpcError(-32602, "keyword must be a string", etc.)
- File not found / syntax error → JsonRpcError(-32602, str(exc))
- Unexpected exception → JsonRpcError(-32603, "Internal error", details)
- Location: _execute_keyword_search() and _execute_performance_check()

**Async Task Failures:**
- Individual file read errors caught and counted in summary (doesn't stop search)
- Permission denied logged as warning, error count incremented
- Location: KeywordSearchTool._search_file() and _search_directory() (lines 235-304)

## Cross-Cutting Concerns

**Logging:**
- Standard Python logging module configured in server.py (lines 20-26)
- stderr output for all log levels (INFO and above visible in production)
- Nested loggers per class (e.g., KeywordSearchTool uses logger with class name)
- Key events: server startup/shutdown, tool execution start, search completion, errors

**Validation:**
- Keyword/root_paths presence checked in KeywordSearchTool.execute()
- File path existence checked before analysis in PerformanceChecker
- MCP parameter types validated at tool handler layer
- Regex ReDoS protection via dangerous pattern detection (line 326-334 in keyword_search.py)

**Authentication:**
- Not applicable - no MCP authentication layer implemented
- Runs as single privileged process with direct file system access

**Type Hints:**
- All public functions have complete type hints (required by mypy config)
- Return types specified throughout
- Optional types used for nullable values
- Pattern matching uses Optional[Pattern[str]] for compiled regex

