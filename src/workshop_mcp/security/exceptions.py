"""Security-specific exceptions for the MCP server.

All exceptions in this module are designed to be safe to expose to clients.
Error messages are intentionally generic to avoid leaking sensitive information.
"""


class SecurityValidationError(Exception):
    """Base class for security validation errors.

    All security validation errors should inherit from this class.
    The string representation is safe to expose to clients.
    """

    pass


class PathValidationError(SecurityValidationError):
    """Raised when path validation fails.

    The message is intentionally generic to avoid leaking information
    about the file system structure or attempted path.

    Examples of when this is raised:
    - Path contains directory traversal sequences (../)
    - Path is outside allowed root directories
    - Path does not exist (when existence is required)
    - Path is a directory when a file is required
    """

    def __init__(self, message: str = "Invalid file path") -> None:
        """Initialize with a generic error message.

        Args:
            message: Error message. Should be generic and not contain
                    the actual path that was rejected.
        """
        super().__init__(message)
