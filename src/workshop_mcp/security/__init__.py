"""Security validation module for MCP server.

This module provides security controls for input validation:
- PathValidator: Prevents directory traversal attacks
- PathValidationError: Safe exception for path validation failures
- SecurityValidationError: Base class for all security exceptions

Usage:
    from workshop_mcp.security import PathValidator, PathValidationError

    validator = PathValidator()  # Loads from MCP_ALLOWED_ROOTS env var
    try:
        validated = validator.validate(user_path)
    except PathValidationError as e:
        # Safe to return str(e) to client - generic message
        return error_response(str(e))
"""

__version__ = "0.1.0"

from .exceptions import PathValidationError, SecurityValidationError
from .path_validator import PathValidator

__all__ = [
    "PathValidator",
    "PathValidationError",
    "SecurityValidationError",
]
