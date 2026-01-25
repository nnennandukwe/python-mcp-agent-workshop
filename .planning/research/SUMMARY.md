# Project Research Summary

**Project:** Security Hardening
**Domain:** Python MCP Server Security (Input Validation, ReDoS Protection, Error Sanitization)
**Researched:** 2026-01-25
**Confidence:** HIGH

## Executive Summary

The Python MCP Agent Workshop requires security hardening to address recurring Qodo code review warnings across path traversal, ReDoS vulnerabilities, and information disclosure through error messages. Research reveals that the solution is straightforward: use Python stdlib path validation (no new dependencies), add the `regex` library for timeout-protected pattern matching, and implement a custom exception wrapper pattern for safe error messages.

The recommended approach follows defense-in-depth principles with a dedicated security validation module that sits between the MCP server's tool dispatch layer and business logic. This provides centralized security policy, testable isolation, and clear audit trails without disrupting existing tool implementations. The key architectural insight is that security validation belongs at the earliest possible point in the request flow—before any tool execution begins—not scattered across tool implementations.

The most critical pitfall to avoid is the `os.path.join()` absolute path injection vulnerability, where user-supplied absolute paths bypass the intended base directory entirely. This has led to numerous real-world CVEs and must be prevented using `pathlib.Path.resolve()` + `is_relative_to()` validation. The second major risk is incomplete ReDoS protection: the current blocklist approach catches some patterns but is fundamentally incomplete. Adding timeout protection via the `regex` library provides defense-in-depth that's missing today.

## Key Findings

### Recommended Stack

The research identified minimal-dependency solutions that leverage Python stdlib wherever possible while adding only one critical library for ReDoS protection.

**Core technologies:**
- **Python stdlib `pathlib`**: Path traversal prevention using `resolve()` + `is_relative_to()` — Zero dependencies, battle-tested, handles symlinks and canonicalization correctly
- **`regex` library (mrab-regex) ^2026.1.15**: ReDoS protection with native timeout parameter — Drop-in `re` replacement that raises `TimeoutError` when regex operations exceed configured time limit
- **Custom exception wrappers**: Safe error message pattern — No new dependencies, separates public messages from internal logging, designed to be safe-by-default

**Supporting libraries (optional):**
- **Pydantic ^2.12.5**: Schema validation for MCP tool inputs (defense-in-depth, not required to fix Qodo warnings)
- **Bandit ^1.9.3**: Security linter for CI integration (development tool, catches future issues)

**Version compatibility:** All recommendations compatible with Python 3.10+ (current project requirement). The `pathlib.is_relative_to()` method was added in Python 3.9, making it available for use without compatibility concerns.

### Expected Features

Research confirmed that Qodo and static analyzers flag specific security controls as table stakes for any production codebase handling file paths or regex patterns.

**Must have (table stakes):**
- **Path Traversal Prevention** — Qodo will flag any file_path parameter without validation; OWASP Top 10 issue
- **Safe Error Messages** — Exception details leak internal paths, versions, stack traces to callers
- **Complete ReDoS Protection** — Current blocklist approach is incomplete; patterns can slip through
- **Input Type Validation** — Already partially implemented; completeness matters for security

**Should have (educational value):**
- **Allowlisted Directories** — Demonstrates MCP "roots" concept from specification
- **Timeout for Regex Operations** — Shows defense-in-depth beyond pattern detection
- **Structured Error Codes** — Workshop teaches JSON-RPC properly with consistent error taxonomy
- **Security Logging** — Educational pattern showing audit trail (who requested what path)

**Defer (v2+):**
- **Full Sandboxing** — Overkill for trusted local callers; complex to implement
- **RE2 Regex Engine** — Requires C library dependency; timeout approach is sufficient
- **OAuth/Token Auth** — Local servers don't need authentication complexity
- **Rate Limiting** — Not needed for trusted local process communication

### Architecture Approach

The research strongly recommends a **utility module with explicit calls** over decorator patterns or middleware approaches. Security validation should be explicit and visible in code reviews, not hidden behind decorator magic. Different tools need different validation (keyword search validates paths AND regex; performance check validates paths only), making decorators inflexible.

**Major components:**
1. **`security/path_validator.py`** — Validates file paths stay within allowed boundaries using allowlist pattern; called by server before tool execution
2. **`security/regex_validator.py`** — Validates regex patterns for ReDoS safety using blocklist + timeout; called by server before passing to KeywordSearchTool
3. **`security/error_sanitizer.py`** — Strips sensitive details from exceptions; called by server in all exception handlers
4. **`security/exceptions.py`** — Typed security exceptions (PathValidationError, RegexValidationError) with safe-by-default messages

**Integration points:** The MCP server's `_execute_keyword_search()` and `_execute_performance_check()` methods gain security validation calls immediately after type validation but before any tool invocation. This fail-fast approach rejects bad inputs at the entry point, ensuring no unvalidated input reaches business logic.

### Critical Pitfalls

Research identified three critical pitfalls with verified CVEs and documented attack patterns.

1. **Path Traversal via `os.path.join()` Absolute Path Injection** — When using `os.path.join()` with user input, attackers bypass the base directory by providing absolute paths. Python documentation explicitly states: "If a component is an absolute path, all previous components are thrown away." Prevention: Use `pathlib.Path.resolve()` + `is_relative_to()` pattern and pre-validate for absolute paths on both Unix and Windows.

2. **Incomplete ReDoS Protection via Pattern Blocklists** — The current blocklist approach rejects `(a+)+` but misses equivalent patterns. Blocklists are inherently incomplete as new attack patterns emerge. Prevention: Add timeout protection using the `regex` PyPI package (1-2 second timeout), limit input length before regex matching, and keep blocklist as first-line defense.

3. **Information Disclosure via Exception Details** — Exposing exception type and message reveals implementation details: file paths (`/var/secrets/key.pem`), SQL queries, library versions, stack traces. Prevention: Map exceptions to generic messages for external responses, log full details internally with correlation ID, never include `exc_info=True` in user-facing responses.

4. **TOCTOU Between Validation and Use** — CVE-2026-22701 (filelock) demonstrates this is actively exploited. The time gap between checking a path and using it allows symlink injection. For educational projects with local-only access, risk is mitigated, but document the trust boundary.

5. **Windows UNC Path Bypass** — Path validation often missing Windows-specific check for `\\server\share` absolute paths. Verify absolute path detection covers Unix (`/`), Windows drive letters (`C:\`), and UNC paths.

## Implications for Roadmap

Based on research, suggested phase structure with clear dependency chain:

### Phase 1: Path Validation Foundation
**Rationale:** Most critical security control (prevents arbitrary file read); zero new dependencies; establishes pattern for later phases
**Delivers:** `security/` module with path_validator.py and exceptions.py; integration into both MCP tools
**Addresses:** Path traversal prevention (FEATURES.md P1), Qodo critical warnings
**Avoids:** os.path.join() absolute path injection pitfall, Windows UNC path bypass, TOCTOU race (documented as accepted risk)
**Research needed:** None — stdlib pattern with official documentation, well-established

### Phase 2: ReDoS Protection Enhancement
**Rationale:** Depends on Phase 1 exceptions.py; adds `regex` library for timeout; completes defense-in-depth
**Delivers:** regex_validator.py with timeout-protected pattern compilation; server integration for keyword_search tool only
**Uses:** `regex` library ^2026.1.15 (STACK.md recommendation)
**Addresses:** Complete ReDoS protection (FEATURES.md P1), Qodo high warnings
**Avoids:** Incomplete blocklist pitfall, unbounded regex timeout trap
**Research needed:** None — regex library has native timeout feature, documented in PyPI

### Phase 3: Error Sanitization Standardization
**Rationale:** Depends on Phase 1 exceptions.py; improves existing partial implementation; lowest security impact
**Delivers:** error_sanitizer.py with correlation ID pattern; standardized error responses across all handlers
**Implements:** SafeError wrapper pattern (ARCHITECTURE.md)
**Addresses:** Safe error messages (FEATURES.md P1), information disclosure prevention
**Avoids:** Stack trace exposure, path leakage in error messages
**Research needed:** None — standard pattern with OWASP documentation

### Phase 4 (Optional): Enhanced Validation
**Rationale:** Defense-in-depth additions after core security established; optional educational enhancements
**Delivers:** Allowlisted directories config, security logging, structured error codes
**Addresses:** Should-have features from FEATURES.md (educational value)
**Uses:** Patterns from Phases 1-3
**Research needed:** Minimal — MCP spec for "roots" concept, standard logging patterns

### Phase Ordering Rationale

- **Phase 1 first** because path validation prevents the highest-impact vulnerability (arbitrary file read), has zero dependencies, and establishes the exceptions.py foundation that Phases 2-3 require
- **Phase 2 before Phase 3** because ReDoS has higher security impact than error sanitization (DoS vs. info disclosure), and regex timeout adds a new dependency that should be validated mid-sequence
- **Sequential not parallel** because all phases share exceptions.py and integration points in server.py; sequential testing is cleaner
- **Phase 4 deferred** because it's optional enhancement; core security is complete after Phase 3

### Research Flags

**Phases with standard patterns (skip research):**
- **Phase 1:** Path validation uses documented Python stdlib pattern from OpenStack/OWASP guidelines
- **Phase 2:** ReDoS timeout uses well-documented `regex` library feature with official PyPI documentation
- **Phase 3:** Error sanitization follows standard exception wrapper pattern

**No phases need deeper research.** All patterns are well-documented with official sources. Implementation can proceed directly from research outputs.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Python stdlib and `regex` library have official documentation; versions verified on PyPI; compatibility confirmed with Python 3.10+ |
| Features | HIGH | Based on MCP Security Best Practices (official spec), OWASP guidelines, and analysis of Qodo code review patterns |
| Architecture | HIGH | Utility module pattern is standard Python approach; validated against existing codebase style; clear integration points |
| Pitfalls | HIGH | Verified with CVE databases (CVE-2026-22701), Python official docs, OpenStack security guidelines, recent vulnerability reports |

**Overall confidence:** HIGH

All recommendations are backed by official documentation, established security guidelines, or verified CVEs. The path forward is clear with minimal uncertainty.

### Gaps to Address

**Minor gaps that need decisions during implementation (not blockers):**

- **Allowed directories configuration** — Should it be hardcoded to `Path.cwd()` or configurable? Recommendation: Start with `Path.cwd()` only, make configurable in Phase 4 if needed
- **Regex timeout value** — Should timeout be 1 second or 2 seconds? Recommendation: Start with 1 second, make configurable via constant if needed
- **Symlink handling policy** — Should the system follow symlinks or reject them? Recommendation: Follow symlinks (using `resolve()`) since local callers are trusted; document the decision
- **Windows path testing** — Codebase likely developed on Unix; need to verify Windows UNC path detection works correctly. Recommendation: Add unit tests for Windows paths even if running on Unix

**None of these gaps are blockers.** All can be resolved with reasonable defaults during Phase 1 implementation.

## Sources

### Primary (HIGH confidence)
- [Python pathlib documentation](https://docs.python.org/3/library/pathlib.html) — `resolve()`, `is_relative_to()` methods
- [Python os.path documentation](https://docs.python.org/3/library/os.path.html) — `os.path.join()` behavior with absolute paths
- [regex PyPI package](https://pypi.org/project/regex/) — Version 2026.1.15, timeout parameter
- [MCP Security Best Practices](https://modelcontextprotocol.io/specification/draft/basic/security_best_practices) — Resource limits, sandboxing guidance
- [OWASP Path Traversal](https://owasp.org/www-community/attacks/Path_Traversal) — Attack patterns and prevention
- [OWASP ReDoS](https://owasp.org/www-community/attacks/Regular_expression_Denial_of_Service_-_ReDoS) — ReDoS attack patterns
- [CVE-2026-22701](https://www.cvedetails.com/cve/CVE-2026-22701/) — filelock TOCTOU vulnerability

### Secondary (MEDIUM confidence)
- [OpenStack Security Guidelines - File Paths](https://security.openstack.org/guidelines/dg_using-file-paths.html) — Path validation patterns
- [Sonar: 10 Unknown Security Pitfalls for Python](https://www.sonarsource.com/blog/10-unknown-security-pitfalls-for-python/) — os.path.join vulnerability
- [Snyk Python Security Cheat Sheet](https://snyk.io/blog/python-security-best-practices-cheat-sheet/) — Best practices
- [Invicti: Stack Trace Disclosure](https://www.invicti.com/web-vulnerability-scanner/vulnerabilities/stack-trace-disclosure-python/) — Error handling
- [Python Security Best Practices (Corgea)](https://corgea.com/Learn/python-security-best-practices-a-comprehensive-guide-for-engineers) — Comprehensive guide

### Tertiary (LOW confidence - for context only)
- Community blog posts on ReDoS patterns — Supplementary examples
- Comparisons of validation libraries — Informational, not relied upon for decisions

---
*Research completed: 2026-01-25*
*Ready for roadmap: yes*
