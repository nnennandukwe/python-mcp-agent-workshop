"""Tests for SecurityValidationError exception handling in MCP server.

These tests verify that SecurityValidationError subclasses pass through their
safe messages to clients instead of being caught by the generic Exception handler.

The SecurityValidationError hierarchy:
- SecurityValidationError (base)
  - PathValidationError (path validation failures)
  - RegexValidationError (regex pattern validation failures)
  - RegexTimeoutError (regex evaluation timeouts)
  - RegexAbortError (regex operation aborts due to repeated timeouts)

All these exceptions have intentionally safe messages that can be exposed to clients.
"""

import logging
from unittest.mock import patch

from workshop_mcp.security import (
    RegexAbortError,
    RegexTimeoutError,
    RegexValidationError,
    SecurityValidationError,
)
from workshop_mcp.server import WorkshopMCPServer


class TestRegexValidationErrorPassthrough:
    """Test that RegexValidationError passes through its safe message."""

    def test_regex_validation_error_message_passthrough(self, tmp_path, monkeypatch):
        """RegexValidationError should return -32602 with its safe message."""
        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
        server = WorkshopMCPServer()

        # Mock keyword search to raise RegexValidationError
        with patch.object(
            server.keyword_search_tool,
            "execute",
            side_effect=RegexValidationError("Pattern rejected: nested quantifiers detected"),
        ):
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "call_tool",
                "params": {
                    "name": "keyword_search",
                    "arguments": {
                        "keyword": "(a+)+$",  # Malicious regex pattern
                        "root_paths": [str(tmp_path)],
                        "use_regex": True,
                    },
                },
            }

            response = server._handle_request(request)

        assert "error" in response
        assert response["error"]["code"] == -32602  # Invalid params
        assert response["error"]["message"] == "Pattern rejected: nested quantifiers detected"
        # Should NOT be "Internal error"
        assert response["error"]["message"] != "Internal error"

    def test_regex_validation_error_default_message(self, tmp_path, monkeypatch):
        """RegexValidationError with default message should pass through."""
        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
        server = WorkshopMCPServer()

        # Mock keyword search to raise RegexValidationError with default message
        with patch.object(
            server.keyword_search_tool,
            "execute",
            side_effect=RegexValidationError(),
        ):
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "call_tool",
                "params": {
                    "name": "keyword_search",
                    "arguments": {
                        "keyword": "test",
                        "root_paths": [str(tmp_path)],
                    },
                },
            }

            response = server._handle_request(request)

        assert "error" in response
        assert response["error"]["code"] == -32602
        assert response["error"]["message"] == "Invalid regex pattern"


class TestRegexAbortErrorPassthrough:
    """Test that RegexAbortError passes through its safe message."""

    def test_regex_abort_error_message_passthrough(self, tmp_path, monkeypatch):
        """RegexAbortError should return -32602 with its safe message."""
        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
        server = WorkshopMCPServer()

        # Mock keyword search to raise RegexAbortError
        with patch.object(
            server.keyword_search_tool,
            "execute",
            side_effect=RegexAbortError("Pattern timed out on too many files"),
        ):
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "call_tool",
                "params": {
                    "name": "keyword_search",
                    "arguments": {
                        "keyword": "slow.*pattern",
                        "root_paths": [str(tmp_path)],
                        "use_regex": True,
                    },
                },
            }

            response = server._handle_request(request)

        assert "error" in response
        assert response["error"]["code"] == -32602  # Invalid params
        assert response["error"]["message"] == "Pattern timed out on too many files"
        # Should NOT be "Internal error"
        assert response["error"]["message"] != "Internal error"

    def test_regex_abort_error_default_message(self, tmp_path, monkeypatch):
        """RegexAbortError with default message should pass through."""
        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
        server = WorkshopMCPServer()

        # Mock keyword search to raise RegexAbortError with default message
        with patch.object(
            server.keyword_search_tool,
            "execute",
            side_effect=RegexAbortError(),
        ):
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "call_tool",
                "params": {
                    "name": "keyword_search",
                    "arguments": {
                        "keyword": "test",
                        "root_paths": [str(tmp_path)],
                    },
                },
            }

            response = server._handle_request(request)

        assert "error" in response
        assert response["error"]["code"] == -32602
        assert response["error"]["message"] == "Pattern timed out on too many files"


class TestRegexTimeoutErrorPassthrough:
    """Test that RegexTimeoutError passes through its safe message."""

    def test_regex_timeout_error_message_passthrough(self, tmp_path, monkeypatch):
        """RegexTimeoutError should return -32602 with its safe message."""
        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
        server = WorkshopMCPServer()

        # Mock keyword search to raise RegexTimeoutError
        with patch.object(
            server.keyword_search_tool,
            "execute",
            side_effect=RegexTimeoutError("Pattern evaluation timed out"),
        ):
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "call_tool",
                "params": {
                    "name": "keyword_search",
                    "arguments": {
                        "keyword": "slow.*pattern",
                        "root_paths": [str(tmp_path)],
                        "use_regex": True,
                    },
                },
            }

            response = server._handle_request(request)

        assert "error" in response
        assert response["error"]["code"] == -32602  # Invalid params
        assert response["error"]["message"] == "Pattern evaluation timed out"
        # Should NOT be "Internal error"
        assert response["error"]["message"] != "Internal error"

    def test_regex_timeout_error_default_message(self, tmp_path, monkeypatch):
        """RegexTimeoutError with default message should pass through."""
        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
        server = WorkshopMCPServer()

        # Mock keyword search to raise RegexTimeoutError with default message
        with patch.object(
            server.keyword_search_tool,
            "execute",
            side_effect=RegexTimeoutError(),
        ):
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "call_tool",
                "params": {
                    "name": "keyword_search",
                    "arguments": {
                        "keyword": "test",
                        "root_paths": [str(tmp_path)],
                    },
                },
            }

            response = server._handle_request(request)

        assert "error" in response
        assert response["error"]["code"] == -32602
        assert response["error"]["message"] == "Pattern evaluation timed out"


class TestSecurityValidationErrorBaseClass:
    """Test that base SecurityValidationError passes through its message."""

    def test_base_security_error_passthrough(self, tmp_path, monkeypatch):
        """SecurityValidationError base class should pass through its message."""
        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
        server = WorkshopMCPServer()

        # Mock keyword search to raise base SecurityValidationError
        with patch.object(
            server.keyword_search_tool,
            "execute",
            side_effect=SecurityValidationError("Generic security error"),
        ):
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "call_tool",
                "params": {
                    "name": "keyword_search",
                    "arguments": {
                        "keyword": "test",
                        "root_paths": [str(tmp_path)],
                    },
                },
            }

            response = server._handle_request(request)

        assert "error" in response
        assert response["error"]["code"] == -32602
        assert response["error"]["message"] == "Generic security error"
        # Should NOT be "Internal error"
        assert response["error"]["message"] != "Internal error"


class TestPathValidationErrorRegression:
    """Test that PathValidationError still works correctly (no regression)."""

    def test_path_validation_error_still_works(self, tmp_path, monkeypatch):
        """PathValidationError should still return its safe message."""
        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
        server = WorkshopMCPServer()

        # Try to access path outside allowed roots
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "call_tool",
            "params": {
                "name": "performance_check",
                "arguments": {
                    "file_path": "/etc/passwd",
                },
            },
        }

        response = server._handle_request(request)

        assert "error" in response
        assert response["error"]["code"] == -32602
        # PathValidationError has safe, generic message
        assert "outside allowed directories" in response["error"]["message"]
        # Should NOT contain the actual path
        assert "/etc/passwd" not in response["error"]["message"]

    def test_keyword_search_path_validation_still_works(self, tmp_path, monkeypatch):
        """PathValidationError from keyword_search should still work."""
        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
        server = WorkshopMCPServer()

        # Try to search outside allowed roots
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "call_tool",
            "params": {
                "name": "keyword_search",
                "arguments": {
                    "keyword": "test",
                    "root_paths": ["/etc"],  # Outside allowed roots
                },
            },
        }

        response = server._handle_request(request)

        assert "error" in response
        assert response["error"]["code"] == -32602
        assert "outside allowed directories" in response["error"]["message"]


class TestSecurityExceptionLogging:
    """Test that security exceptions are logged at WARNING level."""

    def test_regex_validation_error_logged(self, tmp_path, monkeypatch, caplog):
        """RegexValidationError should be logged at WARNING level."""
        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
        server = WorkshopMCPServer()

        # Mock keyword search to raise RegexValidationError
        with patch.object(
            server.keyword_search_tool,
            "execute",
            side_effect=RegexValidationError("Pattern rejected: nested quantifiers detected"),
        ):
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "call_tool",
                "params": {
                    "name": "keyword_search",
                    "arguments": {
                        "keyword": "(a+)+$",
                        "root_paths": [str(tmp_path)],
                        "use_regex": True,
                    },
                },
            }

            with caplog.at_level(logging.WARNING):
                server._handle_request(request)

        # Verify the error was logged
        assert any(
            "Security validation error" in record.message or "nested quantifiers" in record.message
            for record in caplog.records
        )

    def test_regex_abort_error_logged(self, tmp_path, monkeypatch, caplog):
        """RegexAbortError should be logged at WARNING level."""
        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
        server = WorkshopMCPServer()

        # Mock keyword search to raise RegexAbortError
        with patch.object(
            server.keyword_search_tool,
            "execute",
            side_effect=RegexAbortError("Pattern timed out on too many files"),
        ):
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "call_tool",
                "params": {
                    "name": "keyword_search",
                    "arguments": {
                        "keyword": "test",
                        "root_paths": [str(tmp_path)],
                    },
                },
            }

            with caplog.at_level(logging.WARNING):
                server._handle_request(request)

        # Verify the error was logged
        assert any(
            "Security validation error" in record.message or "timed out" in record.message
            for record in caplog.records
        )
