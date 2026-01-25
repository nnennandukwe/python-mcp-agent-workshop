---
phase: 03-error-sanitization
plan: 01
subsystem: logging
tags: [contextvars, logging, correlation-id, uuid, context-manager]

# Dependency graph
requires:
  - phase: none
    provides: standalone module
provides:
  - correlation_id_var ContextVar for request-scoped IDs
  - CorrelationIdFilter for log record enhancement
  - request_context() context manager for scoped logging
affects: [03-02, error-handling, server-logging]

# Tech tracking
tech-stack:
  added: []
  patterns: [ContextVar with token/reset pattern, logging.Filter subclass]

key-files:
  created:
    - src/workshop_mcp/logging_context.py
    - tests/test_logging_context.py
  modified: []

key-decisions:
  - "DEC-03-01-001: Use uuid4().hex[:8] for 8-char correlation IDs"
  - "DEC-03-01-002: Use token/reset pattern for proper ContextVar cleanup"
  - "DEC-03-01-003: Default correlation ID is '-' (not empty string) for log parsing"

patterns-established:
  - "ContextVar with token/reset: Always store set() return and call reset(token) in finally"
  - "Filter always returns True: Adds attributes but never blocks log records"

# Metrics
duration: 2min
completed: 2026-01-25
---

# Phase 3 Plan 01: Logging Context Summary

**Correlation ID management via ContextVar and logging.Filter for request-scoped log tracing using uuid4 hex IDs**

## Performance

- **Duration:** 2 min
- **Started:** 2026-01-25T17:28:56Z
- **Completed:** 2026-01-25T17:31:04Z
- **Tasks:** 3 (TDD: RED, GREEN, REFACTOR)
- **Files modified:** 2

## Accomplishments

- Created correlation_id_var ContextVar with default "-" for non-request contexts
- Implemented CorrelationIdFilter adding correlation_id attribute to all log records
- Built request_context() context manager generating 8-char hex IDs
- Proper context reset on both normal exit and exception (try/finally with token)
- Full test coverage with 15 tests covering all behaviors

## Task Commits

Each TDD phase was committed atomically:

1. **RED: Add failing tests** - `f9a607c` (test)
2. **GREEN: Implement module** - `288fd2c` (feat)
3. **REFACTOR: Fix import sorting** - `4d6a159` (refactor)

## Files Created/Modified

- `src/workshop_mcp/logging_context.py` - Correlation ID ContextVar, Filter, and context manager (89 lines)
- `tests/test_logging_context.py` - Comprehensive tests for all module behaviors (234 lines)

## Decisions Made

1. **DEC-03-01-001:** Use uuid4().hex[:8] for correlation IDs - 8 hex chars provides 4 billion unique IDs, sufficient for request tracing
2. **DEC-03-01-002:** Use token/reset pattern instead of try/finally with direct set - ensures proper restoration in nested contexts
3. **DEC-03-01-003:** Default to "-" rather than empty string - makes log parsing easier (always has a visible value)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - TDD cycle completed smoothly.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- logging_context module ready for integration into server.py error handling
- request_context() can wrap _serve_once() to scope logs to requests
- CorrelationIdFilter can be added to existing logging configuration
- Plan 03-02 can now use correlation IDs in error responses

---
*Phase: 03-error-sanitization*
*Completed: 2026-01-25*
