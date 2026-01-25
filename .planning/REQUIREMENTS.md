# Requirements: Security Hardening

**Defined:** 2026-01-25
**Core Value:** Eliminate security warnings from Qodo reviews by implementing proper input validation, safe error handling, and regex protection.

## v1 Requirements

Requirements for this security hardening milestone. Each maps to roadmap phases.

### Path Validation

- [ ] **PATH-01**: Validate file_path parameter is within allowed directory using pathlib.resolve() + is_relative_to()
- [ ] **PATH-02**: Block absolute paths that escape the root directory
- [ ] **PATH-03**: Configurable allowed roots via environment variable

### ReDoS Protection

- [ ] **REDOS-01**: Timeout on regex operations using `regex` library as drop-in replacement for `re`
- [ ] **REDOS-02**: Input length limits on regex patterns and search content
- [ ] **REDOS-03**: Enhanced pattern blocklist beyond current checks (catch .*.*  and other patterns)

### Error Sanitization

- [ ] **ERR-01**: Generic error messages to clients (no exception type/message leaked)
- [ ] **ERR-02**: Log full error details internally with correlation IDs for debugging
- [ ] **ERR-03**: Security-specific exception hierarchy (PathValidationError, RegexValidationError, etc.)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Enhanced Security

- **SEC-01**: Security logging with audit trail
- **SEC-02**: Structured error codes for client debugging
- **SEC-03**: Pydantic input schema validation

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Authentication/authorization | Trusted local caller only (Claude Code, Cursor) |
| Rate limiting | Not needed for local-only threat model |
| Full sandboxing | Overkill for educational workshop project |
| Dependency vulnerability scanning | Separate CI concern, not code change |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PATH-01 | Phase 1 | Pending |
| PATH-02 | Phase 1 | Pending |
| PATH-03 | Phase 1 | Pending |
| REDOS-01 | Phase 2 | Pending |
| REDOS-02 | Phase 2 | Pending |
| REDOS-03 | Phase 2 | Pending |
| ERR-01 | Phase 3 | Pending |
| ERR-02 | Phase 3 | Pending |
| ERR-03 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 9 total
- Mapped to phases: 9
- Unmapped: 0

---
*Requirements defined: 2026-01-25*
*Last updated: 2026-01-25 after roadmap creation*
