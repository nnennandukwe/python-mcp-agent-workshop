---
milestone: v1.0
audited: 2026-01-25T19:30:00Z
status: gaps_found
scores:
  requirements: 9/9
  phases: 3/3
  integration: 11/13
  flows: 3/5
gaps:
  requirements: []
  integration:
    - severity: critical
      issue: SecurityValidationError handler missing in tool execution blocks
      affected: RegexValidationError, RegexAbortError
      impact: Return "Internal error" instead of safe descriptive message
  flows:
    - name: ReDoS pattern rejection error message
      status: broken
      reason: RegexValidationError caught by generic Exception handler
    - name: ReDoS abort error message
      status: broken
      reason: RegexAbortError caught by generic Exception handler
tech_debt: []
---

# Milestone Audit Report: Security Hardening v1.0

**Audited:** 2026-01-25T19:30:00Z
**Status:** GAPS FOUND
**Overall:** 9/9 requirements satisfied, but 1 critical integration gap

## Executive Summary

All security protections work correctly - path traversal is blocked, ReDoS patterns are rejected, timeouts prevent DoS, and error messages are sanitized. However, there's a critical integration gap: when `RegexValidationError` or `RegexAbortError` is raised, the error message returned to clients is "Internal error" instead of the safe descriptive message (e.g., "Pattern rejected: nested quantifiers detected").

**Security Impact:** Low (attacks are blocked, protection works)
**UX Impact:** Medium (users see confusing "Internal error" for blocked patterns)
**Fix Effort:** ~15 lines of code

## Requirements Coverage

All 9 v1 requirements are satisfied:

| Requirement | Phase | Status | Evidence |
|-------------|-------|--------|----------|
| PATH-01 | 1 | ✓ Complete | PathValidator uses resolve() + is_relative_to() |
| PATH-02 | 1 | ✓ Complete | Absolute paths outside root rejected |
| PATH-03 | 1 | ✓ Complete | MCP_ALLOWED_ROOTS environment variable |
| REDOS-01 | 2 | ✓ Complete | regex library with timeout=1.0 |
| REDOS-02 | 2 | ✓ Complete | MAX_PATTERN_LENGTH = 500 |
| REDOS-03 | 2 | ✓ Complete | Nested quantifier blocklist |
| ERR-01 | 3 | ✓ Complete | Generic messages for all mapped exceptions |
| ERR-02 | 3 | ✓ Complete | Correlation IDs in all log entries |
| ERR-03 | 3 | ✓ Complete | SecurityValidationError hierarchy |

**Coverage:** 9/9 (100%)

## Phase Verification Summary

| Phase | Goal | Score | Status |
|-------|------|-------|--------|
| 01 Path Validation | Users cannot read files outside allowed directories | 9/9 | ✓ Passed |
| 02 ReDoS Protection | Regex operations cannot cause denial-of-service | 10/10 | ✓ Passed |
| 03 Error Sanitization | Internal implementation details never exposed | 8/8 | ✓ Passed |

**All 3 phases individually verified and passed.**

## Cross-Phase Integration Analysis

### Working Integrations (11/13)

1. **PathValidator → server.py** - ✓ Instantiated, called for both tools
2. **PathValidationError → server.py** - ✓ Caught explicitly, messages pass through
3. **validate_pattern → keyword_search.py** - ✓ Called before regex execution
4. **RegexValidationError → keyword_search.py** - ✓ Imported, raised correctly
5. **RegexAbortError → keyword_search.py** - ✓ Raised when >50% timeout
6. **regex library → keyword_search.py** - ✓ Used with timeout parameter
7. **correlation_id_var → server.py** - ✓ Used in error responses
8. **CorrelationIdFilter → server.py** - ✓ Added to logging handlers
9. **request_context → server.py** - ✓ Wraps entire _serve_once
10. **Generic exception mapping → server.py** - ✓ ValueError, FileNotFoundError, etc.
11. **Parse error sanitization → server.py** - ✓ JSONDecodeError handled

### Gap Found (2/13)

**SecurityValidationError handler missing in tool execution blocks**

- **Current State:** server.py catches `PathValidationError` before tool execution, but `RegexValidationError` and `RegexAbortError` are raised during tool execution and fall through to the generic `except Exception` handler
- **Expected:** All `SecurityValidationError` subclasses should pass through their safe messages
- **Impact:** Users see "Internal error" instead of "Pattern rejected: nested quantifiers detected" or "Pattern timed out on too many files"

**Root Cause:** Exception handling order in `_execute_keyword_search`:
```python
except ValueError as exc: ...
except FileNotFoundError as exc: ...
except KeyError as exc: ...
except Exception as exc:  # ← RegexValidationError caught here
    return JsonRpcError(-32603, "Internal error", ...)
```

**Required Fix:** Add handler before `except Exception`:
```python
except SecurityValidationError as exc:
    logger.warning("Security validation error: %s", exc)
    return JsonRpcError(-32602, str(exc))
```

## E2E Flow Status

| Flow | Status | Notes |
|------|--------|-------|
| Path traversal attack blocked | ✓ Complete | PathValidationError passes through correctly |
| ReDoS pattern blocked | ✗ Broken | Returns "Internal error" instead of rejection message |
| ReDoS timeout abort | ✗ Broken | Returns "Internal error" instead of abort message |
| Normal operation | ✓ Complete | Correlation IDs work, responses correct |
| Non-security exceptions | ✓ Complete | Generic messages work correctly |

## Test Coverage

**Total:** 259 tests passing

| Area | Tests | Passing |
|------|-------|---------|
| Path Validation | 49 | 49 |
| ReDoS Protection | 56 | 56 |
| Error Sanitization | 27 | 27 |
| Other | 127 | 127 |

**Missing Tests:**
- Server-level integration test for RegexValidationError message passthrough
- Server-level integration test for RegexAbortError message passthrough

## Anti-Patterns

None found across all phases. All implementations are clean.

## Tech Debt

None accumulated. All implementations are complete without TODO/FIXME markers.

## Recommendations

### Critical (Fix Before Completion)

1. **Add SecurityValidationError handler in server.py**
   - Location: `_execute_keyword_search` and `_execute_performance_check`
   - Action: Insert handler before generic Exception handler
   - Effort: ~15 lines

2. **Add missing integration tests**
   - Test that RegexValidationError returns -32602 with safe message
   - Test that RegexAbortError returns -32602 with safe message
   - Effort: ~40 lines

### Low Priority (Future Enhancement)

3. Consider using RegexTimeoutError instead of catching TimeoutError directly for consistency

## Conclusion

The milestone achieves its core goal: **security warnings eliminated**. All attack vectors are blocked. However, there's a gap in error message consistency that should be fixed before completion.

**Status:** GAPS FOUND - 1 critical integration issue

---
*Audited: 2026-01-25T19:30:00Z*
*Auditor: Claude (gsd-integration-checker)*
