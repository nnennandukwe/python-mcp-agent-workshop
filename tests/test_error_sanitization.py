"""Tests for error sanitization and security exception handling in MCP server.

These tests verify that:
1. Internal error details (paths, stack traces) are NOT leaked to clients
2. SecurityValidationError subclasses pass through their safe messages
3. Full debugging information is only available in server logs with correlation IDs
"""

import json
from io import BytesIO
from unittest.mock import patch

from workshop_mcp.security import (
    RegexAbortError,
    RegexTimeoutError,
    RegexValidationError,
    SecurityValidationError,
)
from workshop_mcp.server import WorkshopMCPServer


class TestErrorSanitization:
    """Test that exception details are sanitized in client responses."""

    def test_valueerror_returns_generic_message(self, tmp_path, monkeypatch):
        """ValueError returns 'Invalid parameters' without revealing details."""
        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
        server = WorkshopMCPServer()

        with patch.object(
            server.keyword_search_tool,
            "execute",
            side_effect=ValueError(f"Invalid value for path {tmp_path}/secret/internal.py"),
        ):
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "call_tool",
                "params": {
                    "name": "keyword_search",
                    "arguments": {"keyword": "test", "root_paths": [str(tmp_path)]},
                },
            }
            response = server._handle_request(request)

        assert response["error"]["message"] == "Invalid parameters"
        assert "secret" not in str(response["error"])

    def test_filenotfounderror_returns_generic_message(self, tmp_path, monkeypatch):
        """FileNotFoundError returns 'Resource not found' without revealing path."""
        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
        server = WorkshopMCPServer()

        with patch.object(
            server.keyword_search_tool,
            "execute",
            side_effect=FileNotFoundError("/home/user/sensitive/data/config.json"),
        ):
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "call_tool",
                "params": {
                    "name": "keyword_search",
                    "arguments": {"keyword": "test", "root_paths": [str(tmp_path)]},
                },
            }
            response = server._handle_request(request)

        assert response["error"]["message"] == "Resource not found"
        assert "sensitive" not in str(response["error"])

    def test_syntaxerror_returns_generic_message(self):
        """SyntaxError returns 'Invalid source code syntax' without details."""
        server = WorkshopMCPServer()

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "call_tool",
            "params": {
                "name": "performance_check",
                "arguments": {"source_code": "def foo(:\n    pass"},
            },
        }
        response = server._handle_request(request)

        assert response["error"]["message"] == "Invalid source code syntax"
        assert "line" not in response["error"]["message"].lower()

    def test_keyerror_returns_generic_message(self, tmp_path, monkeypatch):
        """KeyError returns 'Missing required argument' without key name."""
        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
        server = WorkshopMCPServer()

        with patch.object(
            server.keyword_search_tool,
            "execute",
            side_effect=KeyError("internal_config_api_key"),
        ):
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "call_tool",
                "params": {
                    "name": "keyword_search",
                    "arguments": {"keyword": "test", "root_paths": [str(tmp_path)]},
                },
            }
            response = server._handle_request(request)

        assert response["error"]["message"] == "Missing required argument"
        assert "api_key" not in str(response["error"])

    def test_internal_error_has_correlation_id_no_details(self, tmp_path, monkeypatch):
        """Internal errors include correlation_id but not exception details."""
        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
        server = WorkshopMCPServer()

        revealing_error = "Database connection to secret.db failed with password xyz"
        with patch.object(
            server.keyword_search_tool,
            "execute",
            side_effect=RuntimeError(revealing_error),
        ):
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "call_tool",
                "params": {
                    "name": "keyword_search",
                    "arguments": {"keyword": "test", "root_paths": [str(tmp_path)]},
                },
            }
            request_bytes = json.dumps(request).encode("utf-8")
            request_message = (
                f"Content-Length: {len(request_bytes)}\r\n\r\n".encode() + request_bytes
            )

            stdin = BytesIO(request_message)
            stdout = BytesIO()
            server.serve_once(stdin, stdout)

            stdout.seek(0)
            response_data = stdout.read()
            header_end = response_data.find(b"\r\n\r\n")
            response = json.loads(response_data[header_end + 4 :].decode("utf-8"))

        assert response["error"]["code"] == -32603
        assert response["error"]["message"] == "Internal error"
        assert "secret.db" not in str(response["error"])
        assert "correlation_id" in response["error"].get("data", {})
        assert len(response["error"]["data"]["correlation_id"]) == 8


class TestSecurityExceptionPassthrough:
    """Test that SecurityValidationError subclasses pass through safe messages."""

    def test_regex_validation_error_passthrough(self, tmp_path, monkeypatch):
        """RegexValidationError returns -32602 with its safe message."""
        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
        server = WorkshopMCPServer()

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
            response = server._handle_request(request)

        assert response["error"]["code"] == -32602
        assert response["error"]["message"] == "Pattern rejected: nested quantifiers detected"

    def test_regex_abort_and_timeout_errors_passthrough(self, tmp_path, monkeypatch):
        """RegexAbortError and RegexTimeoutError pass through safe messages."""
        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
        server = WorkshopMCPServer()

        for error_class, expected_msg in [
            (RegexAbortError, "Pattern timed out on too many files"),
            (RegexTimeoutError, "Pattern evaluation timed out"),
        ]:
            with patch.object(server.keyword_search_tool, "execute", side_effect=error_class()):
                request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "call_tool",
                    "params": {
                        "name": "keyword_search",
                        "arguments": {"keyword": "test", "root_paths": [str(tmp_path)]},
                    },
                }
                response = server._handle_request(request)

            assert response["error"]["code"] == -32602
            assert response["error"]["message"] == expected_msg

    def test_path_validation_error_passthrough(self, tmp_path, monkeypatch):
        """PathValidationError returns safe message without revealing path."""
        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
        server = WorkshopMCPServer()

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "call_tool",
            "params": {"name": "performance_check", "arguments": {"file_path": "/etc/passwd"}},
        }
        response = server._handle_request(request)

        assert response["error"]["code"] == -32602
        assert "outside allowed directories" in response["error"]["message"]
        assert "/etc/passwd" not in response["error"]["message"]

    def test_base_security_error_passthrough(self, tmp_path, monkeypatch):
        """Base SecurityValidationError passes through its message."""
        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
        server = WorkshopMCPServer()

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
                    "arguments": {"keyword": "test", "root_paths": [str(tmp_path)]},
                },
            }
            response = server._handle_request(request)

        assert response["error"]["code"] == -32602
        assert response["error"]["message"] == "Generic security error"
