# Feature Research: Python MCP Server Security Hardening

**Domain:** MCP Server Security (Python, Local/Trusted Callers)
**Researched:** 2026-01-25
**Confidence:** HIGH (based on official MCP docs, OWASP, OpenStack guidelines)

## Context

This MCP server runs locally, serving trusted callers (Claude Code, Cursor). The threat model is:
- **NOT** exposed to the internet
- **NOT** handling untrusted user input directly
- Callers are AI coding assistants that pass file paths and regex patterns

The goal is to eliminate security warnings from Qodo code reviews while maintaining educational value for workshop participants.

## Feature Landscape

### Table Stakes (Users Expect These)

Features that Qodo and static analyzers will flag if missing. These are non-negotiable for passing code review.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Path Traversal Prevention** | Qodo flags any file_path parameter without validation; OWASP Top 10 | LOW | Use `pathlib.resolve()` + `is_relative_to()` pattern |
| **Safe Error Messages** | Exception details leak internal paths, versions, stack traces | LOW | Generic user messages, detailed server-side logging |
| **Input Type Validation** | Already partially implemented; completeness matters | LOW | Ensure all parameters validated before use |
| **ReDoS Protection (Complete)** | Current check is incomplete; dangerous patterns still pass | MEDIUM | Either block user regex entirely OR use proper detection |

### Differentiators (Competitive Advantage)

Features that add educational value for workshop participants. Not required to pass Qodo, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Allowlisted Directories** | Demonstrates MCP "roots" concept from spec | LOW | Config-based directory allowlist |
| **Timeout for Regex Operations** | Demonstrates defense-in-depth | MEDIUM | Use `signal` or thread-based timeout |
| **Structured Error Codes** | Workshop teaches JSON-RPC properly | LOW | Consistent error code taxonomy |
| **Security Logging** | Educational: shows audit trail pattern | LOW | Log rejected paths, failed validations |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but add complexity without benefit for this scope.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Full Sandboxing** | Maximum security | Overkill for trusted local callers; complex to implement | Allowlist directories instead |
| **RE2 Regex Engine** | Prevents ReDoS entirely | Requires C library dependency; complicates workshop setup | Timeout + pattern rejection |
| **OAuth/Token Auth** | MCP spec supports it | Adds significant complexity; local servers don't need it | Rely on local process isolation |
| **Rate Limiting** | Prevents abuse | Local callers are trusted; adds unnecessary complexity | Not needed for this scope |
| **Request Signing** | Tamper prevention | stdio transport is process-local; signing adds no security | Use stdio transport isolation |

## Feature Dependencies

```
[Path Validation]
    └── required for ──> [Safe Error Messages]
                              └── errors should not reveal validated paths

[Input Type Validation]
    └── required before ──> [ReDoS Protection]
                              └── must confirm string before regex check

[Allowlisted Directories]
    └── enhances ──> [Path Validation]
                        └── validation checks against allowlist
```

### Dependency Notes

- **Path Validation requires Safe Error Messages:** If path validation fails, the error must not reveal the invalid path attempt
- **Input Type Validation before ReDoS Protection:** Can't check regex safety on non-string input
- **Allowlisted Directories enhances Path Validation:** Allowlist is an additional constraint on top of traversal prevention

## Implementation Priority

### Launch With (v1 - Security Hardening MVP)

Minimum to eliminate Qodo warnings.

- [x] **Path Traversal Prevention** — Direct Qodo flag, pattern is simple
- [x] **Safe Error Messages** — Direct Qodo flag, prevents info leakage
- [x] **Complete ReDoS Protection** — Current implementation is incomplete

### Add After Validation (v1.x)

Features to add once core security is working.

- [ ] **Allowlisted Directories** — When users want to restrict search scope
- [ ] **Security Logging** — When debugging/auditing is needed
- [ ] **Regex Timeout** — Defense-in-depth if ReDoS protection proves insufficient

### Future Consideration (v2+)

Features to defer until there's a clear need.

- [ ] **Sandboxing** — Only if server is exposed beyond local process
- [ ] **RE2 Engine** — Only if regex timeout proves inadequate
- [ ] **Authentication** — Only if server moves to HTTP transport

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Qodo Fix? | Priority |
|---------|------------|---------------------|-----------|----------|
| Path Traversal Prevention | HIGH | LOW | YES | P1 |
| Safe Error Messages | HIGH | LOW | YES | P1 |
| Complete ReDoS Protection | HIGH | MEDIUM | YES | P1 |
| Input Type Validation | MEDIUM | LOW | Partial | P1 |
| Allowlisted Directories | MEDIUM | LOW | NO | P2 |
| Structured Error Codes | LOW | LOW | NO | P2 |
| Security Logging | LOW | LOW | NO | P3 |
| Regex Timeout | MEDIUM | MEDIUM | NO | P3 |

**Priority key:**
- P1: Must have for security hardening milestone (Qodo warnings)
- P2: Should have, adds educational value
- P3: Nice to have, defer unless needed

## Detailed Implementation Guidance

### Path Traversal Prevention (P1)

**Pattern from OpenStack Security Guidelines:**

```python
from pathlib import Path

def validate_path(file_path: str, allowed_base: Path) -> Path:
    """Validate file path is within allowed directory."""
    resolved = Path(file_path).resolve()

    if not resolved.is_relative_to(allowed_base.resolve()):
        raise ValueError("Access denied: path outside allowed directory")

    if not resolved.exists():
        raise FileNotFoundError("File not found")

    return resolved
```

**Key points:**
- Use `pathlib.Path.resolve()` to canonicalize (handles `..`, symlinks)
- Use `is_relative_to()` (Python 3.9+) to check containment
- Do NOT use string `startswith()` — fails on `/var/www` vs `/var/www-admin`

**Current gap in codebase:**
- `performance_check` tool accepts `file_path` without any validation
- `keyword_search` validates paths exist but doesn't check containment

### Safe Error Messages (P1)

**Current problem in server.py:**

```python
# Lines 407-416 - keyword_search error handling
except Exception as exc:
    logger.exception("Error executing keyword_search")
    return self._error_response(
        request_id,
        JsonRpcError(
            -32603,
            "Internal error",
            {"details": "An unexpected error occurred. Check server logs for details."},
        ),
    )
```

This is already partially correct (generic message). But other places may leak:

```python
# Line 136 - parse error leaks JSON details
raise JsonRpcError(-32700, "Parse error", {"details": str(exc)})
```

**Pattern:**
- User-facing: Generic message like "Invalid request"
- Server-side: Full exception with `logger.exception()` or `logger.error()`

### Complete ReDoS Protection (P1)

**Current implementation (keyword_search.py lines 324-340):**

```python
dangerous_patterns = [
    r'\([^)]*[+*][^)]*\)[+*]',  # Nested quantifiers like (a+)+
    r'\([^)]*\|[^)]*\)[+*]',     # Alternation with quantifier like (a|b)+
]
```

**Gaps:**
- Does not catch `.*.*` or `\s*\s*` patterns
- Does not catch quantified backreferences
- Does not enforce input length limits

**Recommended approach:**
1. Add more dangerous patterns to check
2. Enforce maximum regex length (e.g., 1000 chars)
3. Consider adding timeout as defense-in-depth

## Security Standards Referenced

### OWASP Guidelines

- [Path Traversal Prevention](https://owasp.org/www-community/attacks/Path_Traversal)
- [ReDoS Prevention](https://owasp.org/www-community/attacks/Regular_expression_Denial_of_Service_-_ReDoS)
- Input Validation

### MCP Security Best Practices

From [MCP Security Best Practices](https://modelcontextprotocol.io/specification/draft/basic/security_best_practices):

> "Apply resource limits and sandboxing. The MCP server should enforce limits on what the AI can do — e.g., the maximum file size it can read, or CPU time for an execution tool."

> "Roots are a standardized way for clients to expose filesystem boundaries to servers."

### Python-Specific Patterns

From [OpenStack Security Guidelines](https://security.openstack.org/guidelines/dg_using-file-paths.html):

```python
def is_safe_path(basedir, path, follow_symlinks=True):
    if follow_symlinks:
        matchpath = os.path.realpath(path)
    else:
        matchpath = os.path.abspath(path)
    return basedir == os.path.commonpath((basedir, matchpath))
```

## Qodo-Specific Concerns

Based on research, Qodo flags:
- Hardcoded secrets (not applicable here)
- Unsafe input handling (applicable: path, regex)
- Insecure defaults (check: are defaults secure?)
- Unhandled errors (check: all exceptions caught?)
- Information leakage (applicable: error messages)

**Qodo severity levels:**
- Critical: Must fix before merge
- High: Should fix
- Medium: Consider fixing
- Low: Informational

Path traversal and info leakage typically flagged as HIGH or CRITICAL.

## Sources

### Official Documentation
- [MCP Security Best Practices](https://modelcontextprotocol.io/specification/draft/basic/security_best_practices) - HIGH confidence
- [OpenStack Path Traversal Guidelines](https://security.openstack.org/guidelines/dg_using-file-paths.html) - HIGH confidence
- [OWASP ReDoS](https://owasp.org/www-community/attacks/Regular_expression_Denial_of_Service_-_ReDoS) - HIGH confidence

### Security Research
- [Path Traversal Prevention in Python](https://salvatoresecurity.com/preventing-directory-traversal-vulnerabilities-in-python/) - MEDIUM confidence
- [Qodo Code Review Capabilities](https://www.qodo.ai/blog/compliance-in-code-reviews-automating-security-standards-and-ticket-checks/) - MEDIUM confidence
- [Python Security Best Practices](https://corgea.com/Learn/python-security-best-practices-a-comprehensive-guide-for-engineers) - MEDIUM confidence

### Error Handling
- [Information Leakage via Error Messages](https://cqr.company/web-vulnerabilities/information-leakage-via-error-messages/) - MEDIUM confidence
- [Fixing Error Handling](https://qwiet.ai/fixing-error-handling-avoiding-information-leakage-in-your-web-app/) - MEDIUM confidence

---
*Feature research for: Python MCP Server Security Hardening*
*Researched: 2026-01-25*
