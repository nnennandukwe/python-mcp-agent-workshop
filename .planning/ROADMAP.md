# Roadmap: Security Hardening

## Overview

This security hardening milestone eliminates Qodo code review warnings by implementing defense-in-depth security controls. The journey progresses from path validation (highest-impact vulnerability prevention) through ReDoS protection (denial-of-service prevention) to error sanitization (information disclosure prevention). Each phase builds on a shared security module foundation, with Phase 1 establishing the exception hierarchy used by subsequent phases.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [ ] **Phase 1: Path Validation** - Prevent arbitrary file read via path traversal
- [ ] **Phase 2: ReDoS Protection** - Prevent regex denial-of-service attacks
- [ ] **Phase 3: Error Sanitization** - Prevent information disclosure via error messages

## Phase Details

### Phase 1: Path Validation
**Goal**: Users cannot read files outside allowed directories
**Depends on**: Nothing (first phase)
**Requirements**: PATH-01, PATH-02, PATH-03
**Success Criteria** (what must be TRUE):
  1. File operations reject paths containing `../` traversal sequences
  2. File operations reject absolute paths outside the allowed root
  3. Allowed root directory is configurable via environment variable
  4. Rejected paths return a generic error (no path details leaked)
**Plans**: 2 plans

Plans:
- [ ] 01-01-PLAN.md — PathValidator security module with TDD (exceptions, validation, tests)
- [ ] 01-02-PLAN.md — Server integration (wire PathValidator into MCP server)

### Phase 2: ReDoS Protection
**Goal**: Regex operations cannot cause denial-of-service
**Depends on**: Phase 1 (uses security exceptions)
**Requirements**: REDOS-01, REDOS-02, REDOS-03
**Success Criteria** (what must be TRUE):
  1. Regex operations timeout after configurable limit (default 1 second)
  2. Patterns exceeding length limit are rejected before execution
  3. Known ReDoS patterns (nested quantifiers, catastrophic backtracking) are blocked
  4. Blocked/timed-out patterns return a generic error (no pattern details leaked)
**Plans**: TBD

Plans:
- [ ] 02-01: TBD

### Phase 3: Error Sanitization
**Goal**: Internal implementation details are never exposed to clients
**Depends on**: Phase 1 (uses security exceptions)
**Requirements**: ERR-01, ERR-02, ERR-03
**Success Criteria** (what must be TRUE):
  1. Client-facing errors contain only generic messages (no exception type/message)
  2. Full error details are logged internally with correlation IDs
  3. Security-specific exceptions provide typed error handling
  4. No stack traces, file paths, or library versions appear in responses
**Plans**: TBD

Plans:
- [ ] 03-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Path Validation | 0/2 | Planned | - |
| 2. ReDoS Protection | 0/TBD | Not started | - |
| 3. Error Sanitization | 0/TBD | Not started | - |

---
*Roadmap created: 2026-01-25*
*Phase 1 planned: 2026-01-25*
*Coverage: 9/9 v1 requirements mapped*
