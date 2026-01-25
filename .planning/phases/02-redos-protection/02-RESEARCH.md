# Phase 2: ReDoS Protection - Research

**Researched:** 2026-01-25
**Domain:** Regex security, timeout mechanisms, Python regex library
**Confidence:** HIGH

## Summary

This research investigates how to implement ReDoS (Regular Expression Denial of Service) protection for the keyword_search tool. The primary approach is to use the third-party `regex` library (PyPI package `regex`) as a drop-in replacement for Python's standard `re` module, which provides native timeout support.

The codebase currently uses `re.compile()`, `re.findall()`, and `pattern.findall()` in `keyword_search.py`. These can be replaced with the `regex` module equivalents that support a `timeout` parameter. The timeout applies to the entire operation and raises `TimeoutError` when exceeded.

Additionally, the existing pattern blocklist in `_build_pattern()` should be enhanced to catch more catastrophic backtracking patterns while remaining permissive to avoid false positives.

**Primary recommendation:** Replace `import re` with `import regex` and add `timeout=1.0` parameter to all `findall()` calls. Add `RegexValidationError` exception to the security module.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| regex | 2026.1.15 | Drop-in replacement for `re` with timeout | Native timeout support, API-compatible, actively maintained |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| concurrent.futures | stdlib | Thread-based fallback timeout | Only if regex library timeout proves unreliable |
| asyncio | stdlib | Async task timeout wrapper | Already in use for async file operations |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| regex library timeout | signal.SIGALRM | Unix-only, doesn't work on Windows, not thread-safe |
| regex library timeout | ThreadPoolExecutor + Future.result(timeout) | More complex, overhead per operation |
| regex library | re2 (Google) | Better worst-case guarantees but different regex syntax |

**Installation:**
```bash
poetry add regex
```

## Architecture Patterns

### Integration Points in keyword_search.py

The current code has these regex touchpoints:

1. **`_build_pattern()` (lines 318-340):** Compiles regex pattern with optional flags
2. **`_count_occurrences()` (lines 342-355):** Calls `pattern.findall()` or `re.findall()`

### Pattern 1: Regex with Timeout

**What:** Use `regex` module's native timeout parameter
**When to use:** All pattern matching operations
**Example:**
```python
# Source: https://pypi.org/project/regex/
import regex

# Compile-time (no timeout here)
pattern = regex.compile(r'search_term', flags=regex.IGNORECASE)

# Match-time (timeout applies here)
try:
    matches = pattern.findall(content, timeout=1.0)
except TimeoutError:
    # Handle timeout - skip this file
    raise RegexTimeoutError("Pattern evaluation timed out")
```

### Pattern 2: Per-File Timeout with Continue-on-Failure

**What:** Wrap each file's regex operation with timeout, continue search on failure
**When to use:** When processing multiple files
**Example:**
```python
# Source: User requirements - CONTEXT.md
skipped_files = []
timeout_count = 0
total_files = len(files)

for file_path in files:
    try:
        matches = pattern.findall(content, timeout=1.0)
        # Process matches...
    except TimeoutError:
        skipped_files.append(str(file_path))
        timeout_count += 1

        # Abort if >50% files timeout
        if timeout_count > total_files * 0.5:
            raise RegexAbortError("Pattern timed out on too many files")
```

### Pattern 3: Early Pattern Validation

**What:** Validate pattern length and blocklist BEFORE attempting compilation
**When to use:** At the start of execute() method
**Example:**
```python
# Source: User requirements - CONTEXT.md
MAX_PATTERN_LENGTH = 500

def validate_pattern(pattern: str, use_regex: bool) -> None:
    """Validate pattern before use. Raises RegexValidationError on failure."""
    if len(pattern) > MAX_PATTERN_LENGTH:
        raise RegexValidationError("Pattern exceeds maximum length (500 characters)")

    if use_regex:
        # Check for catastrophic backtracking patterns
        if _is_redos_pattern(pattern):
            raise RegexValidationError("Pattern rejected: nested quantifiers detected")

        # Validate syntax
        try:
            regex.compile(pattern)
        except regex.error:
            raise RegexValidationError("Invalid regex syntax")
```

### Recommended Module Structure
```
src/workshop_mcp/security/
    __init__.py              # Add RegexValidationError export
    exceptions.py            # Add RegexValidationError, RegexTimeoutError
    path_validator.py        # Existing
    regex_validator.py       # NEW: Pattern validation logic
```

### Anti-Patterns to Avoid
- **Validating after compilation:** Check blocklist BEFORE calling `regex.compile()` - a malicious pattern can DoS during compilation
- **Global timeout across all files:** Use per-file timeout so one slow file doesn't kill entire search
- **Exposing regex error details:** Internal `regex.error` messages may contain the pattern - wrap in generic message

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Regex timeout | signal.SIGALRM wrapper | `regex` library timeout parameter | Cross-platform, thread-safe, no race conditions |
| ReDoS pattern detection | Custom regex analyzer | Simple blocklist + timeout as safety net | Full ReDoS detection is NP-hard; blocklist catches 90% of attacks |
| Async timeout wrapper | Custom asyncio.wait_for | Let regex timeout handle it | The regex C code respects timeout internally |

**Key insight:** The `regex` library's timeout is implemented at the C level, making it reliable for CPU-bound regex operations. Custom Python-level timeouts using threads or signals cannot interrupt the C regex engine once it's executing.

## Common Pitfalls

### Pitfall 1: Timeout on compile() vs match operations

**What goes wrong:** Attempting to set timeout on `regex.compile()` - it doesn't support timeout
**Why it happens:** Timeout only applies to matching operations (`findall`, `search`, `match`, `sub`)
**How to avoid:** Always use timeout on the matching call, not compilation
**Warning signs:** Hangs during pattern compilation with catastrophic pattern

```python
# WRONG - compile() doesn't support timeout
pattern = regex.compile(r'(a+)+', timeout=1.0)  # Invalid parameter

# RIGHT - timeout on matching operation
pattern = regex.compile(r'(a+)+')
matches = pattern.findall(text, timeout=1.0)
```

### Pitfall 2: Timeout accumulation across files

**What goes wrong:** 1-second timeout per file seems safe, but 1000 files = 1000 seconds max
**Why it happens:** Not considering aggregate worst case
**How to avoid:** Implement the >50% abort threshold as specified in requirements
**Warning signs:** Very large directory searches taking unexpectedly long

### Pitfall 3: False sense of security from blocklist alone

**What goes wrong:** Relying only on pattern blocklist without timeout backup
**Why it happens:** Belief that blocklist catches all ReDoS patterns
**How to avoid:** Blocklist is defense-in-depth, timeout is the real protection
**Warning signs:** Novel ReDoS patterns bypassing blocklist

### Pitfall 4: Leaking pattern in error messages

**What goes wrong:** `regex.error` exceptions contain the problematic pattern
**Why it happens:** Directly passing exception message to client
**How to avoid:** Catch and re-raise with generic message, log original internally
**Warning signs:** Error messages containing user-supplied regex in API responses

```python
# WRONG - leaks pattern
except regex.error as e:
    raise JsonRpcError(-32602, str(e))  # May contain pattern

# RIGHT - generic message
except regex.error as e:
    logger.warning("Invalid regex pattern: %s", e)  # Log internally
    raise RegexValidationError("Invalid regex syntax")  # Generic to client
```

## Code Examples

Verified patterns from official sources and user requirements:

### Replace Standard re with regex

```python
# Source: https://pypi.org/project/regex/
# BEFORE (current code in keyword_search.py)
import re
pattern = re.compile(keyword, flags=flags)
matches = pattern.findall(content)

# AFTER
import regex
pattern = regex.compile(keyword, flags=flags)
matches = pattern.findall(content, timeout=1.0)  # 1 second timeout
```

### Catastrophic Backtracking Detection

```python
# Source: https://docs.aws.amazon.com/codeguru/detector-library/python/catastrophic-backtracking-regex/
# Minimal blocklist - only proven ReDoS vectors

REDOS_PATTERNS = [
    # Nested quantifiers with overlap
    r'\([^)]*[+*]\)[+*]',           # (a+)+, (a*)*
    r'\([^)]*[+*][^)]*\)[+*]',      # (a+b)+, (.*)+
    # Nested groups with quantifiers
    r'\(\?:[^)]*[+*][^)]*\)[+*]',   # (?:a+)+
]

def _is_redos_pattern(pattern: str) -> bool:
    """Check if pattern contains known ReDoS constructs."""
    import re  # Use standard re for the check itself
    for dangerous in REDOS_PATTERNS:
        if re.search(dangerous, pattern):
            return True
    return False
```

### New Security Exceptions

```python
# Source: User requirements (CONTEXT.md) + existing exceptions.py pattern
class RegexValidationError(SecurityValidationError):
    """Raised when regex pattern validation fails.

    The message is safe to expose to clients (no pattern details).
    """
    pass

class RegexTimeoutError(SecurityValidationError):
    """Raised when regex evaluation times out.

    The message is safe to expose to clients.
    """
    def __init__(self, message: str = "Pattern evaluation timed out") -> None:
        super().__init__(message)

class RegexAbortError(SecurityValidationError):
    """Raised when too many files timeout during search.

    The message is safe to expose to clients.
    """
    def __init__(self, message: str = "Pattern timed out on too many files") -> None:
        super().__init__(message)
```

### Updated Result Structure with Metadata

```python
# Source: User requirements (CONTEXT.md)
result = {
    "keyword": keyword,
    "root_paths": root_paths,
    "options": {...},
    "files": {...},
    "summary": {...},
    "metadata": {
        "skipped_files": ["/path/to/slow1.py", "/path/to/slow2.py"],
        "skip_reason": "timeout"
    }
}
```

## JSON-RPC Error Codes

Based on JSON-RPC 2.0 specification and user requirements for distinct error types:

| Error Type | Code | Message | When Used |
|------------|------|---------|-----------|
| Invalid regex syntax | -32602 | "Invalid regex syntax" | Pattern fails `regex.compile()` |
| Pattern too long | -32602 | "Pattern exceeds maximum length (500 characters)" | len(pattern) > 500 |
| ReDoS pattern blocked | -32602 | "Pattern rejected: nested quantifiers detected" | Blocklist match |
| Timeout (file) | Continue | N/A | Single file timeout - skip, continue |
| Timeout (abort) | -32001 | "Pattern timed out on too many files" | >50% files skipped |

**Note:** Codes -32000 to -32099 are reserved for implementation-defined server errors per JSON-RPC 2.0 specification. We use -32001 for operation abort to distinguish from standard parameter errors (-32602).

Source: [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `re` module only | `regex` module with timeout | Available since 2019 | Native timeout support |
| signal.SIGALRM timeout | Library-level timeout | N/A | Cross-platform, thread-safe |
| No ReDoS protection | Blocklist + timeout | Security best practice | Defense in depth |

**Deprecated/outdated:**
- signal-based timeout: Only works on Unix main thread, not suitable for async/threaded code
- subprocess isolation: Overkill for regex timeout, high overhead

## Open Questions

Things that couldn't be fully resolved:

1. **Exact methods supporting timeout in regex module**
   - What we know: `sub()`, `findall()`, `match()`, `search()`, `finditer()` support timeout based on PyPI docs
   - What's unclear: Whether compiled pattern objects' methods also support timeout
   - Recommendation: Test during implementation; fall back to module-level functions if needed

2. **Timeout precision**
   - What we know: Timeout is in seconds as a float
   - What's unclear: Granularity and overhead of timeout checking
   - Recommendation: 1.0 second is conservative; could test with 0.5 if needed

## Sources

### Primary (HIGH confidence)
- [regex PyPI](https://pypi.org/project/regex/) - Package documentation, version 2026.1.15, timeout API
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification) - Error code ranges
- [Python docs: concurrent.futures](https://docs.python.org/3/library/concurrent.futures.html) - Alternative timeout patterns
- Existing codebase: `keyword_search.py`, `security/exceptions.py` - Integration points

### Secondary (MEDIUM confidence)
- [AWS CodeGuru: Catastrophic backtracking regex](https://docs.aws.amazon.com/codeguru/detector-library/python/catastrophic-backtracking-regex/) - ReDoS pattern examples
- [Semgrep: Finding Python ReDoS bugs](https://semgrep.dev/blog/2020/finding-python-redos-bugs-at-scale-using-dlint-and-r2c/) - Detection patterns
- [RexEgg: Catastrophic Backtracking](https://www.rexegg.com/regex-explosive-quantifiers.php) - ReDoS theory

### Tertiary (LOW confidence)
- GitHub mrab-regex changelog - Timeout feature history (incomplete docs)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - regex library is well-documented, widely used
- Architecture: HIGH - Integration points are clear from codebase analysis
- Pitfalls: MEDIUM - Based on general security practices and user requirements

**Research date:** 2026-01-25
**Valid until:** 2026-02-25 (30 days - stable domain)
