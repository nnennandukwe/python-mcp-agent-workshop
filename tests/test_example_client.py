"""Integration tests for the example MCP client script.

Runs examples/mcp_client_example.py end-to-end and verifies that the
client can communicate with the server over stdio using Content-Length
framed JSON-RPC 2.0.
"""

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLIENT_SCRIPT = PROJECT_ROOT / "examples" / "mcp_client_example.py"

# The client spawns 5 server subprocesses sequentially, each with a 30s
# internal timeout (worst-case aggregate: 150s).  We use 60s as a pragmatic
# compromise: long enough for healthy runs but short enough to catch hangs
# quickly.  If this proves flaky on slow CI, increase toward 150s.
TIMEOUT_SECONDS = 60


def _run_client() -> subprocess.CompletedProcess[str]:
    """Run the example client and return the completed process."""
    return subprocess.run(
        [sys.executable, str(CLIENT_SCRIPT)],
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
        cwd=str(PROJECT_ROOT),
    )


@pytest.fixture(scope="class")
def client_result() -> subprocess.CompletedProcess[str]:
    """Run the example client once and share the result across the test class."""
    return _run_client()


class TestExampleClient:
    """End-to-end tests for examples/mcp_client_example.py."""

    def test_client_example_runs_successfully(
        self, client_result: subprocess.CompletedProcess[str]
    ) -> None:
        """The example client exits cleanly and prints the completion message."""
        assert client_result.returncode == 0, (
            f"Client exited with code {client_result.returncode}\n"
            f"--- stdout ---\n{client_result.stdout}\n"
            f"--- stderr ---\n{client_result.stderr}"
        )
        assert "All examples completed!" in client_result.stdout
        assert "Traceback" not in client_result.stderr, (
            f"Server logged unexpected traceback\n--- stderr ---\n{client_result.stderr}"
        )

    def test_client_output_contains_all_example_sections(
        self, client_result: subprocess.CompletedProcess[str]
    ) -> None:
        """All five example sections appear in the client output."""
        if client_result.returncode != 0:
            pytest.skip(
                f"Client script failed (exit {client_result.returncode}); skipping output verification"
            )

        # These section headers must match the print() calls in
        # examples/mcp_client_example.py exactly.
        expected_sections = [
            "Example 1: Initialize",
            "Example 2: List Tools",
            "Example 3: Call performance_check Tool",
            "Example 4: Call keyword_search Tool",
            "Example 5: Error Handling",
        ]

        for section in expected_sections:
            assert section in client_result.stdout, (
                f"Missing section: {section!r}\n--- stdout ---\n{client_result.stdout}"
            )

    def test_tool_outputs_contain_meaningful_results(
        self, client_result: subprocess.CompletedProcess[str]
    ) -> None:
        """Tools return substantive output, not empty or error responses."""
        if client_result.returncode != 0:
            pytest.skip(
                f"Client script failed (exit {client_result.returncode}); skipping output verification"
            )

        stdout = client_result.stdout

        # Example 3: performance_check detects blocking I/O in async code
        assert "Total Issues:" in stdout, (
            f"Example 3 missing 'Total Issues:' — profiler may have returned empty results\n"
            f"--- stdout ---\n{stdout}"
        )
        assert "[CRITICAL]" in stdout, (
            f"Example 3 missing '[CRITICAL]' — expected blocking I/O severity\n"
            f"--- stdout ---\n{stdout}"
        )

        # Example 4: keyword_search finds occurrences of "async"
        assert "Total occurrences:" in stdout, (
            f"Example 4 missing 'Total occurrences:' — search may have returned no results\n"
            f"--- stdout ---\n{stdout}"
        )

        # Example 5: error handling surfaces structured error response
        assert "Error Code:" in stdout, (
            f"Example 5 missing 'Error Code:' — server may not have returned a JSON-RPC error\n"
            f"--- stdout ---\n{stdout}"
        )
