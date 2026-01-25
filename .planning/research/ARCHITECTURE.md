# Architecture Research: Security Hardening for Python MCP Server

**Domain:** Python security validation layers for MCP/JSON-RPC servers
**Researched:** 2026-01-25
**Confidence:** HIGH

## Executive Summary

This research addresses how to integrate security validation (path validation, regex safety, error sanitization) into the existing MCP server architecture. The analysis recommends a **layered utility module approach** with optional decorator wrappers, placing validation at the earliest possible point in the request flow.

The key architectural insight: security validation belongs in a dedicated module that the server calls explicitly, not scattered across tool implementations. This provides centralized security policy, testable isolation, and clear audit trails.

## Current Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     External (AI Agent)                         │
│                  Gemini 2.5 Pro via MCP Client                  │
├─────────────────────────────────────────────────────────────────┤
│                     Transport Layer                              │
│         Content-Length framing over stdio (JSON-RPC 2.0)        │
├─────────────────────────────────────────────────────────────────┤
│                     MCP Server (server.py)                       │
│  ┌─────────────┐  ┌──────────────────┐  ┌─────────────────────┐ │
│  │ _read_msg   │→ │ _handle_request  │→ │ _handle_call_tool   │ │
│  │ _write_msg  │  │ (JSON-RPC route) │  │ (tool dispatch)     │ │
│  └─────────────┘  └──────────────────┘  └──────────┬──────────┘ │
├─────────────────────────────────────────────────────┼───────────┤
│                     Tool Layer                       │           │
│  ┌───────────────────────────┐  ┌────────────────────┴────────┐ │
│  │ _execute_keyword_search   │  │ _execute_performance_check  │ │
│  │ - param validation        │  │ - param validation          │ │
│  │ - tool invocation         │  │ - tool invocation           │ │
│  │ - result formatting       │  │ - result formatting         │ │
│  └─────────────┬─────────────┘  └─────────────┬───────────────┘ │
├───────────────────────────────────────────────────────────────────┤
│                     Business Logic                                │
│  ┌───────────────────────────┐  ┌─────────────────────────────┐ │
│  │ KeywordSearchTool         │  │ PerformanceChecker          │ │
│  │ - async file traversal    │  │ - Astroid AST analysis      │ │
│  │ - regex pattern matching  │  │ - pattern detection         │ │
│  └───────────────────────────┘  └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Current Data Flow

```
AI Agent Request
    │
    ▼
_read_message() ─────────────────→ Content-Length parse
    │
    ▼
_handle_request() ───────────────→ JSON-RPC validation
    │                              - jsonrpc version
    │                              - method routing
    ▼
_handle_call_tool() ─────────────→ Tool name dispatch
    │
    ├──→ _execute_keyword_search()
    │        │
    │        ├── Type validation (isinstance checks)
    │        ├── KeywordSearchTool.execute()
    │        │       ├── Path resolution (resolve())
    │        │       ├── Pattern compilation
    │        │       └── File search
    │        └── Result formatting
    │
    └──→ _execute_performance_check()
             │
             ├── Type validation
             ├── PerformanceChecker init
             │       └── File read OR source_code parse
             └── Result formatting
```

### Security Gaps in Current Flow

| Location | Gap | Risk |
|----------|-----|------|
| `_execute_keyword_search` | No path traversal check | Arbitrary file read |
| `_execute_keyword_search` | Limited ReDoS protection | CPU exhaustion |
| `_execute_performance_check` | No path validation | Arbitrary file read |
| `_error_response` | Raw exception in details | Info disclosure |
| Exception handlers | `str(exc)` passed to client | Stack trace leakage |

## Recommended Architecture: Security Validation Layer

### Proposed System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     External (AI Agent)                         │
├─────────────────────────────────────────────────────────────────┤
│                     Transport Layer                              │
│         Content-Length framing over stdio (JSON-RPC 2.0)        │
├─────────────────────────────────────────────────────────────────┤
│                     MCP Server (server.py)                       │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                  _handle_call_tool                          ││
│  │  ┌──────────────────────────────────────────────────────┐   ││
│  │  │            SECURITY VALIDATION LAYER                 │   ││
│  │  │  ┌────────────┐ ┌────────────┐ ┌─────────────────┐   │   ││
│  │  │  │   Path     │ │   Regex    │ │     Error       │   │   ││
│  │  │  │ Validator  │ │ Validator  │ │   Sanitizer     │   │   ││
│  │  │  └────────────┘ └────────────┘ └─────────────────┘   │   ││
│  │  └──────────────────────────────────────────────────────┘   ││
│  └─────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────┤
│                     Tool Executors                               │
│  ┌───────────────────────────┐  ┌─────────────────────────────┐ │
│  │ _execute_keyword_search   │  │ _execute_performance_check  │ │
│  └───────────────────────────┘  └─────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                     Business Logic (unchanged)                   │
└─────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
src/workshop_mcp/
├── __init__.py
├── server.py                    # MCP server (unchanged interface)
├── keyword_search.py            # Keyword search tool (unchanged)
├── security/                    # NEW: Security validation module
│   ├── __init__.py              # Public API exports
│   ├── path_validator.py        # Path traversal prevention
│   ├── regex_validator.py       # ReDoS protection
│   ├── error_sanitizer.py       # Exception sanitization
│   └── exceptions.py            # Security-specific exceptions
└── performance_profiler/        # Performance checker (unchanged)
    ├── __init__.py
    ├── ast_analyzer.py
    ├── patterns.py
    └── performance_checker.py
```

### Structure Rationale

- **`security/` as separate module:** Isolates security concerns from business logic. Security code is testable independently, reusable across tools, and auditable in one place.
- **Individual files per concern:** Path validation, regex validation, and error sanitization have different dependencies and testing needs. Separation enables targeted testing.
- **`exceptions.py`:** Custom exceptions (`PathValidationError`, `RegexValidationError`) provide typed error handling distinct from business errors.

## Architectural Decision: Utility Module vs Decorator

### Options Evaluated

| Approach | Pros | Cons |
|----------|------|------|
| **Utility Module (explicit calls)** | Clear control flow, easy debugging, explicit about what's validated | More verbose at call sites |
| **Decorator Pattern** | Concise, automatic application | Hidden behavior, harder to debug, inflexible for conditional validation |
| **Middleware Pattern** | Centralized, all-or-nothing | Doesn't fit MCP server structure (not web framework), over-engineering |
| **Pydantic @validate_call** | Type coercion, rich validation | Adds dependency, performance overhead, doesn't handle security-specific concerns |

### Recommendation: Utility Module with Explicit Calls

**Use utility module pattern because:**

1. **Explicit is better than implicit** (Python zen). Security validation points should be visible in code review.

2. **Different tools need different validation.** Keyword search validates paths AND regex. Performance check validates paths only. Decorators force uniform validation.

3. **Easier debugging.** When security validation fails, stack trace points directly to the validation call, not buried in decorator magic.

4. **Testable in isolation.** Security module can be unit tested without MCP server infrastructure.

5. **Matches existing code style.** Current codebase uses explicit function calls, not decorator patterns.

**Reference:** [Python Decorator Confusion: Pattern vs Syntax Explained](https://taiheard.medium.com/the-python-decorator-confusion-pattern-vs-syntax-explained-dc6185e3b25b) - decorators are best for cross-cutting concerns that apply uniformly, not conditional security logic.

## Component Responsibilities

| Component | Responsibility | Communicates With |
|-----------|----------------|-------------------|
| `security.path_validator` | Validate file paths stay within allowed boundaries | Called by server before tool execution |
| `security.regex_validator` | Validate regex patterns for ReDoS safety | Called by server before passing to KeywordSearchTool |
| `security.error_sanitizer` | Strip sensitive details from exceptions | Called by server in exception handlers |
| `security.exceptions` | Define typed security exceptions | Raised by validators, caught by server |
| `server.py` | Orchestrate validation and tool dispatch | Calls security module, then tools |

## Proposed Data Flow

### Keyword Search Flow (with security)

```
_execute_keyword_search(request_id, arguments)
    │
    ├── 1. Type validation (existing)
    │
    ├── 2. PATH VALIDATION (new)
    │       │
    │       └── security.path_validator.validate_paths(
    │               root_paths,
    │               allowed_roots=[CWD, or configured list]
    │           )
    │           → raises PathValidationError if traversal detected
    │
    ├── 3. REGEX VALIDATION (new, if use_regex=True)
    │       │
    │       └── security.regex_validator.validate_pattern(
    │               keyword,
    │               max_complexity=100,  # configurable
    │               timeout_ms=1000      # fail-fast check
    │           )
    │           → raises RegexValidationError if dangerous pattern
    │
    ├── 4. Tool execution (existing)
    │       │
    │       └── KeywordSearchTool.execute(...)
    │
    └── 5. Result formatting (existing)

    Exception handling:
    ├── PathValidationError → -32602 "Invalid path: path outside allowed directory"
    ├── RegexValidationError → -32602 "Invalid regex: pattern too complex"
    └── Exception → -32603 with SANITIZED error details
```

### Performance Check Flow (with security)

```
_execute_performance_check(request_id, arguments)
    │
    ├── 1. Type validation (existing)
    │
    ├── 2. PATH VALIDATION (new, if file_path provided)
    │       │
    │       └── security.path_validator.validate_path(
    │               file_path,
    │               allowed_roots=[CWD, or configured list],
    │               must_exist=True,
    │               allowed_extensions=['.py']
    │           )
    │           → raises PathValidationError
    │
    ├── 3. Tool execution (existing)
    │       │
    │       └── PerformanceChecker(file_path=...) or (source_code=...)
    │
    └── 4. Result formatting (existing)

    Exception handling:
    └── Same sanitization as keyword_search
```

### Error Sanitization Flow

```
try:
    # tool execution
except PathValidationError as e:
    return error_response(-32602, str(e))  # safe by design
except RegexValidationError as e:
    return error_response(-32602, str(e))  # safe by design
except (ValueError, FileNotFoundError) as e:
    return error_response(-32602,
        security.error_sanitizer.sanitize(e, include_type=True)
    )
except Exception as e:
    logger.exception("Tool execution failed")  # full details to logs
    return error_response(-32603,
        security.error_sanitizer.sanitize_internal(e)
        # Returns generic "An unexpected error occurred"
        # with error_id for log correlation
    )
```

## Patterns to Follow

### Pattern 1: Fail-Fast Validation

**What:** Validate all inputs before any processing begins. Reject bad inputs immediately at the entry point.

**When to use:** Every tool execution method that accepts external input.

**Trade-offs:** Slight code duplication across tools vs. security guarantee that no unvalidated input reaches business logic.

**Example:**
```python
def _execute_keyword_search(self, request_id, arguments):
    # 1. Type validation (existing)
    keyword = arguments.get("keyword")
    root_paths = arguments.get("root_paths")
    use_regex = arguments.get("use_regex", False)

    # 2. Security validation (new) - BEFORE any tool interaction
    try:
        validated_paths = path_validator.validate_paths(
            root_paths,
            allowed_roots=self._get_allowed_roots()
        )
    except PathValidationError as e:
        return self._error_response(request_id,
            JsonRpcError(-32602, str(e)))

    if use_regex:
        try:
            regex_validator.validate_pattern(keyword)
        except RegexValidationError as e:
            return self._error_response(request_id,
                JsonRpcError(-32602, str(e)))

    # 3. Now safe to proceed with tool execution
    result = self.loop.run_until_complete(
        self.keyword_search_tool.execute(keyword, validated_paths, ...)
    )
```

### Pattern 2: Typed Security Exceptions

**What:** Define custom exception classes for each security validation failure type. Never use generic exceptions for security failures.

**When to use:** All security validation code.

**Trade-offs:** More exception classes to maintain vs. precise error handling and safe-by-design error messages.

**Example:**
```python
# security/exceptions.py
class SecurityValidationError(Exception):
    """Base class for security validation errors."""
    pass

class PathValidationError(SecurityValidationError):
    """Raised when path validation fails."""
    def __init__(self, message: str, path: str = None):
        # Message is designed to be safe for external display
        self.path = path  # stored but not included in str()
        super().__init__(message)

class RegexValidationError(SecurityValidationError):
    """Raised when regex pattern is unsafe."""
    def __init__(self, message: str, pattern: str = None):
        self.pattern = pattern  # stored but not included in str()
        super().__init__(message)
```

### Pattern 3: Allowlist Over Blocklist

**What:** Define what IS allowed rather than trying to block what's dangerous. For paths, specify allowed root directories. For regex, specify allowed complexity limits.

**When to use:** All input validation.

**Trade-offs:** More restrictive (may block legitimate use cases) vs. more secure (unknown attacks can't bypass).

**Example:**
```python
# security/path_validator.py
def validate_path(
    path: str,
    allowed_roots: list[Path],
    must_exist: bool = False,
    allowed_extensions: list[str] | None = None
) -> Path:
    """
    Validate path is within allowed directories.

    Args:
        path: User-provided path string
        allowed_roots: List of allowed root directories
        must_exist: If True, path must exist
        allowed_extensions: If provided, file must have one of these extensions

    Returns:
        Resolved, validated Path object

    Raises:
        PathValidationError: If validation fails
    """
    resolved = Path(path).resolve()

    # Allowlist check: path must be under one of allowed_roots
    is_allowed = any(
        _is_path_under(resolved, root)
        for root in allowed_roots
    )
    if not is_allowed:
        raise PathValidationError(
            "Path outside allowed directory",
            path=str(resolved)
        )

    if must_exist and not resolved.exists():
        raise PathValidationError(
            f"Path does not exist",
            path=str(resolved)
        )

    if allowed_extensions and resolved.suffix.lower() not in allowed_extensions:
        raise PathValidationError(
            f"File type not allowed",
            path=str(resolved)
        )

    return resolved

def _is_path_under(path: Path, root: Path) -> bool:
    """Check if path is under root directory (handles symlinks)."""
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False
```

**Reference:** [Preventing Directory Traversal in Python](https://www.guyrutenberg.com/2013/12/06/preventing-directory-traversal-in-python/) - use `relative_to()` after `resolve()` for robust path validation.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Validation in Business Logic

**What people do:** Put path validation inside `KeywordSearchTool.execute()` or `PerformanceChecker.__init__()`.

**Why it's wrong:**
- Business logic shouldn't know about security policies
- Different callers may have different allowed paths
- Harder to audit security in one place
- Tool becomes untestable with arbitrary paths

**Do this instead:** Validate in server layer before calling tool. Tool receives already-validated paths and trusts its caller.

### Anti-Pattern 2: String-Based Path Checking

**What people do:**
```python
# BAD: Easily bypassed
if "../" in path or path.startswith("/"):
    raise Error("Invalid path")
```

**Why it's wrong:** Attackers can bypass with URL encoding (`%2e%2e%2f`), alternate separators, or Unicode normalization.

**Do this instead:** Use `pathlib.Path.resolve()` + `relative_to()` which handles canonicalization.

**Reference:** [OpenStack Security Guidelines](https://security.openstack.org/guidelines/dg_using-file-paths.html) - always resolve paths before comparison.

### Anti-Pattern 3: Exposing Exception Details

**What people do:**
```python
# BAD: Leaks internal details
except Exception as e:
    return error_response(-32603, f"Error: {str(e)}")
```

**Why it's wrong:** Exception messages may contain:
- File paths revealing server structure
- Database connection strings
- Stack traces with library versions
- User data from failed operations

**Do this instead:** Log full exception internally, return generic message with correlation ID.

**Reference:** [Python Security Best Practices](https://corgea.com/Learn/python-security-best-practices-a-comprehensive-guide-for-engineers) - sanitize all error messages before returning to users.

### Anti-Pattern 4: Regex Timeout After Match Start

**What people do:**
```python
# BAD: Timeout only helps if match takes long time
import signal
signal.alarm(1)
result = pattern.match(content)
signal.alarm(0)
```

**Why it's wrong:** Signal-based timeouts:
- Don't work on Windows
- Don't work in threads
- Race condition if match completes between alarm set and match call

**Do this instead:** Use Google's RE2 via `re2` library (guaranteed linear time), or pre-analyze pattern for dangerous constructs.

**Reference:** [ReDoS Attacks](https://www.linkedin.com/pulse/redos-attacks-python-application-architectures-akshat-mahajan) - pattern analysis is more reliable than timeouts.

## Integration Points

### Server Integration

```python
# server.py modifications

from workshop_mcp.security import (
    path_validator,
    regex_validator,
    error_sanitizer,
    PathValidationError,
    RegexValidationError
)

class WorkshopMCPServer:
    def __init__(self) -> None:
        self.keyword_search_tool = KeywordSearchTool()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        # Security configuration
        self._allowed_roots = [Path.cwd()]  # configurable

    def _execute_keyword_search(self, request_id, arguments):
        # ... existing type validation ...

        # NEW: Security validation
        try:
            validated_paths = path_validator.validate_paths(
                root_paths, self._allowed_roots
            )
        except PathValidationError as e:
            return self._error_response(request_id,
                JsonRpcError(-32602, str(e)))

        if use_regex:
            try:
                regex_validator.validate_pattern(keyword)
            except RegexValidationError as e:
                return self._error_response(request_id,
                    JsonRpcError(-32602, str(e)))

        # ... rest of execution with validated_paths ...
```

### Error Handler Integration

```python
# Modify existing exception handlers

except (ValueError, FileNotFoundError) as exc:
    return self._error_response(
        request_id,
        JsonRpcError(-32602, error_sanitizer.sanitize(exc)),
    )
except Exception as exc:
    error_id = error_sanitizer.log_and_get_id(exc, logger)
    return self._error_response(
        request_id,
        JsonRpcError(
            -32603,
            "Internal error",
            {"error_id": error_id}  # for log correlation
        ),
    )
```

## Build Order and Dependencies

### Phase 1: Foundation (no dependencies)

| Component | Dependency | Notes |
|-----------|------------|-------|
| `security/exceptions.py` | None | Define exception types first |
| `security/error_sanitizer.py` | `exceptions.py` | Can be integrated immediately |

**Rationale:** Error sanitization can be added to existing exception handlers without changing tool execution flow. Provides immediate security improvement.

### Phase 2: Path Validation (depends on Phase 1)

| Component | Dependency | Notes |
|-----------|------------|-------|
| `security/path_validator.py` | `exceptions.py` | Core validation logic |
| Server integration | `path_validator.py` | Modify `_execute_*` methods |

**Rationale:** Path validation requires exception types. Server integration requires validator. Build validator first, test in isolation, then integrate.

### Phase 3: Regex Validation (depends on Phase 1)

| Component | Dependency | Notes |
|-----------|------------|-------|
| `security/regex_validator.py` | `exceptions.py` | May also require `re2` library |
| Server integration | `regex_validator.py` | Modify `_execute_keyword_search` only |

**Rationale:** Can be built in parallel with Phase 2. Only affects keyword search, not performance check.

### Dependency Graph

```
exceptions.py
     │
     ├──────────────────┬──────────────────┐
     ▼                  ▼                  ▼
error_sanitizer.py  path_validator.py  regex_validator.py
     │                  │                  │
     └──────────────────┴──────────────────┘
                        │
                        ▼
                server.py integration
                        │
                        ▼
                 security tests
```

## Testing Strategy

### Unit Tests (per component)

```
tests/
├── test_security/
│   ├── test_path_validator.py      # Path traversal scenarios
│   ├── test_regex_validator.py     # ReDoS pattern detection
│   └── test_error_sanitizer.py     # Sensitive data stripping
```

### Integration Tests (server level)

```
tests/
├── test_security_integration.py    # End-to-end security scenarios
    ├── test_path_traversal_blocked
    ├── test_redos_pattern_rejected
    └── test_error_details_not_leaked
```

### Security Test Cases

| Test | Purpose | Expected Behavior |
|------|---------|-------------------|
| `../../../etc/passwd` in root_paths | Path traversal | PathValidationError |
| Symlink outside allowed root | Symlink escape | PathValidationError |
| `(a+)+` regex pattern | ReDoS | RegexValidationError |
| Exception with file path | Info disclosure | Path stripped from response |

## Confidence Assessment

| Area | Confidence | Rationale |
|------|------------|-----------|
| Utility module approach | HIGH | Matches existing code style, explicit control flow, standard Python pattern |
| Path validation with pathlib | HIGH | Documented best practice, used in OpenStack/Django security guidelines |
| ReDoS pattern detection | MEDIUM | Heuristic-based detection catches common cases, but RE2 library would be more robust |
| Error sanitization | HIGH | Standard practice, well-documented patterns |
| Build order | HIGH | Clear dependency chain, each phase testable independently |

## Sources

**Path Validation:**
- [OpenStack Security Guidelines - File Paths](https://security.openstack.org/guidelines/dg_using-file-paths.html) - HIGH confidence
- [Preventing Directory Traversal in Python](https://salvatoresecurity.com/preventing-directory-traversal-vulnerabilities-in-python/) - HIGH confidence
- [Guy Rutenberg - Path Traversal Prevention](https://www.guyrutenberg.com/2013/12/06/preventing-directory-traversal-in-python/) - HIGH confidence

**ReDoS Prevention:**
- [ReDoS Attacks in Python](https://www.linkedin.com/pulse/redos-attacks-python-application-architectures-akshat-mahajan) - MEDIUM confidence
- [Regexploit Tool](https://github.com/doyensec/regexploit) - HIGH confidence (tool reference)
- [GuardRails - Insecure Regex](https://docs.guardrails.io/docs/vulnerabilities/python/insecure_use_of_regular_expressions) - MEDIUM confidence

**Error Handling:**
- [Python Security Best Practices](https://corgea.com/Learn/python-security-best-practices-a-comprehensive-guide-for-engineers) - HIGH confidence
- [Sentry - Sensitive Data Scrubbing](https://docs.sentry.io/platforms/python/data-management/sensitive-data/) - HIGH confidence

**Architecture Patterns:**
- [Pydantic Validation Decorator](https://docs.pydantic.dev/latest/concepts/validation_decorator/) - HIGH confidence (evaluated, not recommended)
- [Python Design Patterns](https://python-patterns.guide/gang-of-four/decorator-pattern/) - HIGH confidence

---
*Architecture research for: Python MCP Server Security Hardening*
*Researched: 2026-01-25*
