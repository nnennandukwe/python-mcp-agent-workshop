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


class RegexValidationError(SecurityValidationError):
    """Raised when regex pattern validation fails.

    The message is intentionally generic to avoid leaking information
    about the specific pattern structure or why it was rejected.

    Examples of when this is raised:
    - Pattern exceeds maximum length
    - Pattern contains known ReDoS constructs
    - Pattern has invalid regex syntax
    """

    def __init__(self, message: str = "Invalid regex pattern") -> None:
        """Initialize with a generic error message.

        Args:
            message: Error message. Should be generic and not expose
                    specifics about the pattern rejection reason.
        """
        super().__init__(message)


class RegexTimeoutError(SecurityValidationError):
    """Raised when regex pattern evaluation times out.

    Used when a regex operation takes too long on a single file,
    indicating the pattern may be causing exponential backtracking.
    """

    def __init__(self, message: str = "Pattern evaluation timed out") -> None:
        """Initialize with a timeout error message.

        Args:
            message: Error message describing the timeout.
        """
        super().__init__(message)


class RegexAbortError(SecurityValidationError):
    """Raised when regex operation is aborted due to repeated timeouts.

    Used when a regex pattern times out on multiple files,
    indicating the pattern is consistently problematic.
    """

    def __init__(self, message: str = "Pattern timed out on too many files") -> None:
        """Initialize with an abort error message.

        Args:
            message: Error message describing the abort reason.
        """
        super().__init__(message)
