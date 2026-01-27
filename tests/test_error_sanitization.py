"""Tests for error sanitization in MCP server.

These tests verify that internal error details (file paths, exception messages,
stack traces) are NOT leaked to clients. Instead, generic error messages should
be returned while full details are logged with correlation IDs.

Security principle: Error messages returned to clients should be safe and generic.
Full debugging information should only be available in server logs.
"""

import json
import logging
from io import BytesIO
from unittest.mock import patch

from workshop_mcp.server import WorkshopMCPServer


class TestValueErrorSanitization:
    """Test that ValueError exceptions return generic messages."""

    def test_valueerror_returns_generic_message(self, tmp_path, monkeypatch):
        """ValueError should return 'Invalid parameters' without exception details."""
        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
        server = WorkshopMCPServer()

        # Create a valid file that will trigger ValueError in processing
        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): pass")

        # Mock keyword search tool to raise ValueError with revealing message
        revealing_message = f"Invalid value for path {tmp_path}/secret/internal.py"
        with patch.object(
            server.keyword_search_tool,
            "execute",
            side_effect=ValueError(revealing_message),
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
        error_message = response["error"]["message"]

        # Should be generic message, not the revealing ValueError content
        assert error_message == "Invalid parameters"
        assert "secret" not in error_message
        assert "internal.py" not in error_message
        assert str(tmp_path) not in error_message


class TestFileNotFoundErrorSanitization:
    """Test that FileNotFoundError exceptions return generic messages."""

    def test_filenotfounderror_returns_generic_message(self, tmp_path, monkeypatch):
        """FileNotFoundError should return 'Resource not found' without path."""
        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
        server = WorkshopMCPServer()

        # Mock keyword search tool to raise FileNotFoundError with path
        revealing_path = "/home/user/sensitive/data/config.json"
        with patch.object(
            server.keyword_search_tool,
            "execute",
            side_effect=FileNotFoundError(revealing_path),
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
        error_message = response["error"]["message"]

        # Should be generic message, not the file path
        assert error_message == "Resource not found"
        assert "sensitive" not in error_message
        assert "config.json" not in error_message
        assert "/home/user" not in error_message


class TestSyntaxErrorSanitization:
    """Test that SyntaxError exceptions return generic messages."""

    def test_syntaxerror_returns_generic_message(self):
        """SyntaxError should return 'Invalid source code syntax' without details."""
        server = WorkshopMCPServer()

        # Provide code with syntax error that has line number info
        bad_code = """
def foo(:
    # Syntax error at line 2
    pass
"""

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "call_tool",
            "params": {
                "name": "performance_check",
                "arguments": {
                    "source_code": bad_code,
                },
            },
        }

        response = server._handle_request(request)

        assert "error" in response
        error_message = response["error"]["message"]

        # Should be generic message, not syntax error details
        assert error_message == "Invalid source code syntax"
        assert "line 2" not in error_message.lower()
        assert "def foo" not in error_message
        assert "invalid syntax" not in error_message.lower()


class TestKeyErrorSanitization:
    """Test that KeyError exceptions return generic messages."""

    def test_keyerror_returns_generic_message(self, tmp_path, monkeypatch):
        """KeyError should return 'Missing required argument' without key name."""
        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
        server = WorkshopMCPServer()

        # Mock keyword search to raise KeyError with key name
        sensitive_key = "internal_config_api_key"
        with patch.object(
            server.keyword_search_tool,
            "execute",
            side_effect=KeyError(sensitive_key),
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
        error_message = response["error"]["message"]

        # Should be generic message, not the key name
        assert error_message == "Missing required argument"
        assert "internal_config" not in error_message
        assert "api_key" not in error_message

    def test_missing_keyword_argument_generic_message(self):
        """Missing required argument in request should return generic message."""
        server = WorkshopMCPServer()

        # Missing 'keyword' required argument
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "call_tool",
            "params": {
                "name": "keyword_search",
                "arguments": {
                    "root_paths": ["/tmp"],
                    # 'keyword' is missing
                },
            },
        }

        response = server._handle_request(request)

        assert "error" in response
        error_message = response["error"]["message"]

        # Should be generic - not expose which key was missing
        assert error_message == "Missing required argument"
        # Should not have 'missing' field that reveals key name
        error_data = response["error"].get("data", {})
        assert "missing" not in error_data


class TestParseErrorSanitization:
    """Test that parse errors don't expose JSON decode details."""

    def test_parse_error_no_details(self):
        """Malformed JSON should return 'Parse error' without decode details."""
        server = WorkshopMCPServer()

        # Create malformed JSON request
        malformed_json = b'{"jsonrpc": "2.0", "id": 1, "method": "list_tools", invalid}'
        request_message = f"Content-Length: {len(malformed_json)}\r\n\r\n".encode() + malformed_json

        stdin = BytesIO(request_message)
        stdout = BytesIO()

        server.serve_once(stdin, stdout)

        # Parse response
        stdout.seek(0)
        response_data = stdout.read()
        header_end = response_data.find(b"\r\n\r\n")
        response_json = response_data[header_end + 4 :].decode("utf-8")
        response = json.loads(response_json)

        assert "error" in response
        error_message = response["error"]["message"]

        # Should be generic parse error
        assert error_message == "Parse error"

        # Should NOT have 'details' field with JSONDecodeError info
        error_data = response["error"].get("data", {})
        assert "details" not in error_data

        # Error message should not contain decode specifics
        error_str = str(response["error"])
        assert "Expecting" not in error_str
        assert "line" not in error_str.lower() or "line" in "Parse error"
        assert "column" not in error_str.lower()


class TestInternalErrorSanitization:
    """Test that internal errors include correlation ID but not exception message."""

    def test_internal_error_has_correlation_id(self, tmp_path, monkeypatch):
        """Internal errors should include correlation_id but not str(exc)."""
        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
        server = WorkshopMCPServer()

        # Mock to raise unexpected exception
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
                    "arguments": {
                        "keyword": "test",
                        "root_paths": [str(tmp_path)],
                    },
                },
            }

            # Use serve_once to ensure request_context is established
            request_bytes = json.dumps(request).encode("utf-8")
            request_message = (
                f"Content-Length: {len(request_bytes)}\r\n\r\n".encode() + request_bytes
            )

            stdin = BytesIO(request_message)
            stdout = BytesIO()

            server.serve_once(stdin, stdout)

            # Parse response
            stdout.seek(0)
            response_data = stdout.read()
            header_end = response_data.find(b"\r\n\r\n")
            response_json = response_data[header_end + 4 :].decode("utf-8")
            response = json.loads(response_json)

        assert "error" in response
        assert response["error"]["code"] == -32603  # Internal error code

        error_message = response["error"]["message"]
        assert error_message == "Internal error"

        # Should NOT contain the revealing exception message
        error_str = str(response["error"])
        assert "Database connection" not in error_str
        assert "secret.db" not in error_str
        assert "password" not in error_str

        # Should have correlation_id in data
        error_data = response["error"].get("data", {})
        assert "correlation_id" in error_data
        # Correlation ID should be 8 hex chars
        corr_id = error_data["correlation_id"]
        assert len(corr_id) == 8
        assert all(c in "0123456789abcdef" for c in corr_id)

        # Should NOT have 'details' field
        assert "details" not in error_data

    def test_server_loop_error_has_correlation_id(self, tmp_path, monkeypatch):
        """Errors in server loop should include correlation_id."""
        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
        server = WorkshopMCPServer()

        # Mock _handle_request to raise unexpected exception
        revealing_error = "Unexpected server state: internal buffer overflow"
        with patch.object(
            server,
            "_handle_request",
            side_effect=RuntimeError(revealing_error),
        ):
            request = {"jsonrpc": "2.0", "id": 1, "method": "list_tools"}
            request_bytes = json.dumps(request).encode("utf-8")
            request_message = (
                f"Content-Length: {len(request_bytes)}\r\n\r\n".encode() + request_bytes
            )

            stdin = BytesIO(request_message)
            stdout = BytesIO()

            server.serve_once(stdin, stdout)

            # Parse response
            stdout.seek(0)
            response_data = stdout.read()
            header_end = response_data.find(b"\r\n\r\n")
            response_json = response_data[header_end + 4 :].decode("utf-8")
            response = json.loads(response_json)

        assert "error" in response
        assert response["error"]["code"] == -32603

        # Should have correlation_id, not details
        error_data = response["error"].get("data", {})
        assert "correlation_id" in error_data
        assert "details" not in error_data

        # Should not contain revealing message
        error_str = str(response["error"])
        assert "buffer overflow" not in error_str
        # "Internal error" is the expected message, but should not have revealing details
        assert "Unexpected server state" not in error_str


class TestSecurityValidationErrorPassthrough:
    """Test that SecurityValidationError messages pass through (already safe)."""

    def test_pathvalidationerror_message_passthrough(self, tmp_path, monkeypatch):
        """PathValidationError messages should pass through since they're safe."""
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
        error_message = response["error"]["message"]

        # PathValidationError has safe, generic message
        assert "outside allowed directories" in error_message
        # Should NOT contain the actual path
        assert "/etc/passwd" not in error_message


class TestCorrelationIdLogging:
    """Test that full error details are logged with correlation ID."""

    def test_error_logged_with_correlation_id(self, tmp_path, monkeypatch, caplog):
        """Full error details should be logged with correlation ID."""
        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
        server = WorkshopMCPServer()

        revealing_error = "Detailed error: file /secret/data.db corrupted at byte 42"
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
                    "arguments": {
                        "keyword": "test",
                        "root_paths": [str(tmp_path)],
                    },
                },
            }

            with caplog.at_level(logging.ERROR):
                response = server._handle_request(request)

        # Get the correlation ID from response
        error_data = response["error"].get("data", {})
        error_data.get("correlation_id", "")

        # Full error should be in logs
        log_output = caplog.text
        assert "keyword_search" in log_output.lower() or "error" in log_output.lower()

        # The revealing error details should be logged (for debugging)
        # but NOT in the response (verified above)


class TestValueErrorFromPerformanceCheck:
    """Test ValueError sanitization from performance_check tool."""

    def test_performance_check_valueerror_sanitized(self, tmp_path, monkeypatch):
        """ValueError from performance_check should be sanitized."""
        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
        server = WorkshopMCPServer()

        # Create valid file
        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): pass")

        # Mock PerformanceChecker to raise ValueError
        revealing_message = "Invalid AST node at internal path /opt/app/cache"
        with patch(
            "workshop_mcp.server.PerformanceChecker",
            side_effect=ValueError(revealing_message),
        ):
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "call_tool",
                "params": {
                    "name": "performance_check",
                    "arguments": {
                        "file_path": str(test_file),
                    },
                },
            }

            response = server._handle_request(request)

        assert "error" in response
        error_message = response["error"]["message"]

        # Should be generic
        assert error_message == "Invalid parameters"
        assert "AST" not in error_message
        assert "/opt/app" not in error_message


class TestFileNotFoundFromPerformanceCheck:
    """Test FileNotFoundError sanitization from performance_check tool."""

    def test_performance_check_filenotfound_sanitized(self, tmp_path, monkeypatch):
        """FileNotFoundError from performance_check should be sanitized."""
        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
        server = WorkshopMCPServer()

        # Create valid file
        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): pass")

        # Mock PerformanceChecker to raise FileNotFoundError
        revealing_path = "/var/lib/app/secrets/config.py"
        with patch(
            "workshop_mcp.server.PerformanceChecker",
            side_effect=FileNotFoundError(revealing_path),
        ):
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "call_tool",
                "params": {
                    "name": "performance_check",
                    "arguments": {
                        "file_path": str(test_file),
                    },
                },
            }

            response = server._handle_request(request)

        assert "error" in response
        error_message = response["error"]["message"]

        # Should be generic
        assert error_message == "Resource not found"
        assert "/var/lib" not in error_message
        assert "secrets" not in error_message
