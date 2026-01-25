"""Security validation module for MCP server.

This module provides security controls for input validation:
- PathValidator: Prevents directory traversal attacks
- validate_pattern: ReDoS protection for regex patterns
- PathValidationError: Safe exception for path validation failures
- RegexValidationError: Safe exception for regex validation failures
- RegexTimeoutError: Exception for regex evaluation timeouts
- RegexAbortError: Exception for regex operation aborts
- SecurityValidationError: Base class for all security exceptions

Usage:
    from workshop_mcp.security import PathValidator, PathValidationError

    validator = PathValidator()  # Loads from MCP_ALLOWED_ROOTS env var
    try:
        validated = validator.validate(user_path)
    except PathValidationError as e:
        # Safe to return str(e) to client - generic message
        return error_response(str(e))

    from workshop_mcp.security import validate_pattern, RegexValidationError

    try:
        validate_pattern(user_pattern, use_regex=True)
    except RegexValidationError as e:
        # Safe to return str(e) to client - generic message
        return error_response(str(e))
"""

__version__ = "0.1.0"

from .exceptions import (
    PathValidationError,
    RegexAbortError,
    RegexTimeoutError,
    RegexValidationError,
    SecurityValidationError,
)
from .path_validator import PathValidator
from .regex_validator import MAX_PATTERN_LENGTH, validate_pattern

__all__ = [
    "MAX_PATTERN_LENGTH",
    "PathValidator",
    "PathValidationError",
    "RegexAbortError",
    "RegexTimeoutError",
    "RegexValidationError",
    "SecurityValidationError",
    "validate_pattern",
]
