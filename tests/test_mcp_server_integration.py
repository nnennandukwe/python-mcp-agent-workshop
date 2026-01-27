"""Integration tests for the MCP server with performance profiler."""

import json
from io import BytesIO

import pytest

from workshop_mcp.server import WorkshopMCPServer


class TestMCPServerIntegration:
    """Test MCP server integration with tools."""

    def test_server_initialization_and_list_tools(self):
        """Test server initializes correctly and lists all tools."""
        server = WorkshopMCPServer()
        assert server.keyword_search_tool is not None
        assert server.loop is not None

        response = server._handle_request({"jsonrpc": "2.0", "id": 1, "method": "list_tools"})

        assert "result" in response
        tools = response["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        assert "keyword_search" in tool_names
        assert "performance_check" in tool_names

        # Verify performance_check schema
        perf_tool = next(t for t in tools if t["name"] == "performance_check")
        assert "performance anti-patterns" in perf_tool["description"].lower()
        assert "file_path" in perf_tool["inputSchema"]["properties"]

    def test_performance_check_with_source_code(self):
        """Test performance check detects issues in source code."""
        server = WorkshopMCPServer()

        source_code = """
import time
async def bad_async():
    time.sleep(1)
    with open('file.txt') as f:
        data = f.read()
"""
        request = {
            "jsonrpc": "2.0", "id": 1, "method": "call_tool",
            "params": {"name": "performance_check", "arguments": {"source_code": source_code}},
        }
        response = server._handle_request(request)

        assert "result" in response
        result = response["result"]["content"][0]["json"]
        assert result["summary"]["total_issues"] >= 2
        assert result["summary"]["by_severity"]["critical"] >= 2

    def test_performance_check_with_file_path(self, tmp_path, monkeypatch):
        """Test performance check with file path detects N+1 query."""
        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
        server = WorkshopMCPServer()

        test_file = tmp_path / "test.py"
        test_file.write_text("for user in User.objects.all():\n    print(user.profile.name)")

        request = {
            "jsonrpc": "2.0", "id": 1, "method": "call_tool",
            "params": {"name": "performance_check", "arguments": {"file_path": str(test_file)}},
        }
        response = server._handle_request(request)

        assert "result" in response
        result = response["result"]["content"][0]["json"]
        assert any(i["category"] == "n_plus_one_query" for i in result["issues"])

    def test_performance_check_clean_code_and_error_cases(self):
        """Test clean code returns no issues and error cases return proper errors."""
        server = WorkshopMCPServer()

        # Clean code
        response = server._handle_request({
            "jsonrpc": "2.0", "id": 1, "method": "call_tool",
            "params": {"name": "performance_check", "arguments": {"source_code": "def hello(): return 'world'"}},
        })
        assert response["result"]["content"][0]["json"]["summary"]["total_issues"] == 0

        # Missing params
        response = server._handle_request({
            "jsonrpc": "2.0", "id": 2, "method": "call_tool",
            "params": {"name": "performance_check", "arguments": {}},
        })
        assert response["error"]["code"] == -32602

        # Invalid file path
        response = server._handle_request({
            "jsonrpc": "2.0", "id": 3, "method": "call_tool",
            "params": {"name": "performance_check", "arguments": {"file_path": "/nonexistent.py"}},
        })
        assert response["error"]["code"] == -32602

        # Syntax error
        response = server._handle_request({
            "jsonrpc": "2.0", "id": 4, "method": "call_tool",
            "params": {"name": "performance_check", "arguments": {"source_code": "def bad(\n"}},
        })
        assert response["error"]["code"] == -32602

        # Invalid type
        response = server._handle_request({
            "jsonrpc": "2.0", "id": 5, "method": "call_tool",
            "params": {"name": "performance_check", "arguments": {"file_path": 123}},
        })
        assert "file_path must be a string" in response["error"]["message"]


class TestPathValidationIntegration:
    """Integration tests for path validation in MCP server."""

    def test_rejects_path_traversal_attacks(self, tmp_path, monkeypatch):
        """Test that path traversal attacks are blocked with generic messages."""
        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
        server = WorkshopMCPServer()

        malicious_paths = [
            ("/etc/passwd", "keyword_search", {"keyword": "root", "root_paths": ["/etc"]}),
            (str(tmp_path / ".." / ".." / "etc"), "keyword_search", {"keyword": "test", "root_paths": [str(tmp_path / ".." / ".." / "etc")]}),
            ("/etc/passwd", "performance_check", {"file_path": "/etc/passwd"}),
            (str(tmp_path / ".." / "etc" / "passwd"), "performance_check", {"file_path": str(tmp_path / ".." / "etc" / "passwd")}),
        ]

        for path, tool, args in malicious_paths:
            response = server._handle_request({
                "jsonrpc": "2.0", "id": 1, "method": "call_tool",
                "params": {"name": tool, "arguments": args},
            })
            assert "error" in response, f"Path {path} should be rejected"
            assert response["error"]["code"] == -32602
            # Error should be generic
            assert "etc" not in response["error"]["message"].lower() or "outside allowed" in response["error"]["message"]

    def test_accepts_valid_paths(self, tmp_path, monkeypatch):
        """Test that valid paths within allowed roots work."""
        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
        server = WorkshopMCPServer()

        test_file = tmp_path / "test.py"
        test_file.write_text("# hello world\ndef foo(): return 1")

        # keyword_search
        response = server._handle_request({
            "jsonrpc": "2.0", "id": 1, "method": "call_tool",
            "params": {"name": "keyword_search", "arguments": {"keyword": "hello", "root_paths": [str(tmp_path)]}},
        })
        assert "result" in response

        # performance_check
        response = server._handle_request({
            "jsonrpc": "2.0", "id": 2, "method": "call_tool",
            "params": {"name": "performance_check", "arguments": {"file_path": str(test_file)}},
        })
        assert "result" in response


class TestMCPServerFraming:
    """Test MCP server framing and message handling."""

    def test_serve_once_with_performance_check(self, tmp_path, monkeypatch):
        """Test serve_once with a performance check request."""
        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
        server = WorkshopMCPServer()

        test_file = tmp_path / "test.py"
        test_file.write_text("async def test(): open('file.txt')")

        request = {
            "jsonrpc": "2.0", "id": 1, "method": "call_tool",
            "params": {"name": "performance_check", "arguments": {"file_path": str(test_file)}},
        }
        request_bytes = json.dumps(request).encode("utf-8")
        request_message = f"Content-Length: {len(request_bytes)}\r\n\r\n".encode() + request_bytes

        stdin = BytesIO(request_message)
        stdout = BytesIO()
        assert server.serve_once(stdin, stdout) is True

        stdout.seek(0)
        response_data = stdout.read()
        header_end = response_data.find(b"\r\n\r\n")
        response = json.loads(response_data[header_end + 4:].decode("utf-8"))

        assert "result" in response
        result = response["result"]["content"][0]["json"]
        assert any(i["category"] == "blocking_io_in_async" for i in result["issues"])
