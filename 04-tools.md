# 04 - Tools: Advertising and Invoking Capabilities

Tools are the heart of MCP. This chapter covers two key methods:
`list_tools` (advertise what you can do) and `call_tool` (execute a tool with
arguments).

## Protocol Component: Tool Discovery and Execution

`list_tools` returns a list of tool descriptors, including an input schema so
clients know how to call them.

Example `list_tools` response (trimmed):

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "tools": [
      {
        "name": "keyword_search",
        "description": "Search for keyword occurrences across directory trees.",
        "inputSchema": {
          "type": "object",
          "properties": {
            "keyword": {"type": "string"},
            "root_paths": {"type": "array", "items": {"type": "string"}}
          },
          "required": ["keyword", "root_paths"]
        }
      }
    ]
  }
}
```

`call_tool` executes the named tool. The response is a standard JSON-RPC result
payload with tool output in `content`.

## Minimal Implementation

```python
def handle_list_tools(request_id: int) -> dict:
    return success_response(request_id, {
        "tools": [
            {
                "name": "keyword_search",
                "description": "Search for keyword occurrences across directories.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "keyword": {"type": "string"},
                        "root_paths": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "required": ["keyword", "root_paths"]
                },
            }
        ]
    })

async def call_keyword_search(keyword: str, root_paths: list[str]) -> dict:
    result = await keyword_search_tool.execute(keyword, root_paths)
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
```

## Reference Implementation

The full tool lifecycle lives in:
- `WorkshopMCPServer._handle_list_tools` in `src/workshop_mcp/server.py`
- `WorkshopMCPServer._handle_call_tool` in `src/workshop_mcp/server.py`

You now have a working, from-scratch MCP server. Next, revisit the full server
implementation in `src/workshop_mcp/server.py` and compare it with the snippets
above.
