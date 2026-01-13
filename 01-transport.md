# 01 - Transport: Framing MCP Messages Over stdio

This chapter builds the MCP transport layer from first principles. MCP servers
started by an agent typically communicate over **stdin/stdout** using a
`Content-Length` header followed by a JSON payload. This framing lets both sides
read exact message sizes from a streaming pipe.

## Protocol Component: Content-Length Framing

A single MCP/JSON-RPC message looks like this on the wire:

```
Content-Length: 123\r\n
\r\n
{...json payload...}
```

Key rules:
- Headers are ASCII/UTF-8 lines terminated by `\r\n`.
- A blank line ends the headers.
- `Content-Length` tells you how many bytes of JSON to read.

## Minimal Implementation

Below is the smallest possible read/write loop for the transport layer. The full
implementation lives in `src/workshop_mcp/server.py`.

```python
import json
import sys

stdin = sys.stdin.buffer
stdout = sys.stdout.buffer

# read headers
headers = {}
while True:
    line = stdin.readline()
    if line == b"":  # EOF
        raise RuntimeError("Unexpected EOF while reading headers")
    if line in (b"\n", b"\r\n"):
        break

    decoded = line.decode("utf-8", errors="replace").strip()
    if not decoded:
        break
    if ":" not in decoded:
        # Malformed header line; ignore or raise depending on strictness
        continue

    key, value = decoded.split(":", 1)
    headers[key.strip().lower()] = value.strip()

content_length = int(headers["content-length"])
body = stdin.read(content_length)
request = json.loads(body.decode("utf-8"))

# write response
payload = json.dumps(response).encode("utf-8")
stdout.write(f"Content-Length: {len(payload)}\r\n\r\n".encode("utf-8"))
stdout.write(payload)
stdout.flush()
```

## Reference Implementation

For the production-ready framing (error handling, EOF detection, and invalid
header checks), see:
- `WorkshopMCPServer._read_message` in `src/workshop_mcp/server.py`
- `WorkshopMCPServer._write_message` in `src/workshop_mcp/server.py`

Next: [02 - JSON-RPC Basics](02-jsonrpc.md)
