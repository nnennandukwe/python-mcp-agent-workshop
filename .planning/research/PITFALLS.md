# Pitfalls Research: Python Security Hardening

**Domain:** Python MCP Server Security Hardening
**Researched:** 2026-01-25
**Confidence:** HIGH (verified with official Python docs, recent CVEs, and authoritative sources)

## Critical Pitfalls

### Pitfall 1: Path Traversal via `os.path.join()` Absolute Path Injection

**What goes wrong:**
When using `os.path.join()` with user-supplied input, attackers can bypass the base directory entirely by providing an absolute path. The Python documentation explicitly states: "If a component is an absolute path, all previous components are thrown away."

```python
# VULNERABLE CODE
file_path = os.path.join("/var/www/uploads", user_input)
# If user_input = "/etc/passwd", result is "/etc/passwd"
```

**Why it happens:**
Developers assume `os.path.join()` always appends to the base path. The "join" semantics are misleading - it can actually replace, not just append. This has led to numerous real-world CVEs including Cuckoo Sandbox Evasion and CVE-2020-35736.

**How to avoid:**
1. **Validate input first** - reject absolute paths before joining
2. **Use `pathlib.Path.resolve()` + `is_relative_to()`** - the canonical Python 3.9+ pattern:

```python
from pathlib import Path

def safe_file_access(base_dir: str, user_path: str) -> Path:
    base = Path(base_dir).resolve()
    target = (base / user_path).resolve()

    if not target.is_relative_to(base):
        raise ValueError("Path traversal attempt detected")

    return target
```

3. **Pre-validate for absolute paths on Windows too:**

```python
def is_absolute_path(path: str) -> bool:
    # Unix absolute path
    if path.startswith('/'):
        return True
    # Windows drive letter (C:\, D:\, etc.)
    if len(path) > 1 and path[1] == ':':
        return True
    # Windows UNC path (\\server\share)
    if path.startswith('\\\\'):
        return True
    return False
```

**Warning signs:**
- Code using `os.path.join()` with any user-controllable input
- Path validation using string methods like `startswith()` instead of `is_relative_to()`
- No explicit check for absolute paths before joining

**Phase to address:**
Phase 1 (Path Validation) - this is the most critical security control for file_path parameter

**Confidence:** HIGH - verified in [Python official documentation](https://docs.python.org/3/library/os.path.html#os.path.join), [Sonar Security Pitfalls](https://www.sonarsource.com/blog/10-unknown-security-pitfalls-for-python/), and [OpenStack Security Guidelines](https://security.openstack.org/guidelines/dg_using-file-paths.html)

---

### Pitfall 2: Incomplete ReDoS Protection via Pattern Blocklists

**What goes wrong:**
The current codebase uses a blocklist approach to detect dangerous regex patterns. Blocklists are inherently incomplete - new attack patterns emerge, and clever encoding can bypass detection. The code rejects `(a+)+` but may miss equivalent patterns.

```python
# CURRENT APPROACH - Blocklist (incomplete)
dangerous_patterns = [
    r'\([^)]*[+*][^)]*\)[+*]',  # Nested quantifiers
    r'\([^)]*\|[^)]*\)[+*]',   # Alternation with quantifier
]
```

**Why it happens:**
ReDoS is fundamentally a property of backtracking regex engines. Python's `re` module uses backtracking and doesn't support timeouts natively. Any pattern that allows exponential backtracking paths can cause denial-of-service.

**How to avoid:**
1. **Add timeout protection** using the `regex` PyPI package (drop-in replacement for `re` with timeout support):

```python
import regex

def safe_regex_match(pattern: str, text: str, timeout: float = 1.0):
    try:
        return regex.search(pattern, text, timeout=timeout)
    except TimeoutError:
        raise ValueError("Regex operation timed out - possible ReDoS pattern")
```

2. **Limit input length** before regex matching:

```python
MAX_INPUT_LENGTH = 10000  # Adjust based on expected use case

def validate_input_length(text: str, max_length: int = MAX_INPUT_LENGTH):
    if len(text) > max_length:
        raise ValueError(f"Input exceeds maximum length of {max_length}")
```

3. **Consider using static analysis tools** like [regexploit](https://github.com/doyensec/regexploit) to detect vulnerable patterns in code

**Warning signs:**
- Regex patterns compiled from user input
- No timeout mechanism for regex operations
- Blocklist-only approach without defense-in-depth

**Phase to address:**
Phase 2 (ReDoS Protection) - enhance existing blocklist with timeout as defense-in-depth

**Confidence:** HIGH - verified in [regex PyPI documentation](https://pypi.org/project/regex/) showing timeout feature, and [OWASP ReDoS guidance](https://owasp.org/www-community/attacks/Regular_expression_Denial_of_Service_-_ReDoS)

---

### Pitfall 3: Information Disclosure via Exception Details

**What goes wrong:**
Exposing exception type and message to API callers reveals implementation details that aid attackers. Stack traces expose file paths, library versions, and internal logic.

```python
# PROBLEMATIC - exposes internal details
except Exception as exc:
    return {"error": str(exc)}  # Could reveal: "FileNotFoundError: [Errno 2] No such file: /var/secrets/key.pem"
```

**Why it happens:**
During development, detailed errors help debugging. Developers forget to sanitize errors before production. Python's exception messages often contain sensitive context like file paths, SQL queries, or stack traces.

**How to avoid:**
1. **Map exceptions to generic messages:**

```python
# Error mapping for external responses
ERROR_MESSAGES = {
    "parse_error": "Invalid input format",
    "not_found": "Resource not found",
    "validation": "Invalid parameters",
    "internal": "An unexpected error occurred",
}

def safe_error_response(error_code: str, request_id: str = None):
    return {
        "error": ERROR_MESSAGES.get(error_code, ERROR_MESSAGES["internal"]),
        "request_id": request_id,  # Allows correlation with logs without exposing details
    }
```

2. **Log detailed errors internally, return generic externally:**

```python
import logging
import uuid

logger = logging.getLogger(__name__)

def handle_error(exc: Exception, request_id: str = None):
    error_id = request_id or str(uuid.uuid4())

    # Internal logging - full details
    logger.error(
        "Error %s: %s",
        error_id,
        exc,
        exc_info=True  # Includes stack trace in logs
    )

    # External response - generic message
    return {
        "error": "An unexpected error occurred",
        "error_id": error_id,
    }
```

3. **Never include `exc_info=True` in user-facing responses**

**Warning signs:**
- `str(exc)` or `repr(exc)` in API responses
- Stack traces visible to callers
- Different error messages for similar failures (enables probing)
- Debug mode enabled in production

**Phase to address:**
Phase 3 (Error Handling) - standardize error responses across all tool handlers

**Confidence:** HIGH - verified in [Invicti Stack Trace Disclosure](https://www.invicti.com/web-vulnerability-scanner/vulnerabilities/stack-trace-disclosure-python/), [OWASP Error Handling](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/08-Testing_for_Error_Handling/)

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Blocklist-only ReDoS protection | Quick to implement | Bypasses discovered over time; false sense of security | Never as sole protection - always pair with timeout |
| Using `str(exc)` for error messages | Easy debugging | Information disclosure; inconsistent error format | Development only, never production |
| Trusting `Path.resolve()` alone | Handles `..` sequences | Doesn't catch absolute path injection; follows symlinks | Only after pre-validating input isn't absolute |
| Skipping input length validation | Simpler code | Memory exhaustion attacks; ReDoS amplification | Never for user-provided input |

## Integration Gotchas

Common mistakes when connecting path validation to the MCP tool interface.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| file_path parameter | Validating after opening file | Validate path containment BEFORE any file operation |
| root_paths in keyword_search | Only validating existence, not containment | Each path should be resolved and checked against allowed directories |
| tempfile operations | Using user input in prefix/suffix | Sanitize or reject user-controlled prefix/suffix components |
| Error responses | Including file path in error message | Use generic "file not found" without revealing attempted path |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Unbounded regex timeout | Single request hangs server | Use `regex` package with timeout, max 1-2 seconds | First malicious pattern submitted |
| Deep path validation recursion | Stack overflow on nested paths | Limit path component count (e.g., max 50 components) | Deeply nested paths (../../../... x100) |
| Synchronous path validation in async context | Event loop blocked during validation | Path validation is CPU-bound, acceptably fast; don't over-optimize | N/A for this use case |

## Security Mistakes

Domain-specific security issues specific to this MCP server context.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Allowing symlinks without following | Attacker creates symlink to sensitive file | Either follow symlinks with `resolve()` or reject them entirely |
| TOCTOU between validation and use | Race condition allows path swap | Minimize gap; use atomic operations where possible; revalidate at use |
| Trusting local caller assumption | Compromised host has full access anyway | For educational project, acceptable; document the trust boundary |
| Inconsistent path handling across tools | Different tools have different vulnerabilities | Centralize path validation in a single utility function |

**Note on TOCTOU:** CVE-2026-22701 (filelock) demonstrates this vulnerability is actively exploited. The attack window between checking a path and using it allows symlink injection. For this educational project with local-only access, the risk is mitigated, but production code should use `O_NOFOLLOW` flags and atomic operations.

**Confidence:** HIGH - CVE-2026-22701 published January 2026, verified in [CVE Details](https://www.cvedetails.com/cve/CVE-2026-22701/)

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Path validation:** Often missing Windows UNC path check (`\\server\share`) - verify both Unix and Windows absolute path detection
- [ ] **ReDoS protection:** Often missing timeout - verify blocklist + timeout + input length limit
- [ ] **Error handling:** Often missing log correlation - verify error_id in logs matches response
- [ ] **Input validation:** Often missing type coercion attacks - verify JSON schema validation catches non-string file_path
- [ ] **Symlink handling:** Often missing policy decision - verify explicit choice: follow, reject, or document accepted risk

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Path traversal exploited | HIGH | Audit logs for accessed files; rotate any exposed credentials; patch immediately |
| ReDoS triggered | LOW | Kill hung process; add pattern to blocklist; implement timeout |
| Stack trace exposed | MEDIUM | Assess what was revealed; rotate if credentials visible; patch error handling |
| TOCTOU race exploited | HIGH | Audit what was accessed/modified; restore from backup if needed; add atomic operations |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Path traversal (os.path.join) | Phase 1: Path Validation | Unit tests with absolute paths, `..` sequences, Windows paths |
| Path traversal (string prefix check) | Phase 1: Path Validation | Unit tests using paths like `/var/www-evil/` that pass prefix but fail containment |
| ReDoS via regex | Phase 2: ReDoS Protection | Timeout tests with known evil patterns; fuzz testing |
| Information disclosure | Phase 3: Error Handling | Audit all error responses; ensure no file paths or stack traces |
| Symlink attacks | Phase 1: Path Validation | Policy documented; tests with symlinks if following; tests rejecting if not |
| TOCTOU races | Document only | Note accepted risk for educational project; document mitigation for production |

## Specific Recommendations for This Codebase

Based on reviewing `keyword_search.py` and `server.py`:

### 1. file_path Parameter (performance_check tool)

Currently, `PerformanceChecker(file_path=file_path)` accepts arbitrary paths. Add containment validation:

```python
ALLOWED_BASE_DIRS = [
    Path.cwd(),  # Current working directory
    # Add other allowed directories
]

def validate_file_path(file_path: str) -> Path:
    """Validate file_path is within allowed directories."""
    path = Path(file_path).resolve()

    for base in ALLOWED_BASE_DIRS:
        base = base.resolve()
        if path.is_relative_to(base):
            return path

    raise ValueError("File path not within allowed directories")
```

### 2. root_paths Parameter (keyword_search tool)

Similarly validate each root_path against allowed directories.

### 3. Regex Patterns (_build_pattern method)

Current blocklist is a good start. Add timeout as defense-in-depth:

```python
# Option 1: Use regex package
import regex
compiled = regex.compile(pattern, flags=flags)
# Then in _count_occurrences, use timeout:
regex.findall(compiled, content, timeout=2.0)

# Option 2: Keep re but add input length limit
MAX_CONTENT_LENGTH = 10_000_000  # 10MB
if len(content) > MAX_CONTENT_LENGTH:
    raise ValueError("Content too large for regex search")
```

### 4. Error Responses

Current code has good practice in some places:
```python
{"details": "An unexpected error occurred. Check server logs for details."}
```

But inconsistent in others:
```python
JsonRpcError(-32602, str(exc))  # May expose path information
```

Standardize all error responses to use generic messages.

## Sources

### Official Documentation
- [Python pathlib documentation](https://docs.python.org/3/library/pathlib.html) - `resolve()` and `is_relative_to()` reference
- [Python os.path documentation](https://docs.python.org/3/library/os.path.html) - `os.path.join()` behavior

### CVE and Vulnerability Databases
- [CVE-2026-22701 - filelock TOCTOU](https://www.cvedetails.com/cve/CVE-2026-22701/) - January 2026 symlink vulnerability
- [CVE-2024-12718 - Python tarfile](https://www.upwind.io/feed/cve-2024-12718-path-escape-via-pythons-tarfile-extraction-filters) - tarfile filter bypass

### Security Guidance
- [Sonar: 10 Unknown Security Pitfalls for Python](https://www.sonarsource.com/blog/10-unknown-security-pitfalls-for-python/) - os.path.join, tempfile, assert
- [OpenStack Security: Path Access Guidelines](https://security.openstack.org/guidelines/dg_using-file-paths.html) - canonicalization patterns
- [Invicti: Stack Trace Disclosure](https://www.invicti.com/web-vulnerability-scanner/vulnerabilities/stack-trace-disclosure-python/) - error handling

### ReDoS Prevention
- [regex PyPI package](https://pypi.org/project/regex/) - timeout feature documentation
- [Doyensec regexploit](https://github.com/doyensec/regexploit) - static analysis tool

### MCP Security
- [MCP Server Hardening](https://protocolguard.com/resources/mcp-server-hardening/) - best practices
- [Red Hat: MCP Security Risks and Controls](https://www.redhat.com/en/blog/model-context-protocol-mcp-understanding-security-risks-and-controls) - threat model

---
*Pitfalls research for: Python MCP Server Security Hardening*
*Researched: 2026-01-25*
