---
title: "feat: Add subprocess-level transport layer tests"
type: feat
date: 2026-02-10
---

# Add Subprocess-Level Transport Layer Tests

## Overview

Close the transport layer testing gap by adding subprocess-level tests that exercise real `sys.stdin`/`sys.stdout` binary stream behavior. Currently, in-process integration tests mock stdio with `BytesIO`, which never exercises actual pipe buffering, encoding, EOF handling, or the multi-message `serve()` loop. Only `test_example_client.py` (3 tests) exercises the real subprocess stdio path, and it spawns a new process per request — never testing multi-message sessions.

## Problem Statement

The in-process tests provide false confidence about transport reliability:

| What BytesIO hides | Real pipe behavior |
|--------------------|--------------------|
| `read(n)` always returns exactly n bytes | May return fewer bytes (short reads) on pipes > 64KB |
| `flush()` is a no-op | Required to push data through the pipe |
| EOF is immediate when BytesIO is exhausted | EOF requires explicit pipe close; partial reads are possible |
| No buffering or blocking | Writes can block when pipe buffer fills (~64KB on macOS) |
| No encoding issues | `decode("utf-8")` can raise `UnicodeDecodeError` on real data |

Additionally, these code paths are **completely untested**:
- `serve()` multi-message loop (`server.py:71`) — only `serve_once()` is tested
- `sync_main()` entry point (`server.py:588-606`) — handles `KeyboardInterrupt` and fatal exceptions
- Error recovery within a session — server should continue after a bad request
- Notification handling in multi-message sessions — no response should be written

## Proposed Solution

Create a new test file `tests/test_subprocess_transport.py` with a reusable `MCPSubprocessClient` helper class and targeted subprocess tests organized by scenario.

## Technical Approach

### Phase 1: Test Infrastructure — `MCPSubprocessClient` helper

Build a reusable subprocess client that wraps `subprocess.Popen` for incremental pipe I/O:

```python
# tests/test_subprocess_transport.py

class MCPSubprocessClient:
    """Subprocess-level MCP client for transport layer testing."""

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self.proc: subprocess.Popen | None = None

    def start(self) -> None:
        """Spawn server subprocess with stdin/stdout pipes."""
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "workshop_mcp.server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(PROJECT_ROOT),
        )

    def send(self, request: dict) -> None:
        """Frame and write a JSON-RPC message to server stdin."""
        body = json.dumps(request).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode()
        self.proc.stdin.write(header + body)
        self.proc.stdin.flush()

    def receive(self) -> dict:
        """Read and parse one Content-Length-framed response from stdout."""
        # Read headers until blank line
        # Parse Content-Length
        # Read exactly content_length bytes (with short-read loop)
        # Parse JSON
        ...

    def send_raw(self, data: bytes) -> None:
        """Write raw bytes to stdin for malformed-input tests."""
        self.proc.stdin.write(data)
        self.proc.stdin.flush()

    def close(self) -> int:
        """Close stdin, wait for exit, return exit code."""
        self.proc.stdin.close()
        self.proc.wait(timeout=self.timeout)
        return self.proc.returncode

    @property
    def stderr_output(self) -> str:
        """Captured stderr for diagnostic assertions."""
        return self.proc.stderr.read().decode("utf-8", errors="replace")
```

**Key design decisions:**
- Uses `sys.executable, "-m", "workshop_mcp.server"` for invocation (matches existing `mcp_client_example.py` pattern)
- Per-operation timeout via `select`/`poll` on the pipe to prevent infinite hangs
- `send_raw()` method for malformed-input tests (bad framing, bad encoding)
- Tracks whether a request has an `"id"` field to know if a response is expected (notifications have no id)

**Files:**
- `tests/test_subprocess_transport.py` — new file, all tests and the helper class

### Phase 2: Multi-Message Session Tests (Highest Value)

These tests exercise the `serve()` loop (`server.py:71`) which is currently untested at the subprocess level.

```
Test: test_multi_message_session_lifecycle
  → send initialize request, receive response
  → send initialized notification (no response expected)
  → send tools/list request, receive response with tool names
  → send tools/call with performance_check (source_code param), receive result
  → close stdin → server exits with code 0

Test: test_sequential_tool_calls_in_single_session
  → initialize
  → call performance_check with N+1 query code
  → call keyword_search with test pattern
  → verify both responses are correct and ordered
  → close → exit code 0

Test: test_server_continues_after_notification
  → initialize → initialized notification → tools/list
  → verify tools/list response arrives correctly (notification didn't desync)
```

**What these catch:**
- Event loop reuse between `_serve_once` calls
- stdin buffer position alignment between messages
- stdout flush timing between responses
- Notification handling not corrupting the response stream

### Phase 3: Error Recovery Tests

Verify the server returns an error but **continues serving** after a bad request mid-session.

```
Test: test_error_recovery_bad_json_mid_session
  → initialize (valid, get response)
  → send raw malformed JSON (get error response -32700)
  → send tools/list (valid, get response with tools)
  → verifies serve() loop continues after JsonRpcError

Test: test_error_recovery_unknown_method
  → initialize
  → send {"method": "nonexistent/method", "id": 2}
  → expect error response (-32601 Method not found)
  → send tools/list → get valid response
```

**What these catch:**
- `_serve_once` returning `True` after errors (continues the loop)
- Error response framing not corrupting subsequent messages
- Server state remaining valid after error handling

### Phase 4: Entry Point and Lifecycle Tests

Test `sync_main()` (`server.py:588-606`) which is the `pyproject.toml` console script entry point.

```
Test: test_clean_shutdown_on_eof
  → start server, send initialize, receive response
  → close stdin
  → assert exit code 0
  → assert "Server stopped" in stderr

Test: test_sigint_produces_clean_exit
  → start server, send initialize, receive response
  → os.kill(proc.pid, signal.SIGINT)
  → assert exit code 0
  → assert no traceback in stderr

Test: test_entry_point_via_sync_main
  → spawn via: sys.executable, "-c",
    "from workshop_mcp.server import sync_main; sync_main()"
  → send initialize, receive response, close → exit code 0
  → verifies the console script code path works

Test: test_stderr_lifecycle_logging
  → full session: initialize → tools/list → close
  → assert "Starting Workshop MCP Server" in stderr
  → assert "Server stopped" in stderr
  → assert "Traceback" NOT in stderr
```

**What these catch:**
- `sync_main()` exception handling (currently untested)
- `KeyboardInterrupt` → exit code 0 path
- Event loop cleanup in `serve()` finally block (`server.py:75`)
- Console script entry point configuration

### Phase 5: Edge Cases — Framing, Encoding, Large Payloads

```
Test: test_large_payload_exceeding_pipe_buffer
  → initialize
  → call performance_check with source_code > 80KB
    (larger than typical 64KB pipe buffer)
  → if response received: verify correct analysis
  → if short-read bug triggers: document as known issue

Test: test_multibyte_utf8_in_source_code
  → call performance_check with source code containing
    CJK characters, emoji, accented chars in variable names
  → verify response parses correctly

Test: test_content_length_zero
  → send "Content-Length: 0\r\n\r\n"
  → expect -32700 Parse error (empty body isn't valid JSON)
  → verify server continues (send valid request after)

Test: test_extraneous_stdout_detection
  → full session → capture raw stdout bytes
  → verify ONLY well-formed Content-Length frames exist
  → catches accidental print() or debug output to stdout
```

**What these catch:**
- `stdin.read(content_length)` short-read bug on real pipes (`server.py:142`)
- UTF-8 decode behavior differences between BytesIO and real pipes
- Framing edge cases that BytesIO can't expose
- stdout pollution that would corrupt the protocol

### Phase 6: Bug Fixes Discovered During Testing (Conditional)

If tests reveal bugs (likely for large payloads), fix them in scope:

**Likely fix 1:** `stdin.read(content_length)` short-read loop
```python
# server.py:142 — current (single read, may short-read on pipe):
body = stdin.read(content_length)

# Fix: read loop that handles short reads
body = b""
while len(body) < content_length:
    chunk = stdin.read(content_length - len(body))
    if not chunk:  # EOF mid-message
        return None
    body += chunk
```

**Likely fix 2:** Negative Content-Length validation
```python
# After int() parse at server.py:138
if content_length < 0:
    raise JsonRpcError(-32600, "Invalid Content-Length header")
```

**Likely fix 3:** `UnicodeDecodeError` on body decode
```python
# server.py:147 — wrap decode in try/except
try:
    text = body.decode("utf-8")
except UnicodeDecodeError:
    raise JsonRpcError(-32700, "Invalid UTF-8 encoding in request body")
```

## Acceptance Criteria

### Functional Requirements

- [x] `MCPSubprocessClient` helper class handles incremental pipe I/O with timeouts
- [x] Multi-message session test passes: initialize → notification → tool calls → EOF
- [x] Error recovery test passes: valid → malformed → valid within one session
- [x] `sync_main()` exit codes verified: 0 on clean EOF, 0 on SIGINT
- [x] Entry point test verifies `sync_main()` import path works
- [x] Large payload (>64KB) test exercises real pipe buffering behavior

### Non-Functional Requirements

- [x] All new tests run in < 30 seconds total (individual test timeout: 10s)
- [x] Tests are not flaky — use explicit synchronization (wait for response before next send), not sleep-based timing
- [x] `@pytest.mark.subprocess` marker on all tests for selective execution
- [x] Tests work on macOS and Linux (pipe buffer sizes may differ)

### Quality Gates

- [x] `poetry run pytest tests/test_subprocess_transport.py -v` passes
- [x] Full suite `poetry run pytest` still passes (no interference)
- [x] `poetry run ruff check tests/test_subprocess_transport.py` passes
- [ ] `poetry run mypy tests/test_subprocess_transport.py` passes (if mypy is configured for tests)

## Dependencies & Risks

**Dependencies:**
- No new packages required — uses `subprocess`, `json`, `sys`, `signal`, `os` from stdlib
- Requires `poetry install` for the `workshop_mcp` package to be importable by subprocess

**Risks:**
| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Large payload test reveals `stdin.read()` short-read bug | High | Fix in Phase 6; test documents the issue even if fix is deferred |
| SIGINT test timing sensitivity (signal arrives during startup vs. steady state) | Medium | Wait for initialize response before sending SIGINT; use retry with exponential backoff only as last resort |
| Pipe deadlock on large payloads (stdout buffer fills while writing stdin) | Low | Use threads or `select` for concurrent read/write if needed |
| Platform-specific pipe buffer sizes | Low | Test uses >80KB payload (exceeds both macOS 64KB and Linux 64KB defaults) |

## References & Research

### Internal References

- Server `serve()` loop: `src/workshop_mcp/server.py:71-76`
- Server `_read_message()`: `src/workshop_mcp/server.py:108-155`
- Server `_serve_once()`: `src/workshop_mcp/server.py:78-105`
- Server `sync_main()`: `src/workshop_mcp/server.py:588-606`
- Existing subprocess test: `tests/test_example_client.py:24-32`
- BytesIO harness (pattern to exceed): `tests/test_mcp_server_protocol.py:18-50`
- Example client subprocess spawning: `examples/mcp_client_example.py:69-83`
- Pytest config: `pyproject.toml:32-34`

### Existing Pattern to Build On

The `test_example_client.py` pattern of class-scoped fixtures and subprocess.run is the starting point, but `MCPSubprocessClient` with Popen replaces `subprocess.run` to enable incremental I/O within a single server process lifetime.
