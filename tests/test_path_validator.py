"""Tests for PathValidator security module.

This module tests path validation to prevent directory traversal attacks.
All paths must be validated before file system operations.
"""

import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from workshop_mcp.security import PathValidationError, PathValidator, SecurityValidationError


class TestTraversalRejection:
    """Test that PathValidator rejects directory traversal attempts."""

    def test_rejects_traversal_patterns(self):
        """Validate rejects all forms of directory traversal."""
        validator = PathValidator(allowed_roots=[Path("/home/user/project")])

        traversal_paths = [
            "../etc/passwd",
            "foo/../../../etc/passwd",
            "..%2F..%2Fetc/passwd",
        ]

        for path in traversal_paths:
            with pytest.raises(PathValidationError) as exc_info:
                validator.validate(path)
            assert "Path is outside allowed directories" in str(exc_info.value)

    def test_accepts_single_dot_paths(self):
        """Validate accepts paths with single dots (current directory)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "valid" / "path.txt"
            test_file.parent.mkdir(parents=True)
            test_file.touch()

            validator = PathValidator(allowed_roots=[Path(tmpdir)])
            result = validator.validate(f"{tmpdir}/./valid/./path.txt")
            assert result == test_file.resolve()


class TestAbsolutePaths:
    """Test absolute path handling."""

    def test_rejects_absolute_path_outside_root(self):
        """Validate rejects absolute paths outside allowed roots."""
        validator = PathValidator(allowed_roots=[Path("/home/user/project")])

        with pytest.raises(PathValidationError) as exc_info:
            validator.validate("/etc/passwd")
        assert "Path is outside allowed directories" in str(exc_info.value)

    def test_accepts_absolute_path_within_root(self):
        """Validate accepts absolute paths within allowed roots."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "src" / "file.py"
            test_file.parent.mkdir(parents=True)
            test_file.touch()

            validator = PathValidator(allowed_roots=[Path(tmpdir)])
            result = validator.validate(str(test_file))
            assert result == test_file.resolve()

    def test_accepts_path_in_any_allowed_root(self):
        """Validate accepts paths in any of the allowed roots."""
        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                file1 = Path(tmpdir1) / "file1.py"
                file2 = Path(tmpdir2) / "file2.py"
                file1.touch()
                file2.touch()

                validator = PathValidator(
                    allowed_roots=[Path(tmpdir1), Path(tmpdir2)]
                )

                assert validator.validate(str(file1)) == file1.resolve()
                assert validator.validate(str(file2)) == file2.resolve()


class TestEnvironmentConfig:
    """Test environment variable configuration."""

    def test_loads_roots_from_env_var(self):
        """PathValidator loads allowed roots from MCP_ALLOWED_ROOTS env var."""
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
        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ.pop("MCP_ALLOWED_ROOTS", None)
            validator = PathValidator()

            assert len(validator.allowed_roots) == 1
            assert validator.allowed_roots[0] == Path.cwd().resolve()

    def test_skips_nonexistent_paths_in_env(self):
        """PathValidator skips paths that don't exist when loading from env."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_value = f"{tmpdir}:/nonexistent/path/12345"

            with mock.patch.dict(os.environ, {"MCP_ALLOWED_ROOTS": env_value}):
                validator = PathValidator()
                assert len(validator.allowed_roots) == 1
                assert validator.allowed_roots[0] == Path(tmpdir).resolve()


class TestValidateMultiple:
    """Test validate_multiple method."""

    def test_validates_multiple_paths(self):
        """validate_multiple validates all paths and fails fast on invalid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_a = Path(tmpdir) / "a.py"
            file_b = Path(tmpdir) / "b.py"
            file_a.touch()
            file_b.touch()

            validator = PathValidator(allowed_roots=[Path(tmpdir)])

            # Valid paths
            results = validator.validate_multiple([str(file_a), str(file_b)])
            assert len(results) == 2
            assert results[0] == file_a.resolve()

            # Invalid path - fails fast
            with pytest.raises(PathValidationError):
                validator.validate_multiple([str(file_a), "../evil"])


class TestValidateExists:
    """Test validate_exists method."""

    def test_raises_for_nonexistent_file(self):
        """validate_exists raises PathValidationError for nonexistent path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            validator = PathValidator(allowed_roots=[Path(tmpdir)])

            with pytest.raises(PathValidationError) as exc_info:
                validator.validate_exists(f"{tmpdir}/nonexistent.py")
            assert "File not found" in str(exc_info.value)

    def test_file_vs_directory_validation(self):
        """validate_exists distinguishes files from directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.touch()
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()

            validator = PathValidator(allowed_roots=[Path(tmpdir)])

            # File passes with must_be_file=True
            result = validator.validate_exists(str(test_file), must_be_file=True)
            assert result == test_file.resolve()

            # Directory fails with must_be_file=True
            with pytest.raises(PathValidationError) as exc_info:
                validator.validate_exists(str(subdir), must_be_file=True)
            assert "Path is not a file" in str(exc_info.value)

            # Directory passes with must_be_file=False
            result = validator.validate_exists(str(subdir), must_be_file=False)
            assert result == subdir.resolve()


class TestEdgeCases:
    """Test edge cases and security-critical scenarios."""

    def test_rejects_symlink_escape(self):
        """Validate rejects symlinks that point outside allowed roots."""
        with tempfile.TemporaryDirectory() as allowed_dir:
            with tempfile.TemporaryDirectory() as forbidden_dir:
                secret_file = Path(forbidden_dir) / "secret.txt"
                secret_file.write_text("secret data")

                symlink_path = Path(allowed_dir) / "evil_link"
                symlink_path.symlink_to(secret_file)

                validator = PathValidator(allowed_roots=[Path(allowed_dir)])

                with pytest.raises(PathValidationError):
                    validator.validate(str(symlink_path))

    def test_error_messages_are_generic(self):
        """Error messages do not leak path details."""
        validator = PathValidator(allowed_roots=[Path("/safe/root")])

        with pytest.raises(PathValidationError) as exc_info:
            validator.validate("../../etc/shadow")

        error_message = str(exc_info.value)
        assert "/etc/shadow" not in error_message
        assert "../../" not in error_message
        assert "Path is outside allowed directories" in error_message


class TestExceptionHierarchy:
    """Test the security exception class hierarchy."""

    def test_path_validation_error_inherits_from_security_error(self):
        """PathValidationError inherits from SecurityValidationError."""
        assert issubclass(PathValidationError, SecurityValidationError)
        assert issubclass(SecurityValidationError, Exception)

        # Default and custom messages
        assert str(PathValidationError()) == "Invalid file path"
        assert str(PathValidationError("File not found")) == "File not found"


class TestPublicAPI:
    """Test that the public API is correctly exported."""

    def test_validator_has_expected_methods(self):
        """PathValidator has all expected public methods."""
        with tempfile.TemporaryDirectory() as tmpdir:
            validator = PathValidator(allowed_roots=[Path(tmpdir)])

            assert hasattr(validator, "validate")
            assert hasattr(validator, "validate_multiple")
            assert hasattr(validator, "validate_exists")
            assert hasattr(validator, "allowed_roots")
            assert callable(validator.validate)
            assert callable(validator.validate_multiple)
            assert callable(validator.validate_exists)
