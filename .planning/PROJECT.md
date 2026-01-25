# Security Hardening

## What This Is

Security improvements to the Python MCP Agent Workshop codebase, targeting the critical issues consistently flagged by Qodo code review across recent PRs. This is a focused cleanup milestone to establish secure-by-default patterns.

## Core Value

Eliminate security warnings from Qodo reviews by implementing proper input validation, safe error handling, and regex protection.

## Requirements

### Validated

- ✓ MCP server with JSON-RPC 2.0 protocol — existing
- ✓ Performance profiler with Astroid AST analysis — existing
- ✓ Keyword search with async file traversal — existing
- ✓ 102 passing tests with comprehensive coverage — existing

### Active

- [ ] Path validation for `file_path` parameters (prevent arbitrary file read)
- [ ] ReDoS protection with timeout/safeguards for user-supplied regex
- [ ] Sanitized error responses (no internal exception details leaked)

### Out of Scope

- Full audit trail logging — trusted local caller only, adds complexity beyond current need
- Security test suite expansion — focus on fixes first, tests follow naturally
- Dependency vulnerability scanning — separate CI concern, not code change

## Context

**Trigger:** Qodo code review bot consistently flags security compliance issues across PRs 17-22:
- PR 17: Regex DoS risk in keyword search
- PR 19: Arbitrary file read, sensitive data exposure in code snippets
- PR 20: Arbitrary file read, internal error details exposed, incomplete audit logging
- PR 22: Local file disclosure, missing type validation

**Threat model:** Trusted local callers only (Claude Code, Cursor, etc.). Security hardening is defense-in-depth and establishes good patterns.

**Codebase analysis:** `.planning/codebase/CONCERNS.md` already identified these exact issues:
- "Insufficient Regex ReDoS Protection" (lines 134-150)
- "No Input Validation on Paths" (lines 316-324)
- "Incomplete Error Messages" (lines 271-288)

## Constraints

- **Tech stack**: Python 3.10+, existing Astroid/aiofiles dependencies
- **Scope**: Fix Qodo-flagged issues only, no feature additions
- **Testing**: Maintain 102+ passing tests, add targeted security tests

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Path allowlist vs. sandbox | Allowlist is simpler for trusted local use case | — Pending |
| Regex timeout mechanism | signal-based vs. library-based | — Pending |
| Error sanitization approach | Generic message vs. error codes | — Pending |

---
*Last updated: 2026-01-25 after initialization*
