"""
Tests for MCP JSON-RPC protocol handling over stdio.

These tests exercise the WorkshopMCPServer stdio framing, JSON-RPC
request handling, and error responses without relying on the MCP SDK.
"""

import asyncio
import io
import json
from typing import Any, Dict, Optional

import pytest

from workshop_mcp.server import WorkshopMCPServer


def _encode_message(payload: Any) -> bytes:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    header = f"Content-Length: {len(data)}\r\n\r\n".encode("utf-8")
    return header + data


def _decode_message(raw: bytes) -> Dict[str, Any]:
    header_blob, body = raw.split(b"\r\n\r\n", 1)

    content_length: Optional[int] = None
    for line in header_blob.decode("utf-8", errors="replace").split("\r\n"):
        if line.lower().startswith("content-length:"):
            content_length = int(line.split(":", 1)[1].strip())
            break

    assert content_length is not None
    return json.loads(body[:content_length].decode("utf-8"))


def _run_server_harness(
    server: WorkshopMCPServer, raw_message: bytes
) -> Optional[Dict[str, Any]]:
    stdin = io.BytesIO(raw_message)
    stdout = io.BytesIO()

    processed = server.serve_once(stdin, stdout)
    if not processed:
        return None

    stdout.seek(0)
    output = stdout.read()
    if not output:
        return None

    return _decode_message(output)


def _assert_jsonrpc_error(
    response: Optional[Dict[str, Any]],
    *,
    code: int,
    message_contains: str | None = None,
) -> None:
    assert response is not None
    assert response["error"]["code"] == code
    if message_contains is not None:
        assert message_contains in response["error"]["message"]


@pytest.fixture
def server() -> WorkshopMCPServer:
    instance = WorkshopMCPServer()
    yield instance
    instance.loop.close()
    asyncio.set_event_loop(None)


def test_initialize_response(server: WorkshopMCPServer) -> None:
    message = _encode_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"},
        }
    )
    response = _run_server_harness(server, message)

    assert response is not None
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert response["result"]["protocolVersion"] == "2024-11-05"
    assert response["result"]["serverInfo"]["name"] == "workshop-mcp-server"


def test_list_tools_response(server: WorkshopMCPServer) -> None:
    message = _encode_message({"jsonrpc": "2.0", "id": 2, "method": "list_tools"})
    response = _run_server_harness(server, message)

    assert response is not None
    tools = response["result"]["tools"]
    tool_names = {tool["name"] for tool in tools}
    assert "keyword_search" in tool_names


def test_call_tool_response(tmp_path, monkeypatch) -> None:
    # Set allowed roots BEFORE creating server
    monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
    server = WorkshopMCPServer()

    try:
        test_file = tmp_path / "sample.txt"
        test_file.write_text("alpha beta alpha", encoding="utf-8")

        message = _encode_message(
            {
                "jsonrpc": "2.0",
                "id": "call-1",
                "method": "call_tool",
                "params": {
                    "name": "keyword_search",
                    "arguments": {
                        "keyword": "alpha",
                        "root_paths": [str(tmp_path)],
                    },
                },
            }
        )
        response = _run_server_harness(server, message)

        assert response is not None
        assert response["id"] == "call-1"
        content = response["result"]["content"][0]
        assert content["type"] == "text"

        result_payload = json.loads(content["text"])
        assert result_payload["keyword"] == "alpha"
        assert str(tmp_path) in result_payload["root_paths"]
        assert result_payload["summary"]["total_occurrences"] >= 2
    finally:
        server.loop.close()
        asyncio.set_event_loop(None)


def test_invalid_method_returns_error(server: WorkshopMCPServer) -> None:
    message = _encode_message({"jsonrpc": "2.0", "id": 3, "method": "unknown_method"})
    response = _run_server_harness(server, message)

    _assert_jsonrpc_error(response, code=-32601, message_contains="Method not found")


def test_malformed_json_returns_parse_error(server: WorkshopMCPServer) -> None:
    raw_payload = b'{"jsonrpc": "2.0", "method": "initialize",}'
    header = f"Content-Length: {len(raw_payload)}\r\n\r\n".encode("utf-8")
    message = header + raw_payload

    response = _run_server_harness(server, message)

    _assert_jsonrpc_error(response, code=-32700)


# =============================================================================
# JsonRpcError tests
# =============================================================================


class TestJsonRpcError:
    """Tests for the JsonRpcError dataclass."""

    def test_str_returns_message(self) -> None:
        """Test that __str__ returns the error message."""
        from workshop_mcp.server import JsonRpcError

        error = JsonRpcError(code=-32600, message="Invalid Request")
        assert str(error) == "Invalid Request"

    def test_str_with_data(self) -> None:
        """Test __str__ with data field populated."""
        from workshop_mcp.server import JsonRpcError

        error = JsonRpcError(
            code=-32602, message="Invalid params", data={"expected": "object"}
        )
        assert str(error) == "Invalid params"


# =============================================================================
# Server loop and EOF handling tests
# =============================================================================


class TestServerLoop:
    """Tests for the main server loop and EOF handling."""

    def test_serve_once_returns_false_on_eof(self, server: WorkshopMCPServer) -> None:
        """Test that serve_once returns False when stdin reaches EOF."""
        stdin = io.BytesIO(b"")  # Empty input = EOF
        stdout = io.BytesIO()

        result = server.serve_once(stdin, stdout)

        assert result is False
        assert stdout.getvalue() == b""

    def test_serve_once_returns_false_on_incomplete_body(
        self, server: WorkshopMCPServer
    ) -> None:
        """Test that serve_once returns False when body is incomplete (EOF mid-message)."""
        # Header says 100 bytes but only 10 bytes provided
        message = b'Content-Length: 100\r\n\r\n{"jsonrpc"'
        stdin = io.BytesIO(message)
        stdout = io.BytesIO()

        result = server.serve_once(stdin, stdout)

        assert result is False

    def test_serve_once_handles_generic_exception(
        self, server: WorkshopMCPServer, monkeypatch
    ) -> None:
        """Test that serve_once handles unexpected exceptions gracefully."""

        def raise_error(*args, **kwargs):
            raise RuntimeError("Unexpected error")

        monkeypatch.setattr(server, "_read_message", raise_error)

        stdin = io.BytesIO(b"Content-Length: 2\r\n\r\n{}")
        stdout = io.BytesIO()

        result = server.serve_once(stdin, stdout)

        assert result is True
        response = _decode_message(stdout.getvalue())
        assert response["error"]["code"] == -32603
        assert response["error"]["message"] == "Internal error"


# =============================================================================
# Message framing edge cases
# =============================================================================


class TestMessageFraming:
    """Tests for Content-Length framing edge cases."""

    def test_missing_content_length_header(self, server: WorkshopMCPServer) -> None:
        """Test error when Content-Length header is missing."""
        # Only send header terminator without Content-Length
        message = b"X-Custom-Header: value\r\n\r\n{}"
        response = _run_server_harness(server, message)

        _assert_jsonrpc_error(response, code=-32600, message_contains="Content-Length")

    def test_invalid_content_length_header(self, server: WorkshopMCPServer) -> None:
        """Test error when Content-Length is not a valid integer."""
        message = b"Content-Length: not-a-number\r\n\r\n{}"
        response = _run_server_harness(server, message)

        _assert_jsonrpc_error(response, code=-32600, message_contains="Content-Length")

    def test_header_without_colon_ignored(self, server: WorkshopMCPServer) -> None:
        """Test that malformed headers without colon are ignored."""
        # Include a malformed header line (no colon) followed by valid Content-Length
        payload = b'{"jsonrpc": "2.0", "id": 1, "method": "list_tools"}'
        message = (
            b"MalformedHeaderNoColon\r\n"
            b"Content-Length: " + str(len(payload)).encode() + b"\r\n"
            b"\r\n" + payload
        )
        response = _run_server_harness(server, message)

        # Should still work - malformed header is skipped
        assert response is not None
        assert "result" in response

    def test_empty_header_line_terminates_headers(
        self, server: WorkshopMCPServer
    ) -> None:
        """Test that empty line (after stripping) terminates header parsing."""
        payload = b'{"jsonrpc": "2.0", "id": 1, "method": "list_tools"}'
        # Use just \n instead of \r\n for the empty line
        message = (
            b"Content-Length: " + str(len(payload)).encode() + b"\r\n" b"\n" + payload
        )
        response = _run_server_harness(server, message)

        assert response is not None
        assert "result" in response


# =============================================================================
# JSON-RPC request validation edge cases
# =============================================================================


class TestRequestValidation:
    """Tests for JSON-RPC request validation edge cases."""

    def test_request_not_a_dict(self, server: WorkshopMCPServer) -> None:
        """Test error when request is not a JSON object."""
        # Send a JSON array instead of object
        message = _encode_message([1, 2, 3])
        response = _run_server_harness(server, message)

        _assert_jsonrpc_error(response, code=-32600, message_contains="Invalid Request")

    def test_request_is_string(self, server: WorkshopMCPServer) -> None:
        """Test error when request is a string instead of object."""
        raw_payload = b'"just a string"'
        header = f"Content-Length: {len(raw_payload)}\r\n\r\n".encode("utf-8")
        message = header + raw_payload

        response = _run_server_harness(server, message)

        _assert_jsonrpc_error(response, code=-32600)

    def test_notification_returns_none(self, server: WorkshopMCPServer) -> None:
        """Test that notifications (no id field) return no response."""
        # Notification: has method but no id field at all
        message = _encode_message(
            {"jsonrpc": "2.0", "method": "notifications/initialized"}
        )
        stdin = io.BytesIO(message)
        stdout = io.BytesIO()

        result = server.serve_once(stdin, stdout)

        assert result is True
        # No response should be written for notifications
        assert stdout.getvalue() == b""

    def test_invalid_id_type_list(self, server: WorkshopMCPServer) -> None:
        """Test error when id is a list (invalid type)."""
        message = _encode_message(
            {"jsonrpc": "2.0", "id": [1, 2], "method": "list_tools"}
        )
        response = _run_server_harness(server, message)

        _assert_jsonrpc_error(response, code=-32600, message_contains="Invalid Request")

    def test_invalid_id_type_dict(self, server: WorkshopMCPServer) -> None:
        """Test error when id is a dict (invalid type)."""
        message = _encode_message(
            {"jsonrpc": "2.0", "id": {"nested": "id"}, "method": "list_tools"}
        )
        response = _run_server_harness(server, message)

        _assert_jsonrpc_error(response, code=-32600)

    def test_wrong_jsonrpc_version(self, server: WorkshopMCPServer) -> None:
        """Test error when jsonrpc version is not 2.0."""
        message = _encode_message({"jsonrpc": "1.0", "id": 1, "method": "list_tools"})
        response = _run_server_harness(server, message)

        _assert_jsonrpc_error(response, code=-32600, message_contains="Invalid Request")

    def test_method_not_string(self, server: WorkshopMCPServer) -> None:
        """Test error when method is not a string."""
        message = _encode_message({"jsonrpc": "2.0", "id": 1, "method": 123})
        response = _run_server_harness(server, message)

        _assert_jsonrpc_error(response, code=-32600)

    def test_missing_jsonrpc_field(self, server: WorkshopMCPServer) -> None:
        """Test error when jsonrpc field is missing."""
        message = _encode_message({"id": 1, "method": "list_tools"})
        response = _run_server_harness(server, message)

        _assert_jsonrpc_error(response, code=-32600)

    def test_error_response_ignored(self, server: WorkshopMCPServer) -> None:
        """Test that incoming error responses receive no reply per JSON-RPC 2.0 spec."""
        # An error response is not a request - server should not reply
        error_response = {
            "jsonrpc": "2.0",
            "error": {"code": -32000, "message": "Server error"},
        }
        message = _encode_message(error_response)
        stdin = io.BytesIO(message)
        stdout = io.BytesIO()

        result = server.serve_once(stdin, stdout)

        assert result is True
        # No response should be written for incoming error responses
        assert stdout.getvalue() == b""

    def test_initialize_with_non_dict_params(self, server: WorkshopMCPServer) -> None:
        """Test error when initialize params is not a dict."""
        message = _encode_message(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": "not-a-dict"}
        )
        response = _run_server_harness(server, message)

        _assert_jsonrpc_error(response, code=-32602, message_contains="Invalid params")

    def test_initialize_with_list_params(self, server: WorkshopMCPServer) -> None:
        """Test error when initialize params is a list."""
        message = _encode_message(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": [1, 2, 3]}
        )
        response = _run_server_harness(server, message)

        _assert_jsonrpc_error(response, code=-32602)


# =============================================================================
# Tool call parameter validation
# =============================================================================


class TestToolCallValidation:
    """Tests for call_tool parameter validation edge cases."""

    def test_call_tool_non_dict_params(self, server: WorkshopMCPServer) -> None:
        """Test error when call_tool params is not a dict."""
        message = _encode_message(
            {"jsonrpc": "2.0", "id": 1, "method": "call_tool", "params": "not-a-dict"}
        )
        response = _run_server_harness(server, message)

        _assert_jsonrpc_error(response, code=-32602, message_contains="Invalid params")

    def test_call_tool_unknown_tool(self, server: WorkshopMCPServer) -> None:
        """Test error when calling unknown tool."""
        message = _encode_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "call_tool",
                "params": {"name": "nonexistent_tool", "arguments": {}},
            }
        )
        response = _run_server_harness(server, message)

        _assert_jsonrpc_error(response, code=-32602, message_contains="Unknown tool")


class TestKeywordSearchValidation:
    """Tests for keyword_search argument validation."""

    def test_keyword_search_non_dict_arguments(self, server: WorkshopMCPServer) -> None:
        """Test error when keyword_search arguments is not a dict."""
        message = _encode_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "call_tool",
                "params": {"name": "keyword_search", "arguments": "not-a-dict"},
            }
        )
        response = _run_server_harness(server, message)

        _assert_jsonrpc_error(response, code=-32602)

    def test_keyword_not_string(self, server: WorkshopMCPServer) -> None:
        """Test error when keyword is not a string."""
        message = _encode_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "call_tool",
                "params": {
                    "name": "keyword_search",
                    "arguments": {"keyword": 123, "root_paths": ["/tmp"]},
                },
            }
        )
        response = _run_server_harness(server, message)

        _assert_jsonrpc_error(
            response, code=-32602, message_contains="keyword must be a string"
        )

    def test_root_paths_not_list(self, server: WorkshopMCPServer) -> None:
        """Test error when root_paths is not a list."""
        message = _encode_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "call_tool",
                "params": {
                    "name": "keyword_search",
                    "arguments": {"keyword": "test", "root_paths": "/tmp"},
                },
            }
        )
        response = _run_server_harness(server, message)

        _assert_jsonrpc_error(
            response, code=-32602, message_contains="root_paths must be a list"
        )

    def test_root_paths_contains_non_string(self, server: WorkshopMCPServer) -> None:
        """Test error when root_paths contains non-string elements."""
        message = _encode_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "call_tool",
                "params": {
                    "name": "keyword_search",
                    "arguments": {"keyword": "test", "root_paths": ["/tmp", 123]},
                },
            }
        )
        response = _run_server_harness(server, message)

        _assert_jsonrpc_error(
            response,
            code=-32602,
            message_contains="root_paths must be a list of strings",
        )

    def test_case_insensitive_not_boolean(self, server: WorkshopMCPServer) -> None:
        """Test error when case_insensitive is not a boolean."""
        message = _encode_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "call_tool",
                "params": {
                    "name": "keyword_search",
                    "arguments": {
                        "keyword": "test",
                        "root_paths": ["/tmp"],
                        "case_insensitive": "yes",
                    },
                },
            }
        )
        response = _run_server_harness(server, message)

        _assert_jsonrpc_error(
            response, code=-32602, message_contains="case_insensitive must be a boolean"
        )

    def test_use_regex_not_boolean(self, server: WorkshopMCPServer) -> None:
        """Test error when use_regex is not a boolean."""
        message = _encode_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "call_tool",
                "params": {
                    "name": "keyword_search",
                    "arguments": {
                        "keyword": "test",
                        "root_paths": ["/tmp"],
                        "use_regex": 1,
                    },
                },
            }
        )
        response = _run_server_harness(server, message)

        _assert_jsonrpc_error(
            response, code=-32602, message_contains="use_regex must be a boolean"
        )

    def test_include_patterns_not_list(self, server: WorkshopMCPServer) -> None:
        """Test error when include_patterns is not a list."""
        message = _encode_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "call_tool",
                "params": {
                    "name": "keyword_search",
                    "arguments": {
                        "keyword": "test",
                        "root_paths": ["/tmp"],
                        "include_patterns": "*.py",
                    },
                },
            }
        )
        response = _run_server_harness(server, message)

        _assert_jsonrpc_error(
            response, code=-32602, message_contains="include_patterns must be a list"
        )

    def test_include_patterns_contains_non_string(
        self, server: WorkshopMCPServer
    ) -> None:
        """Test error when include_patterns contains non-string elements."""
        message = _encode_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "call_tool",
                "params": {
                    "name": "keyword_search",
                    "arguments": {
                        "keyword": "test",
                        "root_paths": ["/tmp"],
                        "include_patterns": ["*.py", 123],
                    },
                },
            }
        )
        response = _run_server_harness(server, message)

        _assert_jsonrpc_error(
            response,
            code=-32602,
            message_contains="include_patterns must be a list of strings",
        )

    def test_exclude_patterns_not_list(self, server: WorkshopMCPServer) -> None:
        """Test error when exclude_patterns is not a list."""
        message = _encode_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "call_tool",
                "params": {
                    "name": "keyword_search",
                    "arguments": {
                        "keyword": "test",
                        "root_paths": ["/tmp"],
                        "exclude_patterns": "*.pyc",
                    },
                },
            }
        )
        response = _run_server_harness(server, message)

        _assert_jsonrpc_error(
            response, code=-32602, message_contains="exclude_patterns must be a list"
        )

    def test_exclude_patterns_contains_non_string(
        self, server: WorkshopMCPServer
    ) -> None:
        """Test error when exclude_patterns contains non-string elements."""
        message = _encode_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "call_tool",
                "params": {
                    "name": "keyword_search",
                    "arguments": {
                        "keyword": "test",
                        "root_paths": ["/tmp"],
                        "exclude_patterns": ["*.pyc", None],
                    },
                },
            }
        )
        response = _run_server_harness(server, message)

        _assert_jsonrpc_error(
            response,
            code=-32602,
            message_contains="exclude_patterns must be a list of strings",
        )


class TestPerformanceCheckValidation:
    """Tests for performance_check argument validation."""

    def test_performance_check_non_dict_arguments(
        self, server: WorkshopMCPServer
    ) -> None:
        """Test error when performance_check arguments is not a dict."""
        message = _encode_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "call_tool",
                "params": {"name": "performance_check", "arguments": "not-a-dict"},
            }
        )
        response = _run_server_harness(server, message)

        _assert_jsonrpc_error(response, code=-32602, message_contains="Invalid params")

    def test_performance_check_both_file_and_source(
        self, server: WorkshopMCPServer
    ) -> None:
        """Test error when both file_path and source_code are provided."""
        message = _encode_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "call_tool",
                "params": {
                    "name": "performance_check",
                    "arguments": {
                        "file_path": "/tmp/test.py",
                        "source_code": "print('hello')",
                    },
                },
            }
        )
        response = _run_server_harness(server, message)

        _assert_jsonrpc_error(response, code=-32602, message_contains="only one of")
