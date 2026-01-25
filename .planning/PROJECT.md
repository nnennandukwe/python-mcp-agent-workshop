# Python MCP Agent Workshop

## What This Is

An educational MCP server demonstrating AI agent development using the Model Context Protocol. Features keyword search and performance profiler tools with comprehensive security hardening (path validation, ReDoS protection, error sanitization).

## Core Value

Demonstrate how to build secure, production-ready MCP tools from scratch.

## Current State

**v1.0 Security Hardening** — Shipped 2026-01-25

- 2,762 lines of Python
- 270 tests passing
- All Qodo security warnings resolved

## Requirements

### Validated

- ✓ MCP server with JSON-RPC 2.0 protocol — existing
- ✓ Performance profiler with Astroid AST analysis — existing
- ✓ Keyword search with async file traversal — existing
- ✓ Path validation for `file_path` parameters — v1.0
- ✓ ReDoS protection with timeout/safeguards — v1.0
- ✓ Sanitized error responses — v1.0

### Active

(None — run `/gsd:new-milestone` to define next milestone)

### Out of Scope

- Full audit trail logging — trusted local caller only
- Authentication/authorization — trusted local caller only
- Rate limiting — not needed for local-only threat model
- Full sandboxing — overkill for educational workshop

## Context

**v1.0 delivered:** Defense-in-depth security controls across 4 phases:
1. Path traversal prevention (PathValidator with MCP_ALLOWED_ROOTS)
2. ReDoS protection (regex library timeouts, pattern blocklists)
3. Error sanitization (generic messages, correlation IDs)
4. Security exception integration (safe message passthrough)

**Tech stack:** Python 3.10+, Astroid, aiofiles, regex library

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Path allowlist (MCP_ALLOWED_ROOTS) | Simpler than sandbox for trusted local use | ✓ Good |
| regex library with timeout | Library-based timeout is cross-platform | ✓ Good |
| Generic error messages | Prevents information leakage | ✓ Good |
| SecurityValidationError hierarchy | Type-safe error handling | ✓ Good |
| Correlation ID logging | Enables debugging without leaking details | ✓ Good |

---
*Last updated: 2026-01-25 after v1.0 milestone*
