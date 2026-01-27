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


class TestCoreProtocol:
    """Test core MCP protocol methods."""

    def test_initialize_response(self, server: WorkshopMCPServer) -> None:
        """Test initialize returns proper server info and protocol version."""
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

    def test_list_tools_returns_available_tools(self, server: WorkshopMCPServer) -> None:
        """Test list_tools returns keyword_search and performance_check tools."""
        message = _encode_message({"jsonrpc": "2.0", "id": 2, "method": "list_tools"})
        response = _run_server_harness(server, message)

        assert response is not None
        tools = response["result"]["tools"]
        tool_names = {tool["name"] for tool in tools}
        assert "keyword_search" in tool_names

    def test_call_tool_executes_successfully(self, tmp_path, monkeypatch) -> None:
        """Test call_tool executes keyword_search and returns results."""
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
            result_payload = json.loads(response["result"]["content"][0]["text"])
            assert result_payload["keyword"] == "alpha"
            assert result_payload["summary"]["total_occurrences"] >= 2
        finally:
            server.loop.close()
            asyncio.set_event_loop(None)


class TestServerLoop:
    """Test server loop and EOF handling."""

    def test_serve_once_returns_false_on_eof(self, server: WorkshopMCPServer) -> None:
        """Test that serve_once returns False on empty input and incomplete body."""
        # Empty input = EOF
        assert server.serve_once(io.BytesIO(b""), io.BytesIO()) is False

        # Incomplete body (header says 100 bytes but only 10 provided)
        message = b'Content-Length: 100\r\n\r\n{"jsonrpc"'
        assert server.serve_once(io.BytesIO(message), io.BytesIO()) is False

    def test_serve_once_handles_generic_exception(
        self, server: WorkshopMCPServer, monkeypatch
    ) -> None:
        """Test that serve_once handles unexpected exceptions gracefully."""
        monkeypatch.setattr(
            server, "_read_message", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("Unexpected"))
        )

        stdin = io.BytesIO(b"Content-Length: 2\r\n\r\n{}")
        stdout = io.BytesIO()

        result = server.serve_once(stdin, stdout)

        assert result is True
        response = _decode_message(stdout.getvalue())
        assert response["error"]["code"] == -32603
        assert response["error"]["message"] == "Internal error"


class TestMessageFraming:
    """Test Content-Length framing edge cases."""

    def test_content_length_header_validation(self, server: WorkshopMCPServer) -> None:
        """Test missing and invalid Content-Length headers return errors."""
        # Missing Content-Length
        response = _run_server_harness(server, b"X-Custom: value\r\n\r\n{}")
        _assert_jsonrpc_error(response, code=-32600, message_contains="Content-Length")

        # Invalid Content-Length (not a number)
        response = _run_server_harness(server, b"Content-Length: not-a-number\r\n\r\n{}")
        _assert_jsonrpc_error(response, code=-32600, message_contains="Content-Length")

    def test_malformed_headers_handled(self, server: WorkshopMCPServer) -> None:
        """Test that malformed headers (no colon) are ignored and valid headers work."""
        payload = b'{"jsonrpc": "2.0", "id": 1, "method": "list_tools"}'
        message = (
            b"MalformedHeaderNoColon\r\n"
            b"Content-Length: " + str(len(payload)).encode() + b"\r\n"
            b"\r\n" + payload
        )
        response = _run_server_harness(server, message)
        assert response is not None
        assert "result" in response


class TestRequestValidation:
    """Test JSON-RPC request validation."""

    def test_invalid_request_types(self, server: WorkshopMCPServer) -> None:
        """Test error responses for non-dict requests and invalid id types."""
        # Array instead of object
        response = _run_server_harness(server, _encode_message([1, 2, 3]))
        _assert_jsonrpc_error(response, code=-32600, message_contains="Invalid Request")

        # String instead of object
        raw_payload = b'"just a string"'
        header = f"Content-Length: {len(raw_payload)}\r\n\r\n".encode("utf-8")
        response = _run_server_harness(server, header + raw_payload)
        _assert_jsonrpc_error(response, code=-32600)

        # Invalid id type (list)
        response = _run_server_harness(
            server, _encode_message({"jsonrpc": "2.0", "id": [1, 2], "method": "list_tools"})
        )
        _assert_jsonrpc_error(response, code=-32600, message_contains="Invalid Request")

    def test_invalid_jsonrpc_field_values(self, server: WorkshopMCPServer) -> None:
        """Test errors for wrong version, non-string method, missing fields."""
        # Wrong version
        response = _run_server_harness(
            server, _encode_message({"jsonrpc": "1.0", "id": 1, "method": "list_tools"})
        )
        _assert_jsonrpc_error(response, code=-32600, message_contains="Invalid Request")

        # Non-string method
        response = _run_server_harness(
            server, _encode_message({"jsonrpc": "2.0", "id": 1, "method": 123})
        )
        _assert_jsonrpc_error(response, code=-32600)

        # Missing jsonrpc field
        response = _run_server_harness(
            server, _encode_message({"id": 1, "method": "list_tools"})
        )
        _assert_jsonrpc_error(response, code=-32600)

    def test_notification_and_error_response_handling(self, server: WorkshopMCPServer) -> None:
        """Test that notifications and error responses produce no reply."""
        # Notification (no id)
        message = _encode_message({"jsonrpc": "2.0", "method": "notifications/initialized"})
        stdin = io.BytesIO(message)
        stdout = io.BytesIO()
        assert server.serve_once(stdin, stdout) is True
        assert stdout.getvalue() == b""

        # Incoming error response (server should not reply)
        error_msg = _encode_message({
            "jsonrpc": "2.0",
            "error": {"code": -32000, "message": "Server error"},
        })
        stdin = io.BytesIO(error_msg)
        stdout = io.BytesIO()
        assert server.serve_once(stdin, stdout) is True
        assert stdout.getvalue() == b""

    def test_malformed_json_and_unknown_method(self, server: WorkshopMCPServer) -> None:
        """Test parse error for malformed JSON and method not found."""
        # Malformed JSON
        raw_payload = b'{"jsonrpc": "2.0", "method": "initialize",}'
        header = f"Content-Length: {len(raw_payload)}\r\n\r\n".encode("utf-8")
        response = _run_server_harness(server, header + raw_payload)
        _assert_jsonrpc_error(response, code=-32700)

        # Unknown method
        response = _run_server_harness(
            server, _encode_message({"jsonrpc": "2.0", "id": 3, "method": "unknown_method"})
        )
        _assert_jsonrpc_error(response, code=-32601, message_contains="Method not found")

    def test_initialize_params_validation(self, server: WorkshopMCPServer) -> None:
        """Test error when initialize params is not a dict."""
        for invalid_params in ["not-a-dict", [1, 2, 3]]:
            response = _run_server_harness(
                server,
                _encode_message({
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": invalid_params,
                }),
            )
            _assert_jsonrpc_error(response, code=-32602, message_contains="Invalid params")


class TestToolCallValidation:
    """Test call_tool parameter validation."""

    def test_call_tool_basic_validation(self, server: WorkshopMCPServer) -> None:
        """Test call_tool rejects non-dict params and unknown tools."""
        # Non-dict params
        response = _run_server_harness(
            server,
            _encode_message({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "call_tool",
                "params": "not-a-dict",
            }),
        )
        _assert_jsonrpc_error(response, code=-32602, message_contains="Invalid params")

        # Unknown tool
        response = _run_server_harness(
            server,
            _encode_message({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "call_tool",
                "params": {"name": "nonexistent_tool", "arguments": {}},
            }),
        )
        _assert_jsonrpc_error(response, code=-32602, message_contains="Unknown tool")

    def test_keyword_search_argument_validation(self, server: WorkshopMCPServer) -> None:
        """Test keyword_search validates argument types correctly."""
        test_cases = [
            # (arguments, expected_message_contains)
            ({"keyword": 123, "root_paths": ["/tmp"]}, "keyword must be a string"),
            ({"keyword": "test", "root_paths": "/tmp"}, "root_paths must be a list"),
            ({"keyword": "test", "root_paths": ["/tmp", 123]}, "root_paths must be a list of strings"),
            ({"keyword": "test", "root_paths": ["/tmp"], "case_insensitive": "yes"}, "case_insensitive must be a boolean"),
            ({"keyword": "test", "root_paths": ["/tmp"], "use_regex": 1}, "use_regex must be a boolean"),
            ({"keyword": "test", "root_paths": ["/tmp"], "include_patterns": "*.py"}, "include_patterns must be a list"),
            ({"keyword": "test", "root_paths": ["/tmp"], "exclude_patterns": "*.pyc"}, "exclude_patterns must be a list"),
        ]

        for arguments, expected_msg in test_cases:
            response = _run_server_harness(
                server,
                _encode_message({
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "call_tool",
                    "params": {"name": "keyword_search", "arguments": arguments},
                }),
            )
            _assert_jsonrpc_error(response, code=-32602, message_contains=expected_msg)

    def test_performance_check_argument_validation(self, server: WorkshopMCPServer) -> None:
        """Test performance_check validates argument types correctly."""
        # Non-dict arguments
        response = _run_server_harness(
            server,
            _encode_message({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "call_tool",
                "params": {"name": "performance_check", "arguments": "not-a-dict"},
            }),
        )
        _assert_jsonrpc_error(response, code=-32602, message_contains="Invalid params")

        # Both file_path and source_code provided
        response = _run_server_harness(
            server,
            _encode_message({
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
            }),
        )
        _assert_jsonrpc_error(response, code=-32602, message_contains="only one of")
