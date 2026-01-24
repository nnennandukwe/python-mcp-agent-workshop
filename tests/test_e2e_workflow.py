"""End-to-End workflow tests for the performance profiler.

These tests validate the complete workflow from MCP server through
analysis and result formatting using realistic test fixtures.
"""

import json
from io import BytesIO
from pathlib import Path

import pytest

from workshop_mcp.server import WorkshopMCPServer


# Path to test fixtures
FIXTURES_DIR = Path(__file__).parent.parent / "test_fixtures"


class TestBasicPerformanceAnalysis:
    """Scenario 1: Basic performance analysis with known issues."""

    def test_analyze_bad_performance_file(self):
        """Test analysis of file with multiple performance anti-patterns."""
        server = WorkshopMCPServer()
        fixture_path = FIXTURES_DIR / "sample_bad_performance.py"

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "call_tool",
            "params": {
                "name": "performance_check",
                "arguments": {"file_path": str(fixture_path)},
            },
        }

        response = server._handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert "error" not in response

        content = response["result"]["content"]
        assert len(content) == 1
        assert content[0]["type"] == "text"

        result = json.loads(content[0]["text"])

        # Verify summary structure
        assert "summary" in result
        assert "issues" in result

        summary = result["summary"]
        assert "total_issues" in summary
        assert "by_severity" in summary
        assert "by_category" in summary

        # Should detect multiple issues (blocking I/O, memory, loops)
        assert summary["total_issues"] >= 5, f"Expected at least 5 issues, got {summary['total_issues']}"

        # Should detect critical issues (blocking I/O in async)
        assert summary["by_severity"]["critical"] >= 1, "Expected at least 1 critical issue"

    def test_detected_issue_categories(self):
        """Verify key issue categories are detected."""
        server = WorkshopMCPServer()
        fixture_path = FIXTURES_DIR / "sample_bad_performance.py"

        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "call_tool",
            "params": {
                "name": "performance_check",
                "arguments": {"file_path": str(fixture_path)},
            },
        }

        response = server._handle_request(request)
        result = json.loads(response["result"]["content"][0]["text"])

        # Collect all detected categories
        detected_categories = set(issue["category"] for issue in result["issues"])

        # Should detect these categories (N+1 detection requires ORM context)
        # These are the categories we can reliably detect via static analysis
        expected_categories = {
            "blocking_io_in_async",
            "inefficient_loop",
            "memory_inefficiency",
        }

        for category in expected_categories:
            assert category in detected_categories, f"Expected to detect {category}"

    def test_issue_structure_completeness(self):
        """Verify each issue has all required fields."""
        server = WorkshopMCPServer()
        fixture_path = FIXTURES_DIR / "sample_bad_performance.py"

        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "call_tool",
            "params": {
                "name": "performance_check",
                "arguments": {"file_path": str(fixture_path)},
            },
        }

        response = server._handle_request(request)
        result = json.loads(response["result"]["content"][0]["text"])

        required_fields = {
            "category",
            "severity",
            "line_number",
            "end_line_number",
            "description",
            "suggestion",
            "code_snippet",
            "function_name",
        }

        for issue in result["issues"]:
            for field in required_fields:
                assert field in issue, f"Issue missing required field: {field}"

            # Validate field types
            assert isinstance(issue["category"], str)
            assert isinstance(issue["severity"], str)
            assert isinstance(issue["line_number"], int)
            assert issue["line_number"] > 0
            assert isinstance(issue["description"], str)
            assert len(issue["description"]) > 0
            assert isinstance(issue["suggestion"], str)
            assert len(issue["suggestion"]) > 0


class TestCleanCodeAnalysis:
    """Scenario 2: Clean code analysis with minimal/no issues."""

    def test_analyze_good_performance_file(self):
        """Test analysis of well-optimized code returns few issues.

        Note: Static analysis may flag some patterns that are actually fine
        in context (e.g., prefetched queries still show .all() calls).
        The profiler is conservative - it flags potential issues for human review.
        """
        server = WorkshopMCPServer()
        fixture_path = FIXTURES_DIR / "sample_good_performance.py"

        request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "call_tool",
            "params": {
                "name": "performance_check",
                "arguments": {"file_path": str(fixture_path)},
            },
        }

        response = server._handle_request(request)

        assert "result" in response
        assert "error" not in response

        result = json.loads(response["result"]["content"][0]["text"])

        # Should have zero critical issues (blocking I/O in async)
        # The good file uses proper async patterns
        assert result["summary"]["by_severity"]["critical"] == 0, (
            "Good performance file should have no critical issues"
        )

    def test_analyze_truly_clean_source_code(self):
        """Test that simple, clean code has zero issues."""
        server = WorkshopMCPServer()

        # Truly minimal clean code with no patterns that could be flagged
        source_code = '''
def calculate_sum(numbers):
    """Simple function with no performance issues."""
    return sum(numbers)

def greet(name):
    """Another simple function."""
    return f"Hello, {name}!"

class Calculator:
    """Simple class with no performance issues."""

    def add(self, a, b):
        return a + b

    def multiply(self, a, b):
        return a * b
'''

        request = {
            "jsonrpc": "2.0",
            "id": 40,
            "method": "call_tool",
            "params": {
                "name": "performance_check",
                "arguments": {"source_code": source_code},
            },
        }

        response = server._handle_request(request)
        result = json.loads(response["result"]["content"][0]["text"])

        # Truly clean code should have zero issues
        assert result["summary"]["total_issues"] == 0
        assert len(result["issues"]) == 0


class TestSourceCodeAnalysis:
    """Scenario 3: Analysis using source_code parameter."""

    def test_analyze_source_code_with_issues(self):
        """Test analysis with source_code parameter instead of file_path."""
        server = WorkshopMCPServer()

        source_code = '''
import time

async def problematic_function():
    """Async function with blocking I/O."""
    time.sleep(1)  # Blocking!
    with open("data.txt") as f:
        data = f.read()  # Also blocking!
    return data

def build_string_badly(items):
    result = ""
    for item in items:
        result = result + str(item)  # Inefficient!
    return result
'''

        request = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "call_tool",
            "params": {
                "name": "performance_check",
                "arguments": {"source_code": source_code},
            },
        }

        response = server._handle_request(request)

        assert "result" in response
        assert "error" not in response

        result = json.loads(response["result"]["content"][0]["text"])

        # Should detect issues in the provided source code
        assert result["summary"]["total_issues"] >= 2

        # Should detect blocking I/O in async (critical)
        assert result["summary"]["by_severity"]["critical"] >= 2

        # Verify we can identify issues by category
        categories = [issue["category"] for issue in result["issues"]]
        assert "blocking_io_in_async" in categories

    def test_analyze_clean_source_code(self):
        """Test analysis of clean source code."""
        server = WorkshopMCPServer()

        source_code = '''
def simple_calculation(a, b):
    """Simple function with no performance issues."""
    return a + b

def filter_items(items):
    """List comprehension is efficient."""
    return [x for x in items if x > 0]
'''

        request = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "call_tool",
            "params": {
                "name": "performance_check",
                "arguments": {"source_code": source_code},
            },
        }

        response = server._handle_request(request)
        result = json.loads(response["result"]["content"][0]["text"])

        # Should have no issues
        assert result["summary"]["total_issues"] == 0
        assert len(result["issues"]) == 0


class TestErrorHandling:
    """Scenario 4 & 5: Error handling for invalid inputs."""

    def test_invalid_file_path(self):
        """Test error response for non-existent file."""
        server = WorkshopMCPServer()

        request = {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "call_tool",
            "params": {
                "name": "performance_check",
                "arguments": {"file_path": "/nonexistent/path/to/file.py"},
            },
        }

        response = server._handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 7
        assert "error" in response
        assert response["error"]["code"] == -32602

    def test_syntax_error_in_file(self):
        """Test error response for file with syntax errors."""
        server = WorkshopMCPServer()
        fixture_path = FIXTURES_DIR / "sample_syntax_error.py"

        request = {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "call_tool",
            "params": {
                "name": "performance_check",
                "arguments": {"file_path": str(fixture_path)},
            },
        }

        response = server._handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 8
        assert "error" in response
        assert response["error"]["code"] == -32602

    def test_syntax_error_in_source_code(self):
        """Test error response for source code with syntax errors."""
        server = WorkshopMCPServer()

        source_code = '''
def broken_function(
    # Missing closing paren
'''

        request = {
            "jsonrpc": "2.0",
            "id": 9,
            "method": "call_tool",
            "params": {
                "name": "performance_check",
                "arguments": {"source_code": source_code},
            },
        }

        response = server._handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 9
        assert "error" in response
        assert response["error"]["code"] == -32602

    def test_missing_required_params(self):
        """Test error when neither file_path nor source_code provided."""
        server = WorkshopMCPServer()

        request = {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "call_tool",
            "params": {
                "name": "performance_check",
                "arguments": {},
            },
        }

        response = server._handle_request(request)

        assert "error" in response
        assert response["error"]["code"] == -32602
        assert "file_path or source_code" in response["error"]["message"]

    def test_both_params_provided_error(self):
        """Test error when both file_path and source_code are provided."""
        server = WorkshopMCPServer()

        request = {
            "jsonrpc": "2.0",
            "id": 11,
            "method": "call_tool",
            "params": {
                "name": "performance_check",
                "arguments": {
                    "file_path": "/some/path.py",
                    "source_code": "def test(): pass",
                },
            },
        }

        response = server._handle_request(request)

        assert "error" in response
        assert response["error"]["code"] == -32602


class TestMixedCodeAnalysis:
    """Test analysis of code with a mix of good and bad patterns."""

    def test_analyze_mixed_file(self):
        """Test analysis correctly identifies the bad patterns."""
        server = WorkshopMCPServer()
        fixture_path = FIXTURES_DIR / "sample_mixed.py"

        request = {
            "jsonrpc": "2.0",
            "id": 12,
            "method": "call_tool",
            "params": {
                "name": "performance_check",
                "arguments": {"file_path": str(fixture_path)},
            },
        }

        response = server._handle_request(request)

        assert "result" in response
        result = json.loads(response["result"]["content"][0]["text"])

        # Should find at least the blocking I/O issue
        assert result["summary"]["total_issues"] >= 1
        assert result["summary"]["total_issues"] <= 5  # Not too many false positives

        # Verify the blocking I/O issue is detected (time.sleep in async)
        categories = [issue["category"] for issue in result["issues"]]
        assert "blocking_io_in_async" in categories


class TestMCPProtocolCompliance:
    """Test MCP protocol compliance in E2E scenarios."""

    def test_list_tools_returns_performance_check(self):
        """Verify list_tools includes performance_check tool."""
        server = WorkshopMCPServer()

        request = {
            "jsonrpc": "2.0",
            "id": 13,
            "method": "list_tools",
        }

        response = server._handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        assert "tools" in response["result"]

        tools = response["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        assert "performance_check" in tool_names

        # Verify tool has proper schema
        perf_tool = next(t for t in tools if t["name"] == "performance_check")
        assert "description" in perf_tool
        assert "inputSchema" in perf_tool
        assert "properties" in perf_tool["inputSchema"]
        assert "file_path" in perf_tool["inputSchema"]["properties"]
        assert "source_code" in perf_tool["inputSchema"]["properties"]

    def test_framed_request_response(self):
        """Test complete framed request/response cycle."""
        server = WorkshopMCPServer()
        fixture_path = FIXTURES_DIR / "sample_bad_performance.py"

        request = {
            "jsonrpc": "2.0",
            "id": 14,
            "method": "call_tool",
            "params": {
                "name": "performance_check",
                "arguments": {"file_path": str(fixture_path)},
            },
        }

        # Create framed request
        request_json = json.dumps(request)
        request_bytes = request_json.encode("utf-8")
        framed_request = f"Content-Length: {len(request_bytes)}\r\n\r\n".encode("utf-8") + request_bytes

        stdin = BytesIO(framed_request)
        stdout = BytesIO()

        # Process the request
        result = server.serve_once(stdin, stdout)

        assert result is True

        # Parse framed response
        stdout.seek(0)
        response_data = stdout.read()

        header_end = response_data.find(b"\r\n\r\n")
        assert header_end > 0

        response_json = response_data[header_end + 4:].decode("utf-8")
        response = json.loads(response_json)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 14
        assert "result" in response


class TestSeverityPrioritization:
    """Test that issues are correctly categorized by severity."""

    def test_severity_levels_correct(self):
        """Verify severity levels match expected patterns."""
        server = WorkshopMCPServer()
        fixture_path = FIXTURES_DIR / "sample_bad_performance.py"

        request = {
            "jsonrpc": "2.0",
            "id": 15,
            "method": "call_tool",
            "params": {
                "name": "performance_check",
                "arguments": {"file_path": str(fixture_path)},
            },
        }

        response = server._handle_request(request)
        result = json.loads(response["result"]["content"][0]["text"])

        # Group issues by severity
        issues_by_severity = {}
        for issue in result["issues"]:
            severity = issue["severity"]
            if severity not in issues_by_severity:
                issues_by_severity[severity] = []
            issues_by_severity[severity].append(issue)

        # Blocking I/O in async should be critical
        if "critical" in issues_by_severity:
            critical_categories = [i["category"] for i in issues_by_severity["critical"]]
            assert "blocking_io_in_async" in critical_categories

        # N+1 queries should be high
        if "high" in issues_by_severity:
            high_categories = [i["category"] for i in issues_by_severity["high"]]
            assert "n_plus_one_query" in high_categories

        # Verify summary matches actual issue counts
        for severity in ["critical", "high", "medium", "low"]:
            expected_count = len(issues_by_severity.get(severity, []))
            actual_count = result["summary"]["by_severity"][severity]
            assert actual_count == expected_count, (
                f"Severity '{severity}' count mismatch: "
                f"expected {expected_count}, got {actual_count}"
            )
