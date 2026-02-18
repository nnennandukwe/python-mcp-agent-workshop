"""Subprocess-level transport tests for the MCP server.

These tests spawn real server subprocesses over stdio pipes, exercising
the actual sys.stdin/sys.stdout binary stream behavior that in-process
BytesIO-based tests cannot reach: pipe buffering, encoding, EOF handling,
the multi-message serve() loop, and the sync_main() entry point.
"""

import json
import os
import queue
import signal
import subprocess
import sys
import threading
from collections.abc import Generator
from pathlib import Path
from typing import Any, cast

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Marker for selective execution: poetry run pytest -m subprocess
pytestmark = pytest.mark.subprocess


class MCPSubprocessClient:
    """Subprocess-level MCP client for transport layer testing.

    Wraps subprocess.Popen to provide incremental pipe I/O with
    Content-Length framed JSON-RPC 2.0 messages.

    Uses a background reader thread with os.read() on the raw fd to
    avoid the classic select() + BufferedReader mismatch where
    BufferedReader greedily consumes pipe data into its internal buffer,
    making select() report the fd as empty.
    """

    def __init__(
        self,
        timeout: float = 10.0,
        invocation: list[str] | None = None,
    ) -> None:
        self.timeout = timeout
        self.invocation = invocation or [sys.executable, "-m", "workshop_mcp.server"]
        self.proc: subprocess.Popen[bytes] | None = None
        self._stdout_chunks: queue.Queue[bytes | None] = queue.Queue()
        self._stderr_chunks: list[bytes] = []
        self._reader_thread: threading.Thread | None = None
        self._stderr_reader_thread: threading.Thread | None = None
        self._buffer = b""

    def start(self) -> None:
        """Spawn server subprocess with stdin/stdout/stderr pipes."""
        self.proc = subprocess.Popen(
            self.invocation,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(PROJECT_ROOT),
        )
        # Start background threads reading raw stdout and stderr fds
        self._reader_thread = threading.Thread(target=self._stdout_reader, daemon=True)
        self._reader_thread.start()
        self._stderr_reader_thread = threading.Thread(target=self._stderr_reader, daemon=True)
        self._stderr_reader_thread.start()

    def _stdout_reader(self) -> None:
        """Background thread: read raw bytes from stdout fd into queue."""
        assert self.proc is not None and self.proc.stdout is not None
        fd = self.proc.stdout.fileno()
        while True:
            try:
                data = os.read(fd, 65536)
                if not data:
                    self._stdout_chunks.put(None)  # EOF sentinel
                    break
                self._stdout_chunks.put(data)
            except OSError:
                self._stdout_chunks.put(None)
                break

    def _stderr_reader(self) -> None:
        """Background thread: drain stderr to prevent pipe deadlock."""
        assert self.proc is not None and self.proc.stderr is not None
        fd = self.proc.stderr.fileno()
        while True:
            try:
                data = os.read(fd, 65536)
                if not data:
                    break
                self._stderr_chunks.append(data)
            except OSError:
                break

    def send(self, request: dict[str, Any]) -> None:
        """Frame and write a JSON-RPC message to server stdin."""
        assert self.proc is not None and self.proc.stdin is not None
        body = json.dumps(request).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode()
        self.proc.stdin.write(header + body)
        self.proc.stdin.flush()

    def send_raw(self, data: bytes) -> None:
        """Write raw bytes to stdin for malformed-input tests."""
        assert self.proc is not None and self.proc.stdin is not None
        self.proc.stdin.write(data)
        self.proc.stdin.flush()

    def receive(self) -> dict[str, Any]:
        """Read and parse one Content-Length-framed response from stdout."""
        # Read headers line by line until blank line
        headers: dict[str, str] = {}
        while True:
            line = self._read_line()
            if line in (b"\r\n", b"\n"):
                break
            decoded = line.decode("utf-8", errors="replace").strip()
            if not decoded:
                break
            if ":" in decoded:
                key, value = decoded.split(":", 1)
                headers[key.strip().lower()] = value.strip()

        content_length_str = headers.get("content-length")
        assert content_length_str is not None, (
            f"No Content-Length header in response. Headers: {headers}"
        )
        content_length = int(content_length_str)

        # Read body
        body = self._read_bytes(content_length)
        return cast(dict[str, Any], json.loads(body.decode("utf-8")))

    def close(self) -> int:
        """Close stdin, wait for exit, join reader threads, return exit code."""
        assert self.proc is not None
        if self.proc.stdin and not self.proc.stdin.closed:
            self.proc.stdin.close()
        self.proc.wait(timeout=self.timeout)
        if self._reader_thread is not None:
            self._reader_thread.join(timeout=self.timeout)
        if self._stderr_reader_thread is not None:
            self._stderr_reader_thread.join(timeout=self.timeout)
        return self.proc.returncode

    @property
    def stderr_output(self) -> str:
        """Return all captured stderr after process exits."""
        assert self._stderr_reader_thread is not None
        self._stderr_reader_thread.join(timeout=self.timeout)
        return b"".join(self._stderr_chunks).decode("utf-8", errors="replace")

    def remaining_stdout(self) -> bytes:
        """Drain any remaining stdout data after process exits."""
        # Drain the queue
        remaining = self._buffer
        while True:
            try:
                chunk = self._stdout_chunks.get_nowait()
                if chunk is None:
                    break
                remaining += chunk
            except queue.Empty:
                break
        self._buffer = b""
        return remaining

    def kill(self) -> None:
        """Force-kill the server process."""
        if self.proc is not None:
            self.proc.kill()
            self.proc.wait(timeout=5)

    def _fill_buffer(self) -> None:
        """Block until at least one chunk arrives or EOF."""
        try:
            chunk = self._stdout_chunks.get(timeout=self.timeout)
        except queue.Empty:
            raise TimeoutError(f"No data from server within {self.timeout}s")
        if chunk is None:
            raise EOFError("Server closed stdout")
        self._buffer += chunk

    def _read_bytes(self, n: int) -> bytes:
        """Read exactly n bytes with timeout."""
        while len(self._buffer) < n:
            self._fill_buffer()
        result = self._buffer[:n]
        self._buffer = self._buffer[n:]
        return result

    def _read_line(self) -> bytes:
        """Read until \\n with timeout."""
        while b"\n" not in self._buffer:
            self._fill_buffer()
        idx = self._buffer.index(b"\n") + 1
        line = self._buffer[:idx]
        self._buffer = self._buffer[idx:]
        return line


@pytest.fixture
def client() -> Generator[MCPSubprocessClient, None, None]:
    """Create and start a client, clean up on teardown."""
    c = MCPSubprocessClient()
    c.start()
    yield c
    if c.proc and c.proc.poll() is None:
        c.kill()


def _make_initialize_request(request_id: int = 1) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "initialize",
        "params": {"protocolVersion": "2024-11-05"},
    }


def _make_initialized_notification() -> dict[str, Any]:
    return {"jsonrpc": "2.0", "method": "notifications/initialized"}


def _make_list_tools_request(request_id: int = 2) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "method": "list_tools"}


def _make_performance_check_request(source_code: str, request_id: int = 3) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "call_tool",
        "params": {
            "name": "performance_check",
            "arguments": {"source_code": source_code},
        },
    }


# ---------------------------------------------------------------------------
# Phase 2: Multi-Message Session Tests
# ---------------------------------------------------------------------------


class TestMultiMessageSession:
    """Test the serve() loop with multi-message sessions over a single connection."""

    def test_multi_message_session_lifecycle(self, client: MCPSubprocessClient) -> None:
        """Full MCP lifecycle: initialize -> notification -> list_tools -> call_tool -> EOF."""
        # 1. Initialize
        client.send(_make_initialize_request(1))
        resp = client.receive()
        assert resp["id"] == 1
        assert resp["result"]["serverInfo"]["name"] == "workshop-mcp-server"

        # 2. Notification (no response expected)
        client.send(_make_initialized_notification())

        # 3. List tools
        client.send(_make_list_tools_request(2))
        resp = client.receive()
        assert resp["id"] == 2
        tool_names = {t["name"] for t in resp["result"]["tools"]}
        assert "keyword_search" in tool_names
        assert "performance_check" in tool_names

        # 4. Call performance_check with source_code
        source = "for user in User.objects.all():\n    print(user.profile.name)\n"
        client.send(_make_performance_check_request(source, request_id=3))
        resp = client.receive()
        assert resp["id"] == 3
        assert "result" in resp
        content = resp["result"]["content"][0]
        assert content["type"] == "json"
        assert content["json"]["success"] is True

        # 5. Close -> server exits cleanly
        exit_code = client.close()
        assert exit_code == 0

    def test_sequential_tool_calls_in_single_session(self, client: MCPSubprocessClient) -> None:
        """Multiple tool calls in a single session return correct, ordered responses."""
        # Initialize first
        client.send(_make_initialize_request(1))
        client.receive()

        # Call 1: performance_check
        source = "async def bad():\n    with open('f') as fh:\n        return fh.read()\n"
        client.send(_make_performance_check_request(source, request_id=10))
        resp1 = client.receive()
        assert resp1["id"] == 10
        assert resp1["result"]["content"][0]["json"]["success"] is True

        # Call 2: performance_check with different code
        source2 = "x = [i for i in range(1000000)]\n"
        client.send(_make_performance_check_request(source2, request_id=11))
        resp2 = client.receive()
        assert resp2["id"] == 11
        assert "result" in resp2

        exit_code = client.close()
        assert exit_code == 0

    def test_server_continues_after_notification(self, client: MCPSubprocessClient) -> None:
        """Notification between requests doesn't desync the response stream."""
        client.send(_make_initialize_request(1))
        resp = client.receive()
        assert resp["id"] == 1

        # Send notification (no response)
        client.send(_make_initialized_notification())

        # Immediately send a request — should get the correct response
        client.send(_make_list_tools_request(2))
        resp = client.receive()
        assert resp["id"] == 2
        assert "tools" in resp["result"]

        client.close()


# ---------------------------------------------------------------------------
# Phase 3: Error Recovery Tests
# ---------------------------------------------------------------------------


class TestErrorRecovery:
    """Verify the server continues serving after errors mid-session."""

    def test_error_recovery_bad_json_mid_session(self, client: MCPSubprocessClient) -> None:
        """Server recovers from malformed JSON and processes the next valid request."""
        # 1. Valid initialize
        client.send(_make_initialize_request(1))
        resp = client.receive()
        assert resp["id"] == 1

        # 2. Send malformed JSON
        bad_json = b'{"jsonrpc": "2.0", "method": "list_tools",}'
        header = f"Content-Length: {len(bad_json)}\r\n\r\n".encode()
        client.send_raw(header + bad_json)
        error_resp = client.receive()
        assert error_resp["error"]["code"] == -32700  # Parse error

        # 3. Valid request should still work
        client.send(_make_list_tools_request(3))
        resp = client.receive()
        assert resp["id"] == 3
        assert "tools" in resp["result"]

        client.close()

    def test_error_recovery_unknown_method(self, client: MCPSubprocessClient) -> None:
        """Server recovers from unknown method and processes the next valid request."""
        client.send(_make_initialize_request(1))
        client.receive()

        # Unknown method
        client.send(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "nonexistent/method",
            }
        )
        error_resp = client.receive()
        assert error_resp["error"]["code"] == -32601  # Method not found

        # Next valid request works
        client.send(_make_list_tools_request(3))
        resp = client.receive()
        assert resp["id"] == 3
        assert "tools" in resp["result"]

        client.close()


# ---------------------------------------------------------------------------
# Phase 4: Entry Point and Lifecycle Tests
# ---------------------------------------------------------------------------


class TestEntryPointLifecycle:
    """Test sync_main() and server lifecycle behavior."""

    def test_clean_shutdown_on_eof(self, client: MCPSubprocessClient) -> None:
        """Server exits with code 0 when stdin is closed (EOF)."""
        client.send(_make_initialize_request(1))
        client.receive()

        exit_code = client.close()
        assert exit_code == 0

    def test_sigint_produces_clean_exit(self, client: MCPSubprocessClient) -> None:
        """Server exits cleanly on SIGINT without traceback."""
        # Establish a connection first so server is in steady state
        client.send(_make_initialize_request(1))
        client.receive()

        # Send SIGINT
        assert client.proc is not None
        os.kill(client.proc.pid, signal.SIGINT)
        client.proc.wait(timeout=10)

        # Should exit cleanly (0 from KeyboardInterrupt handler, or
        # 130 which is the standard SIGINT exit on some systems)
        assert client.proc.returncode in (0, -signal.SIGINT, 130)
        stderr = client.stderr_output
        assert "Traceback" not in stderr

    def test_entry_point_via_sync_main(self) -> None:
        """The sync_main() import path works (console script code path)."""
        c = MCPSubprocessClient(
            invocation=[
                sys.executable,
                "-c",
                "from workshop_mcp.server import sync_main; sync_main()",
            ]
        )
        c.start()
        try:
            c.send(_make_initialize_request(1))
            resp = c.receive()
            assert resp["id"] == 1
            assert resp["result"]["serverInfo"]["name"] == "workshop-mcp-server"
            exit_code = c.close()
            assert exit_code == 0
        finally:
            if c.proc and c.proc.poll() is None:
                c.kill()

    def test_stderr_lifecycle_logging(self, client: MCPSubprocessClient) -> None:
        """Stderr contains expected lifecycle log messages."""
        client.send(_make_initialize_request(1))
        client.receive()
        client.send(_make_list_tools_request(2))
        client.receive()
        client.close()

        stderr = client.stderr_output
        assert "Starting Workshop MCP Server" in stderr
        assert "Server stopped" in stderr
        assert "Traceback" not in stderr


# ---------------------------------------------------------------------------
# Phase 5: Edge Cases — Framing, Encoding, Large Payloads
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Test framing edge cases, encoding, and large payloads."""

    def test_large_payload_exceeding_pipe_buffer(self, client: MCPSubprocessClient) -> None:
        """Source code >80KB exercises real pipe buffering (pipe buffer ~64KB)."""
        client.send(_make_initialize_request(1))
        client.receive()

        # Generate >80KB of valid Python source code
        lines = []
        for i in range(2000):
            lines.append(f"variable_{i} = 'value_{i}' * 10  # padding line {i}")
        large_source = "\n".join(lines) + "\n"
        assert len(large_source.encode("utf-8")) > 80_000

        client.send(_make_performance_check_request(large_source, request_id=2))
        resp = client.receive()
        assert resp["id"] == 2
        assert "result" in resp
        assert resp["result"]["content"][0]["json"]["success"] is True

        client.close()

    def test_multibyte_utf8_in_source_code(self, client: MCPSubprocessClient) -> None:
        """Multi-byte UTF-8 characters in source code are handled correctly."""
        client.send(_make_initialize_request(1))
        client.receive()

        source = (
            "# Kommentar mit Umlauten: \u00e4\u00f6\u00fc\u00df\n"
            '\u5909\u6570 = "CJK variable name"\n'
            'emoji_var = "\U0001f680\U0001f40d"  # rocket and snake\n'
            "print(\u5909\u6570)\n"
        )
        client.send(_make_performance_check_request(source, request_id=2))
        resp = client.receive()
        assert resp["id"] == 2
        assert "result" in resp

        client.close()

    def test_content_length_zero(self, client: MCPSubprocessClient) -> None:
        """Content-Length: 0 produces a parse error but server continues."""
        client.send(_make_initialize_request(1))
        client.receive()

        # Send Content-Length: 0 with empty body
        client.send_raw(b"Content-Length: 0\r\n\r\n")
        error_resp = client.receive()
        assert error_resp["error"]["code"] == -32700  # Parse error

        # Server should continue
        client.send(_make_list_tools_request(2))
        resp = client.receive()
        assert resp["id"] == 2
        assert "tools" in resp["result"]

        client.close()

    def test_extraneous_stdout_detection(self) -> None:
        """Raw stdout contains only well-formed Content-Length frames."""
        c = MCPSubprocessClient()
        c.start()
        try:
            c.send(_make_initialize_request(1))
            resp = c.receive()
            assert resp["id"] == 1

            c.send(_make_list_tools_request(2))
            resp = c.receive()
            assert resp["id"] == 2

            # Close stdin to trigger EOF and wait for process exit
            exit_code = c.close()
            assert exit_code == 0

            # After process exits, drain any leftover stdout data
            remaining = c.remaining_stdout()
            assert remaining == b"", f"Extraneous bytes on stdout after session: {remaining!r}"
        finally:
            if c.proc and c.proc.poll() is None:
                c.kill()
