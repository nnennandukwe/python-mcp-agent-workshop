# MCP Integration Guide

This guide explains how the Model Context Protocol (MCP) is implemented in this project and how to add new tools.

## Table of Contents

- [MCP Protocol Overview](#mcp-protocol-overview)
- [Server Architecture](#server-architecture)
- [Message Format](#message-format)
- [Adding New Tools](#adding-new-tools)
- [Agent Configuration](#agent-configuration)
- [Testing MCP Tools](#testing-mcp-tools)

## MCP Protocol Overview

The Model Context Protocol (MCP) enables AI agents to interact with external tools and services. This project implements MCP from scratch without using the official SDK.

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Transport** | stdio (stdin/stdout) with Content-Length framing |
| **Protocol** | JSON-RPC 2.0 |
| **Tools** | Functions exposed to AI agents |
| **Capabilities** | What the server can do (tools, resources, etc.) |

### Communication Flow

```
AI Agent                    MCP Server
    │                           │
    │──── initialize ──────────▶│
    │◀─── capabilities ─────────│
    │                           │
    │──── list_tools ──────────▶│
    │◀─── tool definitions ─────│
    │                           │
    │──── call_tool ───────────▶│
    │◀─── tool result ──────────│
```

## Server Architecture

### WorkshopMCPServer Class

```
src/workshop_mcp/server.py
```

The server handles:
1. **Message Framing**: Reading Content-Length headers, parsing JSON bodies
2. **Request Routing**: Dispatching to appropriate handlers based on method
3. **Tool Execution**: Running tools and returning results
4. **Error Handling**: JSON-RPC error responses

### Class Structure

```python
class WorkshopMCPServer:
    def __init__(self):
        # Initialize tools
        self.keyword_search_tool = KeywordSearchTool()
        self.loop = asyncio.new_event_loop()

    def serve(self):
        # Main loop: read requests, handle, write responses

    def _read_message(self, stdin) -> Dict:
        # Parse Content-Length framed message

    def _write_message(self, stdout, message: Dict):
        # Write Content-Length framed response

    def _handle_request(self, request: Dict) -> Dict:
        # Route to handler based on method

    def _handle_initialize(self, request_id, params) -> Dict:
        # Return server capabilities

    def _handle_list_tools(self, request_id) -> Dict:
        # Return tool definitions

    def _handle_call_tool(self, request_id, params) -> Dict:
        # Execute requested tool
```

### Supported Methods

| Method | Purpose |
|--------|---------|
| `initialize` | Capability handshake |
| `list_tools` | Discover available tools |
| `call_tool` | Execute a tool |

## Message Format

### Content-Length Framing

All messages use HTTP-style Content-Length framing:

```
Content-Length: 42\r\n
\r\n
{"jsonrpc":"2.0","id":1,"method":"..."}
```

### JSON-RPC 2.0 Request

```json
{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "call_tool",
    "params": {
        "name": "performance_check",
        "arguments": {
            "file_path": "src/mycode.py"
        }
    }
}
```

### JSON-RPC 2.0 Response (Success)

```json
{
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "content": [
            {
                "type": "json",
                "json": {
                    "success": true,
                    "summary": {...},
                    "issues": [...]
                }
            }
        ]
    }
}
```

### JSON-RPC 2.0 Response (Error)

```json
{
    "jsonrpc": "2.0",
    "id": 1,
    "error": {
        "code": -32602,
        "message": "File not found: /path/to/file.py"
    }
}
```

### Error Codes

| Code | Meaning |
|------|---------|
| -32700 | Parse error (invalid JSON) |
| -32600 | Invalid Request (missing required fields) |
| -32601 | Method not found |
| -32602 | Invalid params (validation error) |
| -32603 | Internal error |

## Adding New Tools

### Step 1: Implement the Tool

Create a new module or class for your tool:

```python
# src/workshop_mcp/my_tool.py
from typing import Dict, Any

class MyTool:
    """My awesome tool."""

    async def execute(self, param1: str, param2: int) -> Dict[str, Any]:
        """Execute the tool."""
        # Your implementation
        return {
            "success": True,
            "result": "..."
        }
```

### Step 2: Register in list_tools

Add tool definition to `_handle_list_tools`:

```python
def _handle_list_tools(self, request_id: Any) -> Dict[str, Any]:
    result = {
        "tools": [
            # ... existing tools ...
            {
                "name": "my_tool",
                "description": "Description of what my tool does",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "param1": {
                            "type": "string",
                            "description": "First parameter"
                        },
                        "param2": {
                            "type": "integer",
                            "description": "Second parameter",
                            "minimum": 0
                        }
                    },
                    "required": ["param1"]
                }
            }
        ]
    }
    return self._success_response(request_id, result)
```

### Step 3: Add Execution Handler

Add handler in `_handle_call_tool`:

```python
def _handle_call_tool(self, request_id, params):
    name = params.get("name")
    arguments = params.get("arguments", {})

    if name == "keyword_search":
        return self._execute_keyword_search(request_id, arguments)
    elif name == "performance_check":
        return self._execute_performance_check(request_id, arguments)
    elif name == "my_tool":
        return self._execute_my_tool(request_id, arguments)
    else:
        return self._error_response(
            request_id,
            JsonRpcError(-32602, "Unknown tool", {"tool": name})
        )
```

### Step 4: Implement Execution Method

```python
def _execute_my_tool(
    self, request_id: Any, arguments: Dict[str, Any]
) -> Dict[str, Any]:
    # Validate arguments
    if not isinstance(arguments, dict):
        return self._error_response(
            request_id,
            JsonRpcError(-32602, "Invalid params", {"expected": "object"})
        )

    param1 = arguments.get("param1")
    param2 = arguments.get("param2", 0)  # Default value

    if not param1:
        return self._error_response(
            request_id,
            JsonRpcError(-32602, "Missing required argument: param1")
        )

    try:
        # Execute tool
        result = self.loop.run_until_complete(
            self.my_tool.execute(param1, param2)
        )

        # Return MCP-formatted response
        return self._success_response(request_id, {
            "content": [
                {"type": "json", "json": result}
            ]
        })

    except ValueError as exc:
        return self._error_response(
            request_id,
            JsonRpcError(-32602, str(exc))
        )
    except Exception:
        logger.exception("Error executing my_tool")
        return self._error_response(
            request_id,
            JsonRpcError(
                -32603,
                "Internal error",
                {"details": "An unexpected error occurred. Check server logs for details."}
            )
        )
```

### Step 5: Write Tests

```python
# tests/test_mcp_server_integration.py

def test_my_tool_success(mcp_server):
    """Test my_tool executes successfully."""
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "call_tool",
        "params": {
            "name": "my_tool",
            "arguments": {"param1": "test", "param2": 42}
        }
    }
    response = mcp_server._handle_request(request)

    assert "error" not in response
    assert response["result"]["content"][0]["json"]["success"] is True


def test_my_tool_missing_param(mcp_server):
    """Test my_tool returns error for missing param."""
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "call_tool",
        "params": {
            "name": "my_tool",
            "arguments": {}  # Missing param1
        }
    }
    response = mcp_server._handle_request(request)

    assert "error" in response
    assert response["error"]["code"] == -32602
```

## Agent Configuration

### TOML Structure

Agents are configured in TOML files under `agents/`:

```toml
version = "1.0.0"
model = "gemini-2.5-pro"

[commands.my_command]
description = "What this agent does"
instructions = """
Your agent instructions here.

## Core Responsibilities:
1. ...

## Output Structure:
...
"""

execution_strategy = "act"  # or "plan"

arguments = [
    {name = "param1", type = "string", required = true, description = "..."},
    {name = "param2", type = "integer", required = false, description = "..."}
]

output_schema = """
{
    "properties": {
        "success": {"type": "boolean"},
        "result": {"type": "string"}
    }
}
"""

exit_expression = "success"
```

### Key Fields

| Field | Description |
|-------|-------------|
| `version` | Agent configuration version |
| `model` | LLM model to use |
| `description` | Brief description shown in agent list |
| `instructions` | Detailed prompt for the agent |
| `execution_strategy` | `act` (direct execution) or `plan` (planning first) |
| `arguments` | Input parameters for the agent |
| `output_schema` | JSON Schema for structured output |
| `exit_expression` | Field to check for completion |

### Writing Good Instructions

1. **Be Specific**: Describe exactly what the agent should do
2. **Provide Structure**: Define output format clearly
3. **Include Examples**: Show expected input/output
4. **Handle Errors**: Explain what to do on failures
5. **Prioritize**: Tell agent what's most important

Example structure:
```markdown
## Core Responsibilities:
1. Primary task
2. Secondary task

## Analysis Framework:
- How to approach the problem
- What to look for

## Output Structure:
1. Section 1: ...
2. Section 2: ...

## Error Handling:
- If X happens, do Y
```

## Testing MCP Tools

### Manual Testing

```bash
# Start server
poetry run python -m workshop_mcp.server

# In another terminal, send request
echo 'Content-Length: 123

{"jsonrpc":"2.0","id":1,"method":"list_tools","params":{}}' | poetry run python -m workshop_mcp.server
```

### Using Python

```python
import json
import subprocess

def send_mcp_request(request):
    """Send a request to MCP server and get response."""
    body = json.dumps(request)
    message = f"Content-Length: {len(body)}\r\n\r\n{body}"

    proc = subprocess.Popen(
        ["poetry", "run", "python", "-m", "workshop_mcp.server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    stdout, stderr = proc.communicate(input=message.encode())

    # Parse response (skip Content-Length header)
    response_body = stdout.split(b"\r\n\r\n", 1)[1]
    return json.loads(response_body)

# Test list_tools
response = send_mcp_request({
    "jsonrpc": "2.0",
    "id": 1,
    "method": "list_tools",
    "params": {}
})
print(json.dumps(response, indent=2))
```

### Unit Tests

```python
# tests/test_mcp_server_integration.py

import pytest
from workshop_mcp.server import WorkshopMCPServer

@pytest.fixture
def mcp_server():
    """Create MCP server instance for testing."""
    return WorkshopMCPServer()

def test_list_tools_includes_performance_check(mcp_server):
    """Verify performance_check tool is listed."""
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "list_tools",
        "params": {}
    }
    response = mcp_server._handle_request(request)

    tools = response["result"]["tools"]
    tool_names = [t["name"] for t in tools]

    assert "performance_check" in tool_names
```

### Integration Tests

See `tests/test_e2e_workflow.py` for complete workflow tests that:
1. Initialize the server
2. List available tools
3. Call tools with various inputs
4. Validate response structure
