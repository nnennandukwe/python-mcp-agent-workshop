---
phase: 03-error-sanitization
plan: 02
subsystem: api
tags: [error-handling, security, correlation-id, logging, json-rpc]

# Dependency graph
requires:
  - phase: 03-01
    provides: CorrelationIdFilter, request_context, correlation_id_var
provides:
  - Sanitized error handling in MCP server
  - Generic error messages for all exception types
  - Correlation ID tracking for internal errors
  - Full error logging for debugging
affects: [future error handling, logging, debugging]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Generic error message pattern: map exception type to safe message"
    - "Correlation ID pattern: request_context() wraps request handling"
    - "Error logging pattern: log full details, return generic message"

key-files:
  created:
    - tests/test_error_sanitization.py
  modified:
    - src/workshop_mcp/server.py

key-decisions:
  - "DEC-03-02-001: Map exception types to fixed generic messages"
  - "DEC-03-02-002: Wrap entire _serve_once in request_context() for correlation"
  - "DEC-03-02-003: Log full exception details at WARNING level before sanitizing"

patterns-established:
  - "Error sanitization: ValueError -> 'Invalid parameters', FileNotFoundError -> 'Resource not found', SyntaxError -> 'Invalid source code syntax', KeyError -> 'Missing required argument'"
  - "Internal error response: include correlation_id in data field for log correlation"
  - "Parse error: no data field, just 'Parse error' message"

# Metrics
duration: 3min
completed: 2026-01-25
---

# Phase 03 Plan 02: Error Sanitization Integration Summary

**Fixed all 6 exception leak points in MCP server with generic error messages and correlation ID tracking for debugging**

## Performance

- **Duration:** 3 min
- **Started:** 2026-01-25T17:33:10Z
- **Completed:** 2026-01-25T17:36:30Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- All error responses now return generic messages without internal details
- ValueError, FileNotFoundError, SyntaxError, KeyError all mapped to safe messages
- Parse errors no longer expose JSON decode details
- Internal errors include correlation_id for log correlation
- Full exception details logged with correlation ID for debugging
- 12 comprehensive tests covering all sanitization scenarios

## Task Commits

Each task was committed atomically:

1. **Task 1: Create error sanitization tests** - `08cead5` (test)
2. **Task 2: Configure logging with correlation ID filter** - `65a4a7d` (feat)
3. **Task 3: Fix all exception leak points** - `421f795` (fix)

## Files Created/Modified

- `tests/test_error_sanitization.py` - 505 lines of tests covering all error sanitization scenarios
- `src/workshop_mcp/server.py` - Updated with logging imports, request_context wrapper, and sanitized error handling

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| DEC-03-02-001 | Map exception types to fixed generic messages | Ensures no internal details leak regardless of exception content |
| DEC-03-02-002 | Wrap entire _serve_once in request_context() | Provides correlation ID for all errors including parse and loop errors |
| DEC-03-02-003 | Log full exception details at WARNING level | Enables debugging while keeping responses safe |

## Exception Mapping

| Exception Type | Generic Message | Code |
|---------------|-----------------|------|
| ValueError | "Invalid parameters" | -32602 |
| FileNotFoundError | "Resource not found" | -32602 |
| SyntaxError | "Invalid source code syntax" | -32602 |
| KeyError | "Missing required argument" | -32602 |
| JSONDecodeError | "Parse error" | -32700 |
| Other exceptions | "Internal error" + correlation_id | -32603 |
| SecurityValidationError | Pass through (already safe) | -32602 |

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Pre-existing mypy error in server.py (json.loads returns Any) - not introduced by this plan, documented but not fixed as out of scope

## Test Coverage

All 12 new tests pass, verifying:
- ValueError returns "Invalid parameters" not str(exc)
- FileNotFoundError returns "Resource not found" not path
- SyntaxError returns "Invalid source code syntax" not details
- KeyError returns "Missing required argument" not key name
- Parse errors return "Parse error" without JSON details
- Internal errors have correlation_id but not exception message
- SecurityValidationError messages pass through unchanged
- Correlation ID appears in logs for debugging

## Next Phase Readiness

- Error sanitization complete
- All 259 project tests pass
- Phase 03 (Error Sanitization) complete
- Ready for project completion

---
*Phase: 03-error-sanitization*
*Completed: 2026-01-25*
