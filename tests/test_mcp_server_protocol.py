"""
Tests for MCP JSON-RPC protocol handling over stdio.

These tests exercise the WorkshopMCPServer stdio framing, JSON-RPC
request handling, and error responses without relying on the MCP SDK.
"""

import io
import json
from typing import Any, Dict, Optional

import pytest

from workshop_mcp.server import WorkshopMCPServer


def _encode_message(payload: Dict[str, Any]) -> bytes:
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


@pytest.fixture
def server() -> WorkshopMCPServer:
    instance = WorkshopMCPServer()
    yield instance
    instance.loop.close()


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


def test_invalid_method_returns_error(server: WorkshopMCPServer) -> None:
    message = _encode_message({"jsonrpc": "2.0", "id": 3, "method": "unknown_method"})
    response = _run_server_harness(server, message)

    assert response is not None
    assert response["error"]["code"] == -32601
    assert "Method not found" in response["error"]["message"]


def test_malformed_json_returns_parse_error(server: WorkshopMCPServer) -> None:
    raw_payload = b'{"jsonrpc": "2.0", "method": "initialize",}'
    header = f"Content-Length: {len(raw_payload)}\r\n\r\n".encode("utf-8")
    message = header + raw_payload

    response = _run_server_harness(server, message)

    assert response is not None
    assert response["error"]["code"] == -32700
