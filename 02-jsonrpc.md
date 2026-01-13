# 02 - JSON-RPC 2.0: Validating and Routing Requests

MCP servers use **JSON-RPC 2.0** to structure requests and responses. This
chapter focuses on validating requests, handling errors, and routing calls to
handlers.

## Protocol Component: JSON-RPC 2.0 Envelope

A JSON-RPC request must include:
- `jsonrpc`: must be "2.0"
- `method`: the RPC name (string)
- `id`: optional for notifications; otherwise string/number/null

Example request:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "list_tools"
}
```

Example success response:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {"tools": []}
}
```

Example error response:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {"code": -32601, "message": "Method not found"}
}
```

## Minimal Implementation

This minimal dispatcher validates JSON-RPC basics and routes known methods. The
full implementation lives in `src/workshop_mcp/server.py`.

```python
def handle_request(request: dict) -> dict | None:
    if request.get("jsonrpc") != "2.0":
        return error_response(request.get("id"), -32600, "Invalid Request")

    if "id" not in request:  # notification
        return None

    method = request.get("method")
    if method == "initialize":
        return handle_initialize(request["id"], request.get("params"))
    if method == "list_tools":
        return handle_list_tools(request["id"])

    return error_response(request["id"], -32601, "Method not found")
```

## Reference Implementation

For strict validation and robust error handling, review:
- `WorkshopMCPServer._handle_request` in `src/workshop_mcp/server.py`
- `JsonRpcError` and `_error_response` helpers in `src/workshop_mcp/server.py`

Next: [03 - Initialize Handshake](03-initialize.md)
