"""Integration tests for the MCP server with performance profiler."""

import json
from io import BytesIO
from pathlib import Path

import pytest

from workshop_mcp.server import WorkshopMCPServer


class TestMCPServerIntegration:
    """Test MCP server integration with performance profiler."""

    def test_initialize(self):
        """Test server initialization."""
        server = WorkshopMCPServer()
        assert server.keyword_search_tool is not None
        assert server.loop is not None

    def test_list_tools_includes_performance_check(self):
        """Test that list_tools includes both keyword_search and performance_check."""
        server = WorkshopMCPServer()

        # Create a request
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "list_tools",
        }

        # Handle the request
        response = server._handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert "tools" in response["result"]

        tools = response["result"]["tools"]
        assert len(tools) == 2

        # Check that both tools are present
        tool_names = [tool["name"] for tool in tools]
        assert "keyword_search" in tool_names
        assert "performance_check" in tool_names

        # Check performance_check tool details
        perf_tool = next(t for t in tools if t["name"] == "performance_check")
        assert "description" in perf_tool
        assert "performance anti-patterns" in perf_tool["description"].lower()
        assert "inputSchema" in perf_tool
        assert perf_tool["inputSchema"]["type"] == "object"
        assert "properties" in perf_tool["inputSchema"]
        assert "file_path" in perf_tool["inputSchema"]["properties"]
        assert "source_code" in perf_tool["inputSchema"]["properties"]


class TestPerformanceCheckTool:
    """Test the performance_check tool execution."""

    def test_performance_check_with_source_code(self):
        """Test performance check with source code."""
        server = WorkshopMCPServer()

        source_code = """
import time

async def bad_async():
    time.sleep(1)
    with open('file.txt') as f:
        data = f.read()
"""

        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "call_tool",
            "params": {
                "name": "performance_check",
                "arguments": {
                    "source_code": source_code,
                },
            },
        }

        response = server._handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 2
        assert "result" in response

        # Parse the result
        content = response["result"]["content"]
        assert len(content) == 1
        assert content[0]["type"] == "json"

        result_data = content[0]["json"]
        assert "summary" in result_data
        assert "issues" in result_data

        # Should detect blocking I/O in async
        assert result_data["summary"]["total_issues"] >= 2
        assert result_data["summary"]["by_severity"]["critical"] >= 2

        # Check that issues have expected structure
        for issue in result_data["issues"]:
            assert "category" in issue
            assert "severity" in issue
            assert "line_number" in issue
            assert "description" in issue
            assert "suggestion" in issue

    def test_performance_check_with_file_path(self, tmp_path):
        """Test performance check with file path."""
        server = WorkshopMCPServer()

        # Create a temporary Python file
        test_file = tmp_path / "test_code.py"
        test_file.write_text("""
for user in User.objects.all():
    print(user.profile.name)
""")

        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "call_tool",
            "params": {
                "name": "performance_check",
                "arguments": {
                    "file_path": str(test_file),
                },
            },
        }

        response = server._handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 3
        assert "result" in response

        # Parse the result
        content = response["result"]["content"]
        result_data = content[0]["json"]

        # Should detect N+1 query
        assert result_data["summary"]["total_issues"] >= 1
        assert any(
            issue["category"] == "n_plus_one_query"
            for issue in result_data["issues"]
        )

    def test_performance_check_with_clean_code(self):
        """Test performance check with code that has no issues."""
        server = WorkshopMCPServer()

        source_code = """
def clean_function():
    return "Hello, World!"
"""

        request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "call_tool",
            "params": {
                "name": "performance_check",
                "arguments": {
                    "source_code": source_code,
                },
            },
        }

        response = server._handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 4
        assert "result" in response

        # Parse the result
        content = response["result"]["content"]
        result_data = content[0]["json"]

        # Should have no issues
        assert result_data["summary"]["total_issues"] == 0
        assert len(result_data["issues"]) == 0

    def test_performance_check_missing_params(self):
        """Test error when no file_path or source_code provided."""
        server = WorkshopMCPServer()

        request = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "call_tool",
            "params": {
                "name": "performance_check",
                "arguments": {},
            },
        }

        response = server._handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 5
        assert "error" in response
        assert response["error"]["code"] == -32602
        assert "file_path or source_code" in response["error"]["message"]

    def test_performance_check_invalid_file_path(self):
        """Test error when file_path doesn't exist."""
        server = WorkshopMCPServer()

        request = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "call_tool",
            "params": {
                "name": "performance_check",
                "arguments": {
                    "file_path": "/nonexistent/path/to/file.py",
                },
            },
        }

        response = server._handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 6
        assert "error" in response
        assert response["error"]["code"] == -32602

    def test_performance_check_syntax_error(self):
        """Test error when source code has syntax errors."""
        server = WorkshopMCPServer()

        source_code = """
def bad_syntax(
    # Missing closing parenthesis
"""

        request = {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "call_tool",
            "params": {
                "name": "performance_check",
                "arguments": {
                    "source_code": source_code,
                },
            },
        }

        response = server._handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 7
        assert "error" in response
        assert response["error"]["code"] == -32602

    def test_performance_check_invalid_argument_types(self):
        """Test error when arguments have wrong types.

        Note: Type validation is expected to be handled by JSON-RPC schema
        validation. Invalid types will fail in the underlying code.
        """
        server = WorkshopMCPServer()

        # Test with file_path as non-string - will fail in PerformanceChecker
        request = {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "call_tool",
            "params": {
                "name": "performance_check",
                "arguments": {
                    "file_path": 123,  # Should be string
                },
            },
        }

        response = server._handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 8
        assert "error" in response
        # Error will be raised from underlying code, not explicit type check


class TestMCPServerFraming:
    """Test MCP server framing and message handling."""

    def test_serve_once_with_performance_check(self, tmp_path):
        """Test serve_once with a performance check request."""
        server = WorkshopMCPServer()

        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("async def test(): open('file.txt')")

        # Create a request
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

        request_json = json.dumps(request)
        request_bytes = request_json.encode("utf-8")
        request_message = f"Content-Length: {len(request_bytes)}\r\n\r\n".encode("utf-8") + request_bytes

        # Create mock stdin and stdout
        stdin = BytesIO(request_message)
        stdout = BytesIO()

        # Process one message
        result = server.serve_once(stdin, stdout)

        assert result is True

        # Parse the response
        stdout.seek(0)
        response_data = stdout.read()

        # Extract the JSON response (after Content-Length header)
        header_end = response_data.find(b"\r\n\r\n")
        response_json = response_data[header_end + 4:].decode("utf-8")
        response = json.loads(response_json)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response

        # Parse the result
        content = response["result"]["content"]
        result_data = content[0]["json"]

        # Should detect blocking I/O in async
        assert result_data["summary"]["total_issues"] >= 1
        assert any(
            issue["category"] == "blocking_io_in_async"
            for issue in result_data["issues"]
        )
