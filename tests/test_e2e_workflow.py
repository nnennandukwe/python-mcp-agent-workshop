"""End-to-End workflow tests for the performance profiler.

These tests validate the complete workflow from MCP server through
analysis and result formatting using realistic test fixtures.
"""

import json
from io import BytesIO
from pathlib import Path

from workshop_mcp.server import WorkshopMCPServer

FIXTURES_DIR = Path(__file__).parent.parent / "test_fixtures"


class TestPerformanceAnalysis:
    """Test performance analysis E2E workflows."""

    def test_analyze_bad_performance_file_detects_issues(self):
        """Test analysis of file with multiple performance anti-patterns."""
        server = WorkshopMCPServer()
        fixture_path = FIXTURES_DIR / "sample_bad_performance.py"

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "call_tool",
            "params": {"name": "performance_check", "arguments": {"file_path": str(fixture_path)}},
        }
        response = server._handle_request(request)

        assert "result" in response
        result = response["result"]["content"][0]["json"]

        # Verify structure
        assert "summary" in result and "issues" in result
        summary = result["summary"]
        assert "total_issues" in summary and "by_severity" in summary

        # Should detect multiple issues including critical ones
        assert summary["total_issues"] >= 5
        assert summary["by_severity"]["critical"] >= 1

        # Verify issue structure
        for issue in result["issues"]:
            assert all(
                field in issue
                for field in ["category", "severity", "line_number", "description", "suggestion"]
            )

        # Should detect key categories
        detected = {issue["category"] for issue in result["issues"]}
        assert "blocking_io_in_async" in detected

    def test_analyze_clean_code_returns_zero_issues(self):
        """Test that simple, clean code has zero issues."""
        server = WorkshopMCPServer()

        source_code = """
def calculate_sum(numbers):
    return sum(numbers)

class Calculator:
    def add(self, a, b):
        return a + b
"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "call_tool",
            "params": {"name": "performance_check", "arguments": {"source_code": source_code}},
        }
        response = server._handle_request(request)
        result = response["result"]["content"][0]["json"]

        assert result["summary"]["total_issues"] == 0
        assert len(result["issues"]) == 0

    def test_analyze_source_code_with_blocking_io_in_async(self):
        """Test analysis detects blocking I/O in async functions."""
        server = WorkshopMCPServer()

        source_code = """
import time

async def problematic_function():
    time.sleep(1)  # Blocking!
    with open("data.txt") as f:
        data = f.read()  # Also blocking!
    return data
"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "call_tool",
            "params": {"name": "performance_check", "arguments": {"source_code": source_code}},
        }
        response = server._handle_request(request)
        result = response["result"]["content"][0]["json"]

        assert result["summary"]["total_issues"] >= 2
        assert result["summary"]["by_severity"]["critical"] >= 2
        assert "blocking_io_in_async" in [i["category"] for i in result["issues"]]


class TestErrorHandling:
    """Test error handling for invalid inputs."""

    def test_invalid_file_path_returns_error(self):
        """Test error response for non-existent file."""
        server = WorkshopMCPServer()

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "call_tool",
            "params": {
                "name": "performance_check",
                "arguments": {"file_path": "/nonexistent/path/file.py"},
            },
        }
        response = server._handle_request(request)

        assert "error" in response
        assert response["error"]["code"] == -32602

    def test_syntax_error_returns_error(self):
        """Test error response for code with syntax errors."""
        server = WorkshopMCPServer()

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "call_tool",
            "params": {"name": "performance_check", "arguments": {"source_code": "def broken(\n"}},
        }
        response = server._handle_request(request)

        assert "error" in response
        assert response["error"]["code"] == -32602

    def test_missing_and_conflicting_params_return_error(self):
        """Test errors when params are missing or both provided."""
        server = WorkshopMCPServer()

        # Missing both
        response = server._handle_request(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "call_tool",
                "params": {"name": "performance_check", "arguments": {}},
            }
        )
        assert "error" in response and "file_path or source_code" in response["error"]["message"]

        # Both provided
        response = server._handle_request(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "call_tool",
                "params": {
                    "name": "performance_check",
                    "arguments": {"file_path": "/path.py", "source_code": "pass"},
                },
            }
        )
        assert (
            "error" in response
            and "only one of file_path or source_code" in response["error"]["message"]
        )


class TestMCPProtocolCompliance:
    """Test MCP protocol compliance in E2E scenarios."""

    def test_list_tools_returns_performance_check(self):
        """Verify list_tools includes performance_check with proper schema."""
        server = WorkshopMCPServer()

        request = {"jsonrpc": "2.0", "id": 1, "method": "list_tools"}
        response = server._handle_request(request)

        tools = response["result"]["tools"]
        perf_tool = next(t for t in tools if t["name"] == "performance_check")

        assert "description" in perf_tool
        assert "inputSchema" in perf_tool
        assert "file_path" in perf_tool["inputSchema"]["properties"]
        assert "source_code" in perf_tool["inputSchema"]["properties"]

    def test_framed_request_response_cycle(self):
        """Test complete framed request/response cycle."""
        server = WorkshopMCPServer()
        fixture_path = FIXTURES_DIR / "sample_bad_performance.py"

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "call_tool",
            "params": {"name": "performance_check", "arguments": {"file_path": str(fixture_path)}},
        }
        request_bytes = json.dumps(request).encode("utf-8")
        framed = f"Content-Length: {len(request_bytes)}\r\n\r\n".encode() + request_bytes

        stdin = BytesIO(framed)
        stdout = BytesIO()
        assert server.serve_once(stdin, stdout) is True

        stdout.seek(0)
        response_data = stdout.read()
        header_end = response_data.find(b"\r\n\r\n")
        response = json.loads(response_data[header_end + 4 :].decode("utf-8"))

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
