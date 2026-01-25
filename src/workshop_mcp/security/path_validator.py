"""Path validation to prevent directory traversal attacks.

This module provides PathValidator which ensures all file paths are within
allowed directories before any file system operations occur.

Security principles:
- Fail-fast: Validate paths immediately upon receipt
- Defense in depth: Use Path.resolve() to canonicalize before checking
- Generic errors: Never expose actual paths in error messages
- Configurable: Allowed roots via environment variable or explicit config
"""

import logging
import os
from pathlib import Path
from typing import List, Optional

from .exceptions import PathValidationError

logger = logging.getLogger(__name__)


class PathValidator:
    """Validates file paths are within allowed directories.

    Uses pathlib.resolve() for canonicalization and is_relative_to() for
    containment checking. This handles:
    - ../ traversal sequences
    - Symlink resolution (follows to final destination)
    - Windows and Unix path formats
    - Absolute path injection

    Usage:
        validator = PathValidator()  # Loads from MCP_ALLOWED_ROOTS env var
        validated_path = validator.validate("/some/path/file.py")

    Configuration:
        Set MCP_ALLOWED_ROOTS environment variable with colon-separated paths:
        - Unix: export MCP_ALLOWED_ROOTS="/home/user/projects:/tmp/workspace"
        - Windows: set MCP_ALLOWED_ROOTS="C:\\Users\\user\\projects;C:\\temp"
    """

    ENV_VAR_NAME = "MCP_ALLOWED_ROOTS"

    def __init__(self, allowed_roots: Optional[List[Path]] = None) -> None:
        """Initialize the validator with allowed root directories.

        Args:
            allowed_roots: List of allowed root directories. If None,
                          loads from MCP_ALLOWED_ROOTS environment variable.
                          Falls back to current working directory if env
                          variable is not set.
        """
        if allowed_roots is not None:
            self.allowed_roots = [root.resolve() for root in allowed_roots]
        else:
            self.allowed_roots = self._load_from_env()

        logger.info(
            "PathValidator initialized with %d allowed roots",
            len(self.allowed_roots),
        )

    def _load_from_env(self) -> List[Path]:
        """Load allowed roots from environment variable.

        Returns:
            List of resolved Path objects for allowed directories.
            Skips paths that don't exist (with warning).
            Falls back to cwd if no valid paths found.
        """
        env_value = os.environ.get(self.ENV_VAR_NAME, "")

        if env_value:
            # Use semicolon on Windows, colon on Unix
            separator = ";" if os.name == "nt" else ":"
            paths: List[Path] = []

            for p in env_value.split(separator):
                p = p.strip()
                if p:
                    resolved = Path(p).resolve()
                    if resolved.exists():
                        paths.append(resolved)
                    else:
                        logger.warning(
                            "Allowed root does not exist, skipping: %s",
                            resolved,
                        )

            if paths:
                return paths

        # Default: current working directory
        cwd = Path.cwd().resolve()
        logger.info(
            "%s not set, defaulting to cwd: %s",
            self.ENV_VAR_NAME,
            cwd,
        )
        return [cwd]

    def validate(self, path: str) -> Path:
        """Validate that a path is within allowed root directories.

        Steps:
        1. Resolve the path to eliminate ../ and follow symlinks
        2. Check if resolved path is under any allowed root
        3. Return resolved Path or raise generic error

        Args:
            path: User-provided path string (can be relative or absolute)

        Returns:
            Resolved, validated Path object

        Raises:
            PathValidationError: If path escapes allowed directories.
                                Error message is generic (no path details).
        """
        try:
            resolved = Path(path).resolve()
        except (OSError, ValueError) as e:
            # Invalid path format (e.g., null bytes, invalid characters)
            logger.warning("Path resolution failed: %s", e)
            raise PathValidationError("Invalid file path")

        # Check against each allowed root
        for root in self.allowed_roots:
            if resolved.is_relative_to(root):
                logger.debug("Path validated: %s (under %s)", resolved, root)
                return resolved

        # Log the actual path internally, but return generic error
        logger.warning(
            "Path validation failed - outside allowed roots: %s",
            resolved,
        )
        raise PathValidationError("Path is outside allowed directories")

    def validate_multiple(self, paths: List[str]) -> List[Path]:
        """Validate multiple paths, failing fast on the first invalid path.

        Args:
            paths: List of user-provided path strings

        Returns:
            List of resolved, validated Path objects

        Raises:
            PathValidationError: If any path escapes allowed directories
        """
        return [self.validate(p) for p in paths]

    def validate_exists(self, path: str, must_be_file: bool = False) -> Path:
        """Validate that a path is within allowed roots AND exists.

        Args:
            path: User-provided path string
            must_be_file: If True, path must be a file (not a directory)

        Returns:
            Resolved, validated Path object

        Raises:
            PathValidationError: If validation fails. Possible messages:
                - "Path is outside allowed directories"
                - "File not found"
                - "Path is not a file"
        """
        validated = self.validate(path)

        if not validated.exists():
            raise PathValidationError("File not found")

        if must_be_file and not validated.is_file():
            raise PathValidationError("Path is not a file")

        return validated
