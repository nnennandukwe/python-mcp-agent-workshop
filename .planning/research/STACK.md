# Stack Research: Python Security Hardening

**Domain:** Security hardening for Python MCP server (path validation, ReDoS protection, error sanitization)
**Researched:** 2026-01-25
**Confidence:** HIGH

## Executive Summary

This research identifies Python libraries and approaches for three security hardening areas needed to address Qodo review warnings:

1. **Path validation/sandboxing** - Use Python stdlib `pathlib.Path.resolve()` + `is_relative_to()` (no external deps)
2. **ReDoS protection** - Use `regex` library with timeout parameter (verified 2026.1.15)
3. **Safe error handling** - Standard patterns with custom exception wrapper classes (no new deps)

The recommended approach minimizes new dependencies while providing robust security controls.

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| Python stdlib `pathlib` | 3.10+ (project requirement) | Path validation, traversal protection | Zero dependencies, `is_relative_to()` available since 3.9, `resolve()` handles symlinks | HIGH |
| `regex` (mrab-regex) | ^2026.1.15 | ReDoS-safe regex with timeout | Drop-in `re` replacement, native timeout parameter raises `TimeoutError`, actively maintained | HIGH |
| Pydantic | ^2.12.5 | Input validation schemas | Type-safe validation, 10x faster than alternatives, excellent error messages, FastAPI ecosystem standard | MEDIUM |

### Supporting Libraries

| Library | Version | Purpose | When to Use | Confidence |
|---------|---------|---------|-------------|------------|
| `regex` | ^2026.1.15 | Timeout-protected regex matching | When `use_regex=True` in keyword_search | HIGH |
| Pydantic | ^2.12.5 | Schema validation for tool inputs | Optional: for stricter input validation at MCP boundary | MEDIUM |

### Development Tools

| Tool | Purpose | Notes | Confidence |
|------|---------|-------|------------|
| Bandit | Security linter | ^1.9.3 - Detects insecure patterns, integrates with CI | HIGH |
| pytest | Test security controls | Already in project | HIGH |

---

## Detailed Recommendations

### 1. Path Validation/Sandboxing

**Recommendation:** Use Python stdlib only (no new dependencies)

**Approach:**
```python
from pathlib import Path
from typing import Optional

class PathValidator:
    """Validates file paths are within allowed directories."""

    def __init__(self, allowed_roots: list[Path]):
        self.allowed_roots = [root.resolve() for root in allowed_roots]

    def validate(self, path: str) -> Path:
        """
        Validate path is within allowed roots.

        Raises:
            ValueError: If path escapes allowed directories
        """
        resolved = Path(path).resolve()

        for root in self.allowed_roots:
            if resolved.is_relative_to(root):
                return resolved

        raise ValueError("Path is outside allowed directories")
```

**Why stdlib over external libraries:**
- `pathlib.Path.is_relative_to()` available since Python 3.9 (project requires 3.10+)
- `Path.resolve()` handles symlink resolution (prevents symlink-based traversal)
- Zero external dependencies = zero supply chain risk
- Battle-tested in Python core

**Security considerations:**
- MUST call `resolve()` before `is_relative_to()` to handle symlinks
- The check is lexical after resolution, not filesystem-based
- Works with both absolute and relative input paths

**Sources:**
- [Python pathlib documentation](https://docs.python.org/3/library/pathlib.html) - `is_relative_to()` added in 3.9, removed in 3.14 the multi-argument form
- [OpenStack security guidelines](https://security.openstack.org/guidelines/dg_using-file-paths.html)

### 2. ReDoS Protection

**Recommendation:** Use `regex` library (mrab-regex) with timeout parameter

**Approach:**
```python
import regex
from regex import TimeoutError as RegexTimeoutError

# Replace dangerous re.compile() with timeout-protected version
def compile_safe_pattern(
    pattern: str,
    flags: int = 0,
    timeout: float = 1.0
) -> regex.Pattern:
    """
    Compile regex pattern with timeout protection.

    Args:
        pattern: Regex pattern string
        flags: Regex flags (regex.IGNORECASE, etc.)
        timeout: Maximum seconds for matching operations

    Raises:
        ValueError: If pattern is invalid
        TimeoutError: If compilation or matching exceeds timeout
    """
    try:
        return regex.compile(pattern, flags=flags, timeout=timeout)
    except regex.error as e:
        raise ValueError(f"Invalid regex pattern: {e}")

# Usage in keyword_search.py
def _build_pattern(self, keyword: str, case_insensitive: bool, use_regex: bool):
    if not use_regex:
        return None

    flags = regex.IGNORECASE if case_insensitive else 0
    # 1 second timeout protects against catastrophic backtracking
    return compile_safe_pattern(keyword, flags=flags, timeout=1.0)
```

**Why `regex` over alternatives:**

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| `regex` (mrab-regex) | Native timeout, drop-in `re` replacement, full PCRE features | External dependency | **USE THIS** |
| `google-re2` / `pyre2` | Guaranteed linear time (no ReDoS possible) | No lookahead/lookbehind/backreferences, C++ build dependency | Use if regex features not needed |
| Pattern detection only | No new dependencies | Incomplete protection, patterns can slip through | Current approach - insufficient |

**Key `regex` library features:**
- `timeout` parameter on all matching methods
- Raises `TimeoutError` (stdlib exception) when exceeded
- Compatible with `re` module (VERSION0 flag for full compat)
- Supports Python 3.9+ (project uses 3.10+)

**Sources:**
- [regex on PyPI](https://pypi.org/project/regex/) - Version 2026.1.15, timeout documented
- [mrab-regex GitHub](https://github.com/mrabarnett/mrab-regex)
- [LWN article on regex timeout](https://lwn.net/Articles/885682/)

### 3. Safe Error Handling

**Recommendation:** Implement exception wrapper pattern with sanitized messages (no new dependencies)

**Approach:**
```python
from typing import Optional, Any
import logging

logger = logging.getLogger(__name__)

class SafeError(Exception):
    """Base exception with safe public message and internal details."""

    def __init__(
        self,
        public_message: str,
        internal_details: Optional[str] = None,
        original_exception: Optional[Exception] = None
    ):
        self.public_message = public_message
        self.internal_details = internal_details
        self.original_exception = original_exception
        super().__init__(public_message)

    def log_internal(self) -> None:
        """Log internal details for debugging without exposing to client."""
        if self.internal_details:
            logger.error(
                "SafeError: %s | Internal: %s",
                self.public_message,
                self.internal_details,
                exc_info=self.original_exception
            )

class ValidationError(SafeError):
    """Raised for input validation failures."""
    pass

class PathTraversalError(SafeError):
    """Raised when path escapes allowed directories."""
    pass

class RegexTimeoutError(SafeError):
    """Raised when regex operation times out."""
    pass

# Usage in server.py
def _execute_performance_check(self, request_id, arguments):
    try:
        # ... tool execution ...
    except FileNotFoundError as e:
        # Safe: don't reveal full path structure
        raise ValidationError(
            public_message="File not found",
            internal_details=f"Path: {file_path}",
            original_exception=e
        )
    except Exception as e:
        # Safe: generic message, log full details internally
        error = SafeError(
            public_message="An unexpected error occurred",
            internal_details=str(e),
            original_exception=e
        )
        error.log_internal()
        raise error
```

**Principles:**
1. **Separate public and internal messages** - Public messages are user-safe, internal details logged only
2. **Use exception chaining** - `raise ... from e` preserves debugging context
3. **Avoid revealing:**
   - Full file paths (may reveal system structure)
   - Stack traces (may reveal implementation)
   - Library versions (may reveal vulnerabilities)
   - Internal error codes
4. **Log everything internally** - Full details go to stderr/logs, not response

**Sources:**
- [Qwiet security best practices](https://qwiet.ai/appsec-resources/securing-your-python-codebase-best-practices-for-developers/)
- [Snyk Python security cheat sheet](https://snyk.io/blog/python-security-best-practices-cheat-sheet/)
- [Python exceptions documentation](https://docs.python.org/3/tutorial/errors.html)

---

## Installation

```bash
# Add to pyproject.toml dependencies
poetry add "regex>=2026.1.15"

# Optional: Add Pydantic if using schema validation
poetry add "pydantic>=2.12.5"

# Add Bandit to dev dependencies
poetry add --group dev "bandit>=1.9.3"
```

**Updated pyproject.toml:**
```toml
[tool.poetry.dependencies]
python = ">=3.10,<4.0"
aiofiles = "^23.2.0"
astroid = "^3.0.0"
regex = "^2026.1.15"  # NEW: ReDoS-safe regex with timeout

[tool.poetry.group.dev.dependencies]
# ... existing ...
bandit = "^1.9.3"  # NEW: Security linter
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Python stdlib `pathlib` | `pathvalidate` library | If you need path sanitization (replacing invalid chars) not just validation |
| `regex` with timeout | `google-re2` / `pyre2` | If you can sacrifice lookahead/lookbehind/backreferences for guaranteed linear time |
| `regex` with timeout | Current pattern detection | Never - pattern detection is incomplete, timeouts are the only reliable protection |
| Custom SafeError class | `structlog` | If you need structured logging across entire app (overkill for this scope) |
| Pydantic | Marshmallow | If you prefer schema-first over type-hint-first validation style |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Pattern-based ReDoS detection only | Incomplete - many dangerous patterns slip through | `regex` with timeout |
| `eval()` or `exec()` for any input | Code injection vulnerability | Never use with untrusted input |
| Generic `except Exception` without re-raise | Swallows bugs, hides issues | Catch specific exceptions, wrap and re-raise |
| Exposing `str(exception)` to clients | May leak internal details | Use SafeError pattern |
| `os.path` for path validation | No `is_relative_to()`, more error-prone | `pathlib.Path` |
| Regex without timeout | ReDoS vulnerable | `regex` library with timeout parameter |

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `regex` ^2026.1.15 | Python 3.9-3.14 | Project uses 3.10+, fully compatible |
| `pathlib.is_relative_to()` | Python 3.9+ | Project uses 3.10+, fully compatible |
| Pydantic ^2.12.5 | Python 3.9+ | Project uses 3.10+, fully compatible |
| Bandit ^1.9.3 | Python 3.9+ | Project uses 3.10+, fully compatible |

---

## Implementation Priority

Based on Qodo review warnings and security impact:

| Priority | Component | Effort | Impact |
|----------|-----------|--------|--------|
| 1 | ReDoS timeout (`regex` library) | Low | HIGH - Prevents DoS |
| 2 | Path validation (stdlib) | Low | HIGH - Prevents traversal |
| 3 | Error sanitization | Medium | MEDIUM - Prevents info leakage |
| 4 | Bandit integration | Low | MEDIUM - Catches future issues |
| 5 | Pydantic schemas | Medium | LOW - Defense in depth |

---

## Sources

### HIGH Confidence (Official Documentation)
- [Python pathlib documentation](https://docs.python.org/3/library/pathlib.html) - `is_relative_to()` method
- [regex PyPI](https://pypi.org/project/regex/) - Version 2026.1.15, timeout feature
- [Pydantic PyPI](https://pypi.org/project/pydantic/) - Version 2.12.5
- [google-re2 PyPI](https://pypi.org/project/google-re2/) - Version 1.1.20251105

### MEDIUM Confidence (Verified with Multiple Sources)
- [Snyk Python security cheat sheet](https://snyk.io/blog/python-security-best-practices-cheat-sheet/)
- [OpenStack security guidelines](https://security.openstack.org/guidelines/dg_using-file-paths.html)
- [Real Python pathlib guide](https://realpython.com/python-pathlib/)

### LOW Confidence (WebSearch Only - Verify Before Use)
- Community blog posts on exception handling patterns
- Comparisons of validation libraries

---

*Stack research for: Python MCP Server Security Hardening*
*Researched: 2026-01-25*
