# Coding Conventions

**Analysis Date:** 2026-01-25

## Naming Patterns

**Files:**
- Lowercase with underscores: `keyword_search.py`, `ast_analyzer.py`, `performance_checker.py`
- Test files follow pattern: `test_<module_name>.py` (e.g., `test_keyword_search.py`)
- Module directories use lowercase underscores: `performance_profiler/`

**Functions:**
- snake_case: `check_all()`, `check_n_plus_one_queries()`, `_search_directory()`
- Private/internal functions prefixed with underscore: `_read_message()`, `_write_message()`, `_build_pattern()`
- Test functions start with `test_`: `test_detect_blocking_open_in_async()`

**Variables:**
- snake_case: `root_paths`, `search_tasks`, `file_path_str`, `content_length`
- Constants in UPPER_CASE: `TEXT_EXTENSIONS`, `JSONRPC_VERSION`, `DEFAULT_PROTOCOL_VERSION`
- Private class attributes with underscore: `self._issues`, `self._search_tasks`

**Types:**
- PascalCase for classes: `KeywordSearchTool`, `PerformanceChecker`, `ASTAnalyzer`, `WorkshopMCPServer`, `JsonRpcError`
- PascalCase for enums: `Severity`, `IssueCategory`, `LoopInfo`, `FunctionInfo`, `CallInfo`

## Code Style

**Formatting:**
- Black formatter with 88-character line length (enforced via `pyproject.toml`)
- target-version set to Python 3.11
- No trailing whitespace

**Linting:**
- isort for import sorting with Black profile
- mypy for type checking
  - `disallow_untyped_defs = true` - All functions must have type hints
  - `warn_return_any = true` - Warns on any return types
  - `warn_unused_configs = true` - Warns on unused mypy configs

## Import Organization

**Order (as seen in source files):**
1. Standard library: `import asyncio`, `import json`, `import logging`, `import sys`
2. Standard library modules: `from dataclasses import dataclass`, `from pathlib import Path`, `from typing import ...`
3. Third-party: `import aiofiles`, `import astroid`
4. Local relative: `from .keyword_search import KeywordSearchTool`, `from .performance_profiler import PerformanceChecker`

**Path Aliases:**
- None configured; direct relative imports used throughout

**Type Hints:**
- Comprehensive type hints on all functions (mypy enforced)
- Examples from `server.py`:
  ```python
  def _read_message(self, stdin: Any) -> Optional[Dict[str, Any]]:
  def _handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
  async def execute(
      self,
      keyword: str,
      root_paths: List[str],
      *,
      case_insensitive: bool = False,
  ) -> Dict[str, Any]:
  ```

## Error Handling

**Patterns:**
- Explicit exception handling with type specification: `except ValueError as exc:`, `except FileNotFoundError:`
- Custom exception class for protocol errors: `JsonRpcError` with code, message, and optional data fields
- Validation at function boundaries with `ValueError` for invalid inputs
- `SyntaxError` for code parsing issues
- `FileNotFoundError` for missing files
- Logging with proper context: `logger.exception()`, `logger.error()`, `logger.warning()`
- Error responses in MCP protocol return formatted error objects with codes and messages

**Examples from `server.py`:**
```python
try:
    content_length = int(content_length_value)
except ValueError:
    raise JsonRpcError(-32600, "Invalid Content-Length header")

try:
    return json.loads(body.decode("utf-8"))
except json.JSONDecodeError as exc:
    raise JsonRpcError(-32700, "Parse error", {"details": str(exc)})
```

## Logging

**Framework:** Python's `logging` module

**Patterns:**
- Logger initialized per module: `logger = logging.getLogger(__name__)`
- Per-class loggers when needed: `self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")`
- Log levels used appropriately:
  - `logger.info()` for general server events and operation summaries
  - `logger.error()` for errors with context
  - `logger.exception()` for exception details with traceback
  - `logger.debug()` for detailed low-level information
  - `logger.warning()` for permission issues and recoverable errors
- Server logging configured to stderr: `handlers=[logging.StreamHandler(sys.stderr)]`

**Examples:**
```python
logger.info("Starting Workshop MCP Server (from scratch)")
logger.error("Error executing keyword_search")
logger.exception("Server loop error")
logger.warning(f"Permission denied accessing directory {root_path}: {e}")
```

## Comments

**When to Comment:**
- Module docstrings describe overall purpose (at top of file)
- Class docstrings describe the class purpose (required)
- Function docstrings required for all public functions with Args, Returns, Raises sections
- Inline comments for non-obvious logic or important implementation details
- Comments explain "why" not "what" (code shows what it does)

**JSDoc/TSDoc:**
- Google-style docstrings (as per CLAUDE.md requirements)
- Examples from `performance_checker.py`:
  ```python
  def check_n_plus_one_queries(self) -> List[PerformanceIssue]:
      """
      Detect N+1 query anti-patterns.

      This occurs when code iterates over a collection and makes a database
      query for each item instead of fetching all data at once.

      Returns:
          List of N+1 query issues
      """
  ```

## Function Design

**Size:**
- Functions are kept focused with single responsibility
- Longest functions are 50-80 lines with clear logical sections
- Helper methods extracted with `_` prefix for internal use

**Parameters:**
- Type-hinted on all parameters
- Keyword-only arguments for optional parameters where it makes sense
- Example from `keyword_search.py`:
  ```python
  async def execute(
      self,
      keyword: str,
      root_paths: List[str],
      *,
      case_insensitive: bool = False,
      use_regex: bool = False,
  ) -> Dict[str, Any]:
  ```

**Return Values:**
- Explicit return types on all functions
- `Optional[T]` used for nullable returns
- `Dict[str, Any]` for structured JSON-like responses
- Dataclass instances for complex returns

## Module Design

**Exports:**
- Public API via `from .module import Class` in `__init__.py`
- Example from `performance_profiler/__init__.py`:
  ```python
  from .ast_analyzer import ASTAnalyzer
  from .performance_checker import PerformanceChecker
  from .patterns import IssueCategory, PerformanceIssue, Severity
  ```

**Barrel Files:**
- Used in `performance_profiler/__init__.py` to expose public interface
- Not used in `workshop_mcp/` root (imports access submodules directly)

## Dataclasses

**Usage:**
- Used for structured data: `@dataclass` decorator on info classes
- Examples:
  - `FunctionInfo` - function metadata
  - `LoopInfo` - loop metadata
  - `CallInfo` - function call information
  - `JsonRpcError` - protocol error representation
- Benefits: automatic `__init__`, `__repr__`, equality comparison

**Pattern from `ast_analyzer.py`:**
```python
@dataclass
class CallInfo:
    """Information about a function call."""

    function_name: str
    line_number: int
    parent_function: Optional[str]
    is_in_loop: bool
    is_in_async_function: bool
    inferred_callable: Optional[str]
```

## Async/Await

**Pattern:**
- Async functions prefixed with `async def`
- Await used on async operations: `await asyncio.gather()`, `await file.read()`
- asyncio used for concurrency with `asyncio.gather()` for parallel execution
- Batch processing for resource management in `keyword_search.py` (50 files per batch)

**Example from `keyword_search.py`:**
```python
async def execute(self, keyword: str, root_paths: List[str], ...) -> Dict[str, Any]:
    search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
    for search_result in search_results:
        if isinstance(search_result, Exception):
            # Handle errors
```

---

*Convention analysis: 2026-01-25*
