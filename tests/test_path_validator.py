"""Tests for PathValidator security module.

This module tests path validation to prevent directory traversal attacks.
All paths must be validated before file system operations.
"""

import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest


class TestPathValidatorTraversalRejection:
    """Test that PathValidator rejects directory traversal attempts."""

    def test_rejects_simple_traversal(self):
        """Validate rejects paths containing ../ traversal sequences."""
        from workshop_mcp.security import PathValidationError, PathValidator

        validator = PathValidator(allowed_roots=[Path("/home/user/project")])

        with pytest.raises(PathValidationError) as exc_info:
            validator.validate("../etc/passwd")

        # Error message should be generic (no path details)
        assert "Path is outside allowed directories" in str(exc_info.value)

    def test_rejects_nested_traversal(self):
        """Validate rejects deeply nested traversal attempts."""
        from workshop_mcp.security import PathValidationError, PathValidator

        validator = PathValidator(allowed_roots=[Path("/home/user/project")])

        with pytest.raises(PathValidationError):
            validator.validate("foo/../../../etc/passwd")

    def test_accepts_single_dot_paths(self):
        """Validate accepts paths with single dots (current directory)."""
        from workshop_mcp.security import PathValidator

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file
            test_file = Path(tmpdir) / "valid" / "path.txt"
            test_file.parent.mkdir(parents=True)
            test_file.touch()

            validator = PathValidator(allowed_roots=[Path(tmpdir)])

            # ./valid/./path.txt should resolve to valid/path.txt
            result = validator.validate(f"{tmpdir}/./valid/./path.txt")
            assert result == test_file.resolve()

    def test_rejects_encoded_traversal(self):
        """Validate rejects URL-encoded or otherwise obfuscated traversal."""
        from workshop_mcp.security import PathValidationError, PathValidator

        validator = PathValidator(allowed_roots=[Path("/home/user/project")])

        # These should all be rejected after path resolution
        with pytest.raises(PathValidationError):
            validator.validate("..%2F..%2Fetc/passwd")  # URL encoded


class TestPathValidatorAbsolutePaths:
    """Test absolute path handling."""

    def test_rejects_absolute_path_outside_root(self):
        """Validate rejects absolute paths outside allowed roots."""
        from workshop_mcp.security import PathValidationError, PathValidator

        validator = PathValidator(allowed_roots=[Path("/home/user/project")])

        with pytest.raises(PathValidationError) as exc_info:
            validator.validate("/etc/passwd")

        assert "Path is outside allowed directories" in str(exc_info.value)

    def test_accepts_absolute_path_within_root(self):
        """Validate accepts absolute paths within allowed roots."""
        from workshop_mcp.security import PathValidator

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file
            test_file = Path(tmpdir) / "src" / "file.py"
            test_file.parent.mkdir(parents=True)
            test_file.touch()

            validator = PathValidator(allowed_roots=[Path(tmpdir)])
            result = validator.validate(str(test_file))

            assert result == test_file.resolve()

    def test_accepts_path_in_any_allowed_root(self):
        """Validate accepts paths in any of the allowed roots."""
        from workshop_mcp.security import PathValidator

        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                # Create test files in both directories
                file1 = Path(tmpdir1) / "file1.py"
                file2 = Path(tmpdir2) / "file2.py"
                file1.touch()
                file2.touch()

                validator = PathValidator(allowed_roots=[Path(tmpdir1), Path(tmpdir2)])

                # Both should be accepted
                assert validator.validate(str(file1)) == file1.resolve()
                assert validator.validate(str(file2)) == file2.resolve()


class TestPathValidatorEnvironmentConfig:
    """Test environment variable configuration."""

    def test_loads_roots_from_env_var(self):
        """PathValidator loads allowed roots from MCP_ALLOWED_ROOTS env var."""
        from workshop_mcp.security import PathValidator

        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                env_value = f"{tmpdir1}:{tmpdir2}"

                with mock.patch.dict(os.environ, {"MCP_ALLOWED_ROOTS": env_value}):
                    validator = PathValidator()

                    assert len(validator.allowed_roots) == 2
                    assert Path(tmpdir1).resolve() in validator.allowed_roots
                    assert Path(tmpdir2).resolve() in validator.allowed_roots

    def test_defaults_to_cwd_when_env_not_set(self):
        """PathValidator defaults to current working directory when env not set."""
        from workshop_mcp.security import PathValidator

        with mock.patch.dict(os.environ, {}, clear=True):
            # Remove MCP_ALLOWED_ROOTS if it exists
            os.environ.pop("MCP_ALLOWED_ROOTS", None)

            validator = PathValidator()

            assert len(validator.allowed_roots) == 1
            assert validator.allowed_roots[0] == Path.cwd().resolve()

    def test_handles_windows_style_separator(self):
        """PathValidator handles semicolon separator for Windows-style config.

        Note: This test verifies the separator selection logic by testing
        the private _load_from_env method indirectly. Full Windows path
        testing requires a Windows environment.
        """
        from workshop_mcp.security import PathValidator

        # On Windows (os.name == "nt"), semicolon is used as separator
        # On Unix (os.name == "posix"), colon is used as separator
        # We verify the correct separator is used based on os.name

        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                if os.name == "nt":
                    # On actual Windows, use semicolon
                    env_value = f"{tmpdir1};{tmpdir2}"
                else:
                    # On Unix, verify colon works (semicolon would fail)
                    env_value = f"{tmpdir1}:{tmpdir2}"

                with mock.patch.dict(os.environ, {"MCP_ALLOWED_ROOTS": env_value}):
                    validator = PathValidator()
                    assert len(validator.allowed_roots) == 2
                    assert Path(tmpdir1).resolve() in validator.allowed_roots
                    assert Path(tmpdir2).resolve() in validator.allowed_roots

    def test_skips_nonexistent_paths_in_env(self):
        """PathValidator skips paths that don't exist when loading from env."""
        from workshop_mcp.security import PathValidator

        with tempfile.TemporaryDirectory() as tmpdir:
            env_value = f"{tmpdir}:/nonexistent/path/12345"

            with mock.patch.dict(os.environ, {"MCP_ALLOWED_ROOTS": env_value}):
                validator = PathValidator()

                # Should only have the existing path
                assert len(validator.allowed_roots) == 1
                assert validator.allowed_roots[0] == Path(tmpdir).resolve()


class TestPathValidatorErrorMessages:
    """Test that error messages are generic (no path details leaked)."""

    def test_error_message_is_generic_for_traversal(self):
        """Error message does not contain the attempted path."""
        from workshop_mcp.security import PathValidationError, PathValidator

        validator = PathValidator(allowed_roots=[Path("/safe/root")])

        with pytest.raises(PathValidationError) as exc_info:
            validator.validate("../../etc/shadow")

        error_message = str(exc_info.value)
        # Should NOT contain the attempted path
        assert "/etc/shadow" not in error_message
        assert "../../" not in error_message
        # Should be generic
        assert "Path is outside allowed directories" in error_message

    def test_error_message_is_generic_for_absolute(self):
        """Error message for absolute path does not leak path details."""
        from workshop_mcp.security import PathValidationError, PathValidator

        validator = PathValidator(allowed_roots=[Path("/safe/root")])

        with pytest.raises(PathValidationError) as exc_info:
            validator.validate("/var/log/auth.log")

        error_message = str(exc_info.value)
        assert "/var/log" not in error_message
        assert "auth.log" not in error_message


class TestPathValidatorMultiple:
    """Test validate_multiple method."""

    def test_validates_multiple_valid_paths(self):
        """validate_multiple returns list of resolved Paths for valid input."""
        from workshop_mcp.security import PathValidator

        with tempfile.TemporaryDirectory() as tmpdir:
            file_a = Path(tmpdir) / "a.py"
            file_b = Path(tmpdir) / "b.py"
            file_a.touch()
            file_b.touch()

            validator = PathValidator(allowed_roots=[Path(tmpdir)])
            results = validator.validate_multiple([str(file_a), str(file_b)])

            assert len(results) == 2
            assert results[0] == file_a.resolve()
            assert results[1] == file_b.resolve()

    def test_fails_fast_on_invalid_path(self):
        """validate_multiple raises on first invalid path."""
        from workshop_mcp.security import PathValidationError, PathValidator

        with tempfile.TemporaryDirectory() as tmpdir:
            valid_file = Path(tmpdir) / "valid.py"
            valid_file.touch()

            validator = PathValidator(allowed_roots=[Path(tmpdir)])

            with pytest.raises(PathValidationError):
                validator.validate_multiple([str(valid_file), "../evil"])

    def test_empty_list_returns_empty(self):
        """validate_multiple with empty list returns empty list."""
        from workshop_mcp.security import PathValidator

        with tempfile.TemporaryDirectory() as tmpdir:
            validator = PathValidator(allowed_roots=[Path(tmpdir)])
            results = validator.validate_multiple([])

            assert results == []


class TestPathValidatorExists:
    """Test validate_exists method."""

    def test_raises_for_nonexistent_file(self):
        """validate_exists raises PathValidationError for nonexistent path."""
        from workshop_mcp.security import PathValidationError, PathValidator

        with tempfile.TemporaryDirectory() as tmpdir:
            validator = PathValidator(allowed_roots=[Path(tmpdir)])

            with pytest.raises(PathValidationError) as exc_info:
                validator.validate_exists(f"{tmpdir}/nonexistent.py")

            assert "File not found" in str(exc_info.value)

    def test_raises_for_directory_when_must_be_file(self):
        """validate_exists raises when path is directory but must_be_file=True."""
        from workshop_mcp.security import PathValidationError, PathValidator

        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()

            validator = PathValidator(allowed_roots=[Path(tmpdir)])

            with pytest.raises(PathValidationError) as exc_info:
                validator.validate_exists(str(subdir), must_be_file=True)

            assert "Path is not a file" in str(exc_info.value)

    def test_accepts_existing_file(self):
        """validate_exists returns resolved Path for existing file."""
        from workshop_mcp.security import PathValidator

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.touch()

            validator = PathValidator(allowed_roots=[Path(tmpdir)])
            result = validator.validate_exists(str(test_file), must_be_file=True)

            assert result == test_file.resolve()

    def test_accepts_directory_when_must_be_file_false(self):
        """validate_exists accepts directory when must_be_file=False."""
        from workshop_mcp.security import PathValidator

        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()

            validator = PathValidator(allowed_roots=[Path(tmpdir)])
            result = validator.validate_exists(str(subdir), must_be_file=False)

            assert result == subdir.resolve()


class TestPathValidatorEdgeCases:
    """Test edge cases and security-critical scenarios."""

    def test_rejects_symlink_escape(self):
        """Validate rejects symlinks that point outside allowed roots."""
        from workshop_mcp.security import PathValidationError, PathValidator

        with tempfile.TemporaryDirectory() as allowed_dir:
            with tempfile.TemporaryDirectory() as forbidden_dir:
                # Create a file in the forbidden directory
                secret_file = Path(forbidden_dir) / "secret.txt"
                secret_file.write_text("secret data")

                # Create a symlink in allowed directory pointing to forbidden
                symlink_path = Path(allowed_dir) / "evil_link"
                symlink_path.symlink_to(secret_file)

                validator = PathValidator(allowed_roots=[Path(allowed_dir)])

                # Should reject because resolved path is outside allowed roots
                with pytest.raises(PathValidationError):
                    validator.validate(str(symlink_path))

    def test_handles_empty_path(self):
        """Validate handles empty path string."""
        from workshop_mcp.security import PathValidationError, PathValidator

        with tempfile.TemporaryDirectory() as tmpdir:
            validator = PathValidator(allowed_roots=[Path(tmpdir)])

            # Empty path resolves to cwd, which may or may not be in allowed roots
            # In this test, cwd is likely not tmpdir
            with pytest.raises(PathValidationError):
                validator.validate("")

    def test_handles_relative_path_within_root(self):
        """Validate handles relative paths that stay within allowed root."""
        from workshop_mcp.security import PathValidator

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test structure
            subdir = Path(tmpdir) / "sub"
            subdir.mkdir()
            test_file = subdir / "file.py"
            test_file.touch()

            validator = PathValidator(allowed_roots=[Path(tmpdir)])

            # Change to tmpdir and use relative path
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = validator.validate("sub/file.py")
                assert result == test_file.resolve()
            finally:
                os.chdir(original_cwd)


class TestSecurityExceptionHierarchy:
    """Test the security exception class hierarchy."""

    def test_path_validation_error_inherits_from_security_error(self):
        """PathValidationError should inherit from SecurityValidationError."""
        from workshop_mcp.security import PathValidationError, SecurityValidationError

        assert issubclass(PathValidationError, SecurityValidationError)
        assert issubclass(SecurityValidationError, Exception)

    def test_path_validation_error_default_message(self):
        """PathValidationError has sensible default message."""
        from workshop_mcp.security import PathValidationError

        error = PathValidationError()
        assert str(error) == "Invalid file path"

    def test_path_validation_error_custom_message(self):
        """PathValidationError accepts custom message."""
        from workshop_mcp.security import PathValidationError

        error = PathValidationError("File not found")
        assert str(error) == "File not found"


class TestPathValidatorPublicAPI:
    """Test that the public API is correctly exported from security module."""

    def test_imports_from_security_module(self):
        """All public classes can be imported from workshop_mcp.security."""
        from workshop_mcp.security import (
            PathValidationError,
            PathValidator,
            SecurityValidationError,
        )

        # Verify classes exist
        assert PathValidator is not None
        assert PathValidationError is not None
        assert SecurityValidationError is not None

    def test_validator_has_expected_methods(self):
        """PathValidator has all expected public methods."""
        from workshop_mcp.security import PathValidator

        with tempfile.TemporaryDirectory() as tmpdir:
            validator = PathValidator(allowed_roots=[Path(tmpdir)])

            # Check method existence
            assert hasattr(validator, "validate")
            assert hasattr(validator, "validate_multiple")
            assert hasattr(validator, "validate_exists")
            assert hasattr(validator, "allowed_roots")
            assert callable(validator.validate)
            assert callable(validator.validate_multiple)
            assert callable(validator.validate_exists)
