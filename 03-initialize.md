# 03 - Initialize: Capability Handshake

Before tools can be called, MCP clients perform an **initialize** handshake to
negotiate protocol versions and capabilities. This chapter shows how to
implement that handshake from scratch.

## Protocol Component: `initialize`

The client sends an `initialize` request, typically including a
`protocolVersion` and client metadata. The server responds with its protocol
version, identity, and supported capabilities.

Example request:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "clientInfo": {"name": "demo-client", "version": "0.1.0"}
  }
}
```

Example response:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "serverInfo": {"name": "workshop-mcp-server", "version": "0.1.0"},
    "capabilities": {"tools": {}}
  }
}
```

## Minimal Implementation

```python
def handle_initialize(request_id: int, params: dict | None) -> dict:
    params = params or {}
    protocol_version = params.get("protocolVersion", "2024-11-05")
    result = {
        "protocolVersion": protocol_version,
        "serverInfo": {"name": "workshop-mcp-server", "version": "0.1.0"},
        "capabilities": {"tools": {}},
    }
    return success_response(request_id, result)
```

## Reference Implementation

The full handshake logic lives in:
- `WorkshopMCPServer._handle_initialize` in `src/workshop_mcp/server.py`

Next: [04 - Tools: list_tools & call_tool](04-tools.md)
