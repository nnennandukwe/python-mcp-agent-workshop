# Phase 1: Path Validation - Research

**Researched:** 2026-01-25
**Domain:** Python path security, directory traversal prevention, environment configuration
**Confidence:** HIGH

## Summary

Path validation is the first security control for this MCP server, preventing attackers from reading files outside allowed directories. The research confirms that Python's `pathlib` module provides all necessary tools via `Path.resolve()` and `Path.is_relative_to()` - no external dependencies required.

The standard approach is a three-step validation:
1. Resolve the path to eliminate `..` sequences and follow symlinks
2. Verify the resolved path is within an allowed root directory
3. Return a generic error if validation fails (never expose the attempted path)

Configuration via environment variable `MCP_ALLOWED_ROOTS` follows established patterns used in production Python applications.

**Primary recommendation:** Implement a `PathValidator` utility class in `src/workshop_mcp/security/` using Python stdlib `pathlib` with configurable allowed roots via environment variable.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pathlib` (stdlib) | Python 3.10+ | Path resolution and validation | Zero dependencies, `is_relative_to()` since 3.9, `resolve()` handles symlinks |
| `os` (stdlib) | Python 3.10+ | Environment variable access | Standard for runtime configuration |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `logging` (stdlib) | Python 3.10+ | Security event logging | Log rejected paths with correlation ID |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pathlib stdlib | `pathvalidate` library | External dep adds supply chain risk; project only needs containment check, not sanitization |
| Environment variables | Config file (YAML/JSON) | Config files can be modified post-deployment; env vars are simpler for single value |
| Single allowed root | Multiple roots list | Multiple roots implemented for flexibility; comma-separated env var `MCP_ALLOWED_ROOTS=/path1:/path2` |

**Installation:**
```bash
# No new dependencies needed - pathlib is stdlib
# Existing pyproject.toml unchanged for this phase
```

## Architecture Patterns

### Recommended Project Structure
```
src/workshop_mcp/
├── security/                    # NEW: Security validation module
│   ├── __init__.py              # Public API: PathValidator, PathValidationError
│   ├── path_validator.py        # Path traversal prevention
│   └── exceptions.py            # Security-specific exceptions
├── server.py                    # Integration: calls path_validator before tool execution
├── keyword_search.py            # Unchanged - receives validated paths
└── performance_profiler/        # Unchanged - receives validated paths
```

### Pattern 1: Fail-Fast Path Validation
**What:** Validate all path inputs immediately upon receipt, before any file system operations.
**When to use:** Every tool execution that accepts file_path or root_paths parameters.
**Example:**
```python
# Source: https://docs.python.org/3/library/pathlib.html (is_relative_to, resolve)
from pathlib import Path
from typing import List
import os

class PathValidator:
    """Validates file paths are within allowed directories."""

    def __init__(self, allowed_roots: List[Path] | None = None):
        """
        Initialize with allowed root directories.

        If allowed_roots is None, reads from MCP_ALLOWED_ROOTS env var.
        Falls back to current working directory if env var not set.
        """
        if allowed_roots is not None:
            self.allowed_roots = [root.resolve() for root in allowed_roots]
        else:
            self.allowed_roots = self._load_from_env()

    def _load_from_env(self) -> List[Path]:
        """Load allowed roots from environment variable."""
        env_value = os.environ.get("MCP_ALLOWED_ROOTS", "")
        if env_value:
            # Support colon-separated list (Unix) or semicolon (Windows)
            separator = ";" if os.name == "nt" else ":"
            paths = [Path(p.strip()).resolve() for p in env_value.split(separator) if p.strip()]
            if paths:
                return paths
        # Default to current working directory
        return [Path.cwd().resolve()]

    def validate(self, path: str) -> Path:
        """
        Validate path is within allowed roots.

        Args:
            path: User-provided path string

        Returns:
            Resolved, validated Path object

        Raises:
            PathValidationError: If path escapes allowed directories
        """
        # Step 1: Resolve to eliminate ../ and follow symlinks
        resolved = Path(path).resolve()

        # Step 2: Check against allowed roots
        for root in self.allowed_roots:
            if resolved.is_relative_to(root):
                return resolved

        # Step 3: Reject with generic error (no path details)
        raise PathValidationError("Path is outside allowed directories")

    def validate_multiple(self, paths: List[str]) -> List[Path]:
        """Validate multiple paths, failing on first invalid path."""
        return [self.validate(p) for p in paths]
```

### Pattern 2: Typed Security Exceptions
**What:** Define custom exception classes that are safe to expose to clients by design.
**When to use:** All security validation code.
**Example:**
```python
# Source: Established Python exception patterns
class SecurityValidationError(Exception):
    """Base class for security validation errors. Safe to expose str()."""
    pass

class PathValidationError(SecurityValidationError):
    """Raised when path validation fails. Message is safe for client."""

    def __init__(self, message: str = "Invalid file path"):
        # Message intentionally generic - no path details
        super().__init__(message)
```

### Pattern 3: Server Integration Point
**What:** Validate paths at the server layer before passing to tools.
**When to use:** In `_execute_keyword_search` and `_execute_performance_check` methods.
**Example:**
```python
# In server.py
from workshop_mcp.security import PathValidator, PathValidationError

class WorkshopMCPServer:
    def __init__(self) -> None:
        self.keyword_search_tool = KeywordSearchTool()
        self.path_validator = PathValidator()  # NEW
        # ...

    def _execute_keyword_search(self, request_id, arguments):
        # ... existing type validation ...

        # NEW: Path validation before tool execution
        try:
            validated_paths = self.path_validator.validate_multiple(root_paths)
        except PathValidationError as e:
            return self._error_response(
                request_id,
                JsonRpcError(-32602, str(e))  # Safe: generic message
            )

        # Pass validated paths to tool
        result = self.loop.run_until_complete(
            self.keyword_search_tool.execute(
                keyword,
                [str(p) for p in validated_paths],  # Convert back to strings
                # ...
            )
        )
```

### Anti-Patterns to Avoid
- **String-based path checking:** Never use `if "../" in path` - easily bypassed with encoding variations
- **Validation in business logic:** Don't put path validation inside KeywordSearchTool - security belongs in server layer
- **os.path.join without pre-validation:** `os.path.join("/base", "/etc/passwd")` returns `/etc/passwd` (absolute path replaces base)
- **Exposing path in error:** Never return `f"Path {path} is not allowed"` - leaks attempted traversal

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Path canonicalization | String replacement for `../` | `Path.resolve()` | Handles symlinks, encoding, Windows paths, edge cases |
| Relative path check | String prefix matching | `Path.is_relative_to()` | Handles path separators correctly, not fooled by `/var/www-evil` vs `/var/www` |
| Environment config parsing | Custom parser | `os.environ.get()` with split | Battle-tested, handles all platforms |

**Key insight:** Path security is a solved problem in Python 3.9+. Custom string manipulation is always worse than `pathlib`.

## Common Pitfalls

### Pitfall 1: Absolute Path Injection via os.path.join()
**What goes wrong:** `os.path.join("/base", user_input)` where `user_input="/etc/passwd"` returns `/etc/passwd`, completely ignoring the base.
**Why it happens:** Python documentation states "If a component is an absolute path, all previous components are thrown away."
**How to avoid:** Always validate before joining, or use `(base / user_input).resolve()` which doesn't have this behavior.
**Warning signs:** Code using `os.path.join()` with any user-controllable input.

### Pitfall 2: Checking Before Resolution
**What goes wrong:** Calling `is_relative_to()` on a path that hasn't been resolved - `../` sequences aren't eliminated.
**Why it happens:** `is_relative_to()` is a string operation, not filesystem-aware.
**How to avoid:** Always call `resolve()` first: `Path(user_input).resolve().is_relative_to(base.resolve())`
**Warning signs:** `is_relative_to()` called without preceding `resolve()`.

### Pitfall 3: Symlink Escape
**What goes wrong:** Attacker creates symlink inside allowed directory pointing to `/etc/passwd`.
**Why it happens:** Path validation without symlink resolution only checks the symlink path, not its target.
**How to avoid:** `Path.resolve()` follows symlinks by default - the resolved path is the actual file location.
**Warning signs:** Using `Path.absolute()` instead of `Path.resolve()` (absolute doesn't follow symlinks).

### Pitfall 4: Windows Path Handling
**What goes wrong:** Validation works on Unix but fails on Windows with drive letters (`C:\`) or UNC paths (`\\server\share`).
**Why it happens:** Different path formats and separators between platforms.
**How to avoid:** `pathlib` handles this automatically - just use `Path.resolve()` and `is_relative_to()`.
**Warning signs:** Manual path string manipulation with `/` or `\` characters.

### Pitfall 5: Leaking Path Details in Error
**What goes wrong:** Error message includes attempted path, revealing directory structure to attacker.
**Why it happens:** Using `str(exc)` from FileNotFoundError or including path in custom error.
**How to avoid:** Return generic "Path is outside allowed directories" - log the actual path internally.
**Warning signs:** `f"Path {path} not found"` in any error response.

## Code Examples

Verified patterns from official sources:

### Complete PathValidator Implementation
```python
# Source: https://docs.python.org/3/library/pathlib.html
# Source: https://salvatoresecurity.com/preventing-directory-traversal-vulnerabilities-in-python/

from pathlib import Path
from typing import List, Optional
import os
import logging

logger = logging.getLogger(__name__)


class PathValidationError(Exception):
    """Raised when path validation fails. Safe to expose to client."""
    pass


class PathValidator:
    """
    Validates file paths are within allowed directories.

    Uses pathlib.resolve() for canonicalization and is_relative_to() for
    containment checking. This handles:
    - ../ traversal sequences
    - Symlink resolution
    - Windows and Unix path formats
    - Absolute path injection
    """

    ENV_VAR_NAME = "MCP_ALLOWED_ROOTS"

    def __init__(self, allowed_roots: Optional[List[Path]] = None):
        if allowed_roots is not None:
            self.allowed_roots = [root.resolve() for root in allowed_roots]
        else:
            self.allowed_roots = self._load_from_env()

        logger.info(
            "PathValidator initialized with %d allowed roots",
            len(self.allowed_roots)
        )

    def _load_from_env(self) -> List[Path]:
        """Load allowed roots from environment variable."""
        env_value = os.environ.get(self.ENV_VAR_NAME, "")

        if env_value:
            separator = ";" if os.name == "nt" else ":"
            paths = []
            for p in env_value.split(separator):
                p = p.strip()
                if p:
                    resolved = Path(p).resolve()
                    if resolved.exists():
                        paths.append(resolved)
                    else:
                        logger.warning(
                            "Allowed root does not exist, skipping: %s",
                            resolved
                        )
            if paths:
                return paths

        # Default: current working directory
        cwd = Path.cwd().resolve()
        logger.info(
            "%s not set, defaulting to cwd: %s",
            self.ENV_VAR_NAME,
            cwd
        )
        return [cwd]

    def validate(self, path: str) -> Path:
        """
        Validate path is within allowed roots.

        Args:
            path: User-provided path string

        Returns:
            Resolved, validated Path object

        Raises:
            PathValidationError: If path escapes allowed directories
        """
        try:
            resolved = Path(path).resolve()
        except (OSError, ValueError) as e:
            # Invalid path format
            logger.warning("Path resolution failed: %s", e)
            raise PathValidationError("Invalid file path")

        for root in self.allowed_roots:
            if resolved.is_relative_to(root):
                logger.debug("Path validated: %s (under %s)", resolved, root)
                return resolved

        # Log internally, return generic error externally
        logger.warning(
            "Path validation failed - outside allowed roots: %s",
            resolved
        )
        raise PathValidationError("Path is outside allowed directories")

    def validate_multiple(self, paths: List[str]) -> List[Path]:
        """Validate multiple paths. Fails fast on first invalid path."""
        return [self.validate(p) for p in paths]

    def validate_exists(self, path: str, must_be_file: bool = False) -> Path:
        """
        Validate path is within allowed roots AND exists.

        Args:
            path: User-provided path string
            must_be_file: If True, path must be a file (not directory)

        Returns:
            Resolved, validated Path object

        Raises:
            PathValidationError: If validation fails
        """
        validated = self.validate(path)

        if not validated.exists():
            raise PathValidationError("File not found")

        if must_be_file and not validated.is_file():
            raise PathValidationError("Path is not a file")

        return validated
```

### Environment Variable Configuration
```python
# Usage: Set MCP_ALLOWED_ROOTS environment variable
# Unix:    export MCP_ALLOWED_ROOTS="/home/user/projects:/tmp/workspace"
# Windows: set MCP_ALLOWED_ROOTS="C:\Users\user\projects;C:\temp\workspace"

# In code, validator loads from env automatically:
validator = PathValidator()  # Reads MCP_ALLOWED_ROOTS

# Or override programmatically:
validator = PathValidator(allowed_roots=[Path("/custom/path")])
```

### Server Integration
```python
# In server.py _execute_performance_check method
def _execute_performance_check(self, request_id, arguments):
    # ... existing validation ...

    file_path = arguments.get("file_path")
    source_code = arguments.get("source_code")

    if file_path:
        try:
            validated_path = self.path_validator.validate_exists(
                file_path,
                must_be_file=True
            )
        except PathValidationError as e:
            return self._error_response(
                request_id,
                JsonRpcError(-32602, str(e))
            )

        # Use validated_path instead of file_path
        checker = PerformanceChecker(file_path=str(validated_path))
    else:
        checker = PerformanceChecker(source_code=source_code)

    # ... rest of execution ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `os.path.join()` + string checks | `pathlib.Path.resolve()` + `is_relative_to()` | Python 3.9 | Eliminates entire class of traversal bugs |
| Manual `../` detection | `Path.resolve()` canonicalization | Python 3.0 | Handles all normalization automatically |
| Separate Windows/Unix code | `pathlib` cross-platform | Python 3.4 | Single implementation works everywhere |

**Deprecated/outdated:**
- `os.path.realpath()` alone: Doesn't provide containment check
- String prefix matching: Bypassable with `/var/www-evil` vs `/var/www`

## Open Questions

Things that couldn't be fully resolved:

1. **TOCTOU (Time-of-check-to-time-of-use) race conditions**
   - What we know: A gap exists between path validation and file use where symlinks could be swapped
   - What's unclear: Whether this is a practical concern for this educational MCP server
   - Recommendation: Document as accepted risk for educational context; production would need atomic operations or file descriptor passing

2. **Recursive symlink handling**
   - What we know: `Path.resolve()` follows symlinks to final destination
   - What's unclear: Behavior with very deep symlink chains (potential DoS)
   - Recommendation: Python 3.13 raises `OSError` for symlink loops with `strict=True`; using `strict=False` (default) handles gracefully

3. **Multiple root interactions**
   - What we know: If `/a` and `/a/b` are both allowed roots, a path under `/a/b` validates under both
   - What's unclear: Whether this causes any issues
   - Recommendation: No issue identified - path is allowed if under ANY root

## Sources

### Primary (HIGH confidence)
- [Python pathlib documentation](https://docs.python.org/3/library/pathlib.html) - `resolve()`, `is_relative_to()` methods, symlink handling
- [Python os documentation](https://docs.python.org/3/library/os.html) - `os.environ.get()` for configuration

### Secondary (MEDIUM confidence)
- [Preventing Directory Traversal Vulnerabilities in Python](https://salvatoresecurity.com/preventing-directory-traversal-vulnerabilities-in-python/) - Security patterns
- [Path Traversal and remediation in Python](https://osintteam.blog/path-traversal-and-remediation-in-python-0b6e126b4746) - Attack vectors
- [MCP Security Vulnerabilities - Practical DevSecOps](https://www.practical-devsecops.com/mcp-security-vulnerabilities/) - MCP-specific security concerns

### Tertiary (LOW confidence)
- Prior research in `.planning/research/STACK.md`, `ARCHITECTURE.md`, `PITFALLS.md` - Used for context

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Python stdlib pathlib is definitively the right tool
- Architecture: HIGH - Security module pattern is established best practice
- Pitfalls: HIGH - Verified with official Python docs and CVE examples

**Research date:** 2026-01-25
**Valid until:** 90 days (stable domain, pathlib API is mature)
