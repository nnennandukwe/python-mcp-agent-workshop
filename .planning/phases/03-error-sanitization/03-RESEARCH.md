# Phase 3: Error Sanitization - Research

**Researched:** 2026-01-25
**Domain:** Error handling, logging, correlation IDs for JSON-RPC server
**Confidence:** HIGH

## Summary

This research analyzed the current error handling in the MCP server to identify where internal details can leak to clients and how to implement secure error sanitization with correlation ID logging.

The current `server.py` has several locations where exception messages (`str(exc)`) are passed directly to clients. While security exceptions (from Phase 1 and 2) already have generic messages, other exception types like `ValueError`, `FileNotFoundError`, `SyntaxError`, and general `Exception` can leak internal details. The fix requires a centralized error sanitization layer that catches all exceptions, logs full details internally with correlation IDs, and returns only generic messages to clients.

Python's `contextvars` module (stdlib since 3.7) is the standard approach for request-scoped correlation IDs in async/sync code. No external dependencies are needed - the existing `logging` module with a custom `Filter` can inject correlation IDs into all log records.

**Primary recommendation:** Wrap tool execution in a context manager that generates correlation IDs, sets up logging context, and sanitizes all exceptions before they reach the client.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `contextvars` | stdlib | Request-scoped correlation IDs | Built-in, async-safe, no dependencies |
| `logging` | stdlib | Structured internal logging | Already in use, supports custom filters |
| `uuid` | stdlib | Generate unique correlation IDs | Standard UUID4 generation |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `typing` | stdlib | Type hints for error handlers | Type safety |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| contextvars | structlog | structlog adds dependency, more features than needed |
| logging.Filter | structlog.contextvars | Same - structlog is overkill for this use case |

**Installation:**
```bash
# No new dependencies required - all stdlib
```

## Architecture Patterns

### Recommended Project Structure
```
src/workshop_mcp/
├── security/
│   ├── exceptions.py      # Already exists - ERR-03 DONE
│   └── ...
├── server.py              # Add error sanitization here
└── logging_context.py     # NEW: correlation ID management
```

### Pattern 1: Correlation ID Context Manager
**What:** A context manager that generates a correlation ID, sets it in contextvars, and ensures it's included in all logs within that context.
**When to use:** At the entry point of each request (in `_handle_request` or `_serve_once`)
**Example:**
```python
# Source: Python contextvars documentation + best practices
import contextvars
import uuid
import logging
from contextlib import contextmanager

# Module-level ContextVar
correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    'correlation_id', default='-'
)

class CorrelationIdFilter(logging.Filter):
    """Injects correlation_id into log records."""
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_var.get()
        return True

@contextmanager
def request_context():
    """Context manager that sets up correlation ID for a request."""
    request_id = str(uuid.uuid4())[:8]  # Short ID for readability
    token = correlation_id_var.set(request_id)
    try:
        yield request_id
    finally:
        correlation_id_var.reset(token)
```

### Pattern 2: Centralized Error Sanitization
**What:** A single function that converts any exception to a safe JSON-RPC error response
**When to use:** As the final catch-all around tool execution
**Example:**
```python
# Source: JSON-RPC 2.0 specification + security best practices
from workshop_mcp.security import SecurityValidationError

def sanitize_error(exc: Exception, correlation_id: str) -> JsonRpcError:
    """Convert any exception to a safe client-facing error.

    Logs full details internally, returns generic message to client.
    """
    # Security exceptions already have safe messages
    if isinstance(exc, SecurityValidationError):
        logger.warning(
            "Security validation failed",
            extra={"correlation_id": correlation_id, "error_type": type(exc).__name__}
        )
        return JsonRpcError(-32602, str(exc))

    # Known recoverable errors - log at warning, generic message
    if isinstance(exc, (ValueError, TypeError)):
        logger.warning(
            "Parameter validation error: %s",
            str(exc),
            extra={"correlation_id": correlation_id}
        )
        return JsonRpcError(-32602, "Invalid parameters")

    if isinstance(exc, FileNotFoundError):
        logger.warning(
            "Resource not found: %s",
            str(exc),
            extra={"correlation_id": correlation_id}
        )
        return JsonRpcError(-32602, "Resource not found")

    if isinstance(exc, SyntaxError):
        logger.warning(
            "Code parsing error: %s",
            str(exc),
            extra={"correlation_id": correlation_id}
        )
        return JsonRpcError(-32602, "Invalid source code syntax")

    # Unknown errors - log full traceback at error level
    logger.exception(
        "Unexpected error (correlation_id=%s)",
        correlation_id
    )
    return JsonRpcError(
        -32603,
        "Internal error",
        {"correlation_id": correlation_id}  # Include ID for client debugging
    )
```

### Pattern 3: JSON-RPC Error Response Format
**What:** Standard JSON-RPC 2.0 error structure
**When to use:** All error responses
**Example:**
```python
# Source: https://www.jsonrpc.org/specification
{
    "jsonrpc": "2.0",
    "id": "request-id",
    "error": {
        "code": -32603,          # Standard error code
        "message": "Internal error",  # Generic, safe message
        "data": {                # Optional - safe metadata only
            "correlation_id": "a1b2c3d4"
        }
    }
}
```

### Anti-Patterns to Avoid
- **Passing `str(exc)` to client:** Exception messages can contain paths, versions, internals
- **Including exception type name:** `ValueError: /etc/passwd not found` leaks info
- **Stack traces in response:** Never include tracebacks in client responses
- **Detailed error data:** Never put file paths, SQL queries, or config in error.data

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Request-scoped context | Thread-local dict | `contextvars.ContextVar` | Async-safe, stdlib |
| Unique IDs | Random strings | `uuid.uuid4()` | Cryptographically random |
| Log filtering | Manual injection | `logging.Filter` | Integrates with all loggers |
| JSON-RPC errors | Ad-hoc dicts | Standard error codes | Spec compliance |

**Key insight:** The stdlib provides everything needed for this phase. Adding structlog or other dependencies would increase complexity without proportional benefit.

## Common Pitfalls

### Pitfall 1: Leaking via Exception Chaining
**What goes wrong:** Python's `raise ... from exc` preserves the original exception, which can leak in tracebacks
**Why it happens:** Exception chaining is useful for debugging but the chain may contain sensitive details
**How to avoid:** Log the chain internally, never serialize it to client response
**Warning signs:** `__cause__` or `__context__` appearing in error responses

### Pitfall 2: Inconsistent Error Handling Paths
**What goes wrong:** Some code paths sanitize errors, others don't
**Why it happens:** Multiple `except` blocks across different methods
**How to avoid:** Centralize all error handling in one location
**Warning signs:** `str(exc)` appearing in multiple `except` blocks throughout server.py

### Pitfall 3: Forgetting to Log Before Sanitizing
**What goes wrong:** Errors are sanitized but full details never logged - debugging impossible
**Why it happens:** Rushing to fix the "leak" without preserving diagnostic info
**How to avoid:** Always log FIRST (with correlation ID), THEN sanitize for client
**Warning signs:** Production issues with no corresponding log entries

### Pitfall 4: Correlation ID Not Reaching Logs
**What goes wrong:** Correlation ID generated but not appearing in log output
**Why it happens:** Filter not added to handler, or format string missing `%(correlation_id)s`
**How to avoid:** Configure logging early, verify with test log output
**Warning signs:** Logs without correlation_id field despite context being set

### Pitfall 5: ContextVar Leakage Between Requests
**What goes wrong:** Correlation ID from previous request appears in current request's logs
**Why it happens:** Not resetting ContextVar after request completes
**How to avoid:** Use context manager pattern with `reset(token)` in finally block
**Warning signs:** Duplicate correlation IDs across different requests

## Code Examples

Verified patterns from official sources:

### Setting Up Logging with Correlation IDs
```python
# Source: Python logging documentation + contextvars docs
import logging
import contextvars

correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    'correlation_id', default='-'
)

class CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_var.get()
        return True

# Configure at module load
def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.addFilter(CorrelationIdFilter())
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s'
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger('workshop_mcp')
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
```

### Current Exception Leak Points (to fix)
```python
# CURRENT (LEAKS) - server.py line 101
JsonRpcError(-32603, "Internal error", {"details": str(exc)})

# CURRENT (LEAKS) - server.py line 138
JsonRpcError(-32700, "Parse error", {"details": str(exc)})

# CURRENT (LEAKS) - server.py line 330
JsonRpcError(-32602, "Missing required argument", {"missing": str(exc)})

# CURRENT (LEAKS) - server.py lines 416, 523
JsonRpcError(-32602, str(exc))  # ValueError, FileNotFoundError, SyntaxError

# FIXED versions:
JsonRpcError(-32603, "Internal error", {"correlation_id": correlation_id})
JsonRpcError(-32700, "Parse error")  # No details
JsonRpcError(-32602, "Missing required argument")  # No specifics
JsonRpcError(-32602, "Invalid parameters")  # Generic
```

### Complete Error Sanitization Wrapper
```python
# Source: Best practices synthesis
from contextlib import contextmanager
from typing import Generator, Any
import uuid

@contextmanager
def request_context() -> Generator[str, None, None]:
    """Sets up correlation ID context for a request."""
    request_id = uuid.uuid4().hex[:8]
    token = correlation_id_var.set(request_id)
    try:
        yield request_id
    finally:
        correlation_id_var.reset(token)

def execute_tool_safely(
    self,
    request_id: Any,
    tool_name: str,
    arguments: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute a tool with full error sanitization."""
    with request_context() as correlation_id:
        try:
            if tool_name == "keyword_search":
                return self._execute_keyword_search_impl(request_id, arguments)
            elif tool_name == "performance_check":
                return self._execute_performance_check_impl(request_id, arguments)
            else:
                return self._error_response(
                    request_id,
                    JsonRpcError(-32602, "Unknown tool"),
                )
        except SecurityValidationError as e:
            # Security exceptions have safe messages
            logger.warning(
                "Security validation failed: %s",
                str(e),
            )
            return self._error_response(
                request_id,
                JsonRpcError(-32602, str(e)),
            )
        except (ValueError, TypeError) as e:
            logger.warning("Parameter error: %s", str(e))
            return self._error_response(
                request_id,
                JsonRpcError(-32602, "Invalid parameters"),
            )
        except FileNotFoundError as e:
            logger.warning("Resource not found: %s", str(e))
            return self._error_response(
                request_id,
                JsonRpcError(-32602, "Resource not found"),
            )
        except SyntaxError as e:
            logger.warning("Syntax error in source: %s", str(e))
            return self._error_response(
                request_id,
                JsonRpcError(-32602, "Invalid source code syntax"),
            )
        except Exception:
            logger.exception("Unexpected error")
            return self._error_response(
                request_id,
                JsonRpcError(
                    -32603,
                    "Internal error",
                    {"correlation_id": correlation_id},
                ),
            )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| thread-local | contextvars | Python 3.7 (2018) | Async-safe context |
| str(exc) in response | Generic messages only | Security best practice | Prevents info leakage |
| No correlation | Correlation IDs | Distributed systems era | Enables request tracing |

**Deprecated/outdated:**
- `threading.local()` for context: Use `contextvars` instead (async-safe)
- Detailed error messages to clients: Security risk, use generic messages

## Open Questions

Things that couldn't be fully resolved:

1. **Log format for production**
   - What we know: JSON logging is standard for production, plain text for development
   - What's unclear: Whether to add JSON formatter now or defer
   - Recommendation: Use plain text with correlation ID for now; JSON can be added later

2. **Correlation ID length**
   - What we know: Full UUID is 36 chars, short (8 chars) is more readable
   - What's unclear: Whether 8 chars is sufficient uniqueness
   - Recommendation: Use 8 chars (hex[:8]) - provides 4 billion unique IDs, sufficient for debugging

## Sources

### Primary (HIGH confidence)
- [Python contextvars documentation](https://docs.python.org/3/library/contextvars.html) - ContextVar API, async behavior
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification) - Error codes, response format
- Codebase analysis of `server.py`, `security/exceptions.py` - Current implementation

### Secondary (MEDIUM confidence)
- [Python Logging Best Practices Complete Guide 2026](https://www.carmatec.com/blog/python-logging-best-practices-complete-guide/) - Logging configuration patterns
- [Correlation IDs in Python](https://medium.com/@ThinkingLoop/10-advanced-logging-correlation-trace-ids-in-python-50bff4024344) - ContextVar with logging filter pattern
- [JSON-RPC Error Codes Reference](https://json-rpc.dev/docs/reference/error-codes) - Error code usage

### Tertiary (LOW confidence)
- None - all findings verified with primary sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - stdlib only, verified with official docs
- Architecture: HIGH - patterns verified with Python docs and JSON-RPC spec
- Pitfalls: HIGH - derived from codebase analysis and established best practices

**Research date:** 2026-01-25
**Valid until:** 60 days (stable domain, stdlib-based)
