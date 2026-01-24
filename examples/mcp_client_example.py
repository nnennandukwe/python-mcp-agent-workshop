#!/usr/bin/env python3
"""
Example: Communicating with the MCP Server

This script demonstrates how to send JSON-RPC requests to the MCP server
and parse the responses. This is useful for:
- Testing the MCP server
- Building custom clients
- Understanding the MCP protocol

Run with:
    poetry run python examples/mcp_client_example.py
"""

import json
import subprocess
import sys
from typing import Any, Dict, Optional


def create_jsonrpc_request(
    method: str,
    params: Optional[Dict[str, Any]] = None,
    request_id: int = 1
) -> Dict[str, Any]:
    """Create a JSON-RPC 2.0 request."""
    request = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
    }
    if params is not None:
        request["params"] = params
    return request


def frame_message(request: Dict[str, Any]) -> bytes:
    """Frame a request with Content-Length header."""
    body = json.dumps(request)
    body_bytes = body.encode('utf-8')
    header = f"Content-Length: {len(body_bytes)}\r\n\r\n"
    return header.encode('utf-8') + body_bytes


def parse_response(data: bytes) -> Dict[str, Any]:
    """Parse a Content-Length framed response."""
    # Split header and body
    parts = data.split(b'\r\n\r\n', 1)
    if len(parts) != 2:
        raise ValueError("Invalid response format")

    header, body = parts

    # Parse Content-Length
    for line in header.decode('utf-8').split('\r\n'):
        if line.lower().startswith('content-length:'):
            expected_length = int(line.split(':', 1)[1].strip())
            break
    else:
        raise ValueError("Missing Content-Length header")

    # Parse JSON body
    return json.loads(body[:expected_length])


def send_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Send a request to the MCP server and get the response."""
    message = frame_message(request)

    # Start the server process
    proc = subprocess.Popen(
        [sys.executable, "-m", "workshop_mcp.server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=subprocess.os.path.dirname(subprocess.os.path.dirname(__file__))
    )

    # Send request and get response
    stdout, stderr = proc.communicate(input=message, timeout=30)

    if proc.returncode != 0 and not stdout:
        raise RuntimeError(f"Server error: {stderr.decode('utf-8')}")

    return parse_response(stdout)


def example_initialize():
    """Example: Initialize the MCP server."""
    print("\n" + "="*60)
    print("Example 1: Initialize")
    print("="*60)

    request = create_jsonrpc_request(
        method="initialize",
        params={"protocolVersion": "2024-11-05"},
        request_id=1
    )

    print(f"\nRequest:")
    print(json.dumps(request, indent=2))

    response = send_request(request)

    print(f"\nResponse:")
    print(json.dumps(response, indent=2))

    # Extract info
    if "result" in response:
        server_info = response["result"].get("serverInfo", {})
        print(f"\nServer: {server_info.get('name')} v{server_info.get('version')}")
        print(f"Protocol: {response['result'].get('protocolVersion')}")


def example_list_tools():
    """Example: List available tools."""
    print("\n" + "="*60)
    print("Example 2: List Tools")
    print("="*60)

    request = create_jsonrpc_request(
        method="list_tools",
        params={},
        request_id=2
    )

    print(f"\nRequest:")
    print(json.dumps(request, indent=2))

    response = send_request(request)

    print(f"\nResponse (tools list):")
    if "result" in response:
        for tool in response["result"]["tools"]:
            print(f"\n  Tool: {tool['name']}")
            print(f"  Description: {tool['description'][:80]}...")
            print(f"  Input Schema: {list(tool['inputSchema']['properties'].keys())}")


def example_call_performance_check():
    """Example: Call the performance_check tool."""
    print("\n" + "="*60)
    print("Example 3: Call performance_check Tool")
    print("="*60)

    # Analyze source code directly
    source_code = '''
async def bad_function():
    with open('file.txt') as f:
        return f.read()
'''

    request = create_jsonrpc_request(
        method="call_tool",
        params={
            "name": "performance_check",
            "arguments": {
                "source_code": source_code
            }
        },
        request_id=3
    )

    print(f"\nRequest:")
    print(json.dumps(request, indent=2))

    response = send_request(request)

    print(f"\nResponse:")
    if "result" in response:
        content = response["result"]["content"][0]
        if content["type"] == "json":
            result = content["json"]
            print(f"\nSuccess: {result['success']}")
            print(f"Total Issues: {result['summary']['total_issues']}")
            print(f"\nIssues:")
            for issue in result["issues"]:
                print(f"  [{issue['severity'].upper()}] Line {issue['line_number']}: "
                      f"{issue['description']}")
    elif "error" in response:
        print(f"\nError: {response['error']['message']}")


def example_call_keyword_search():
    """Example: Call the keyword_search tool."""
    print("\n" + "="*60)
    print("Example 4: Call keyword_search Tool")
    print("="*60)

    import os
    examples_dir = os.path.dirname(os.path.abspath(__file__))

    request = create_jsonrpc_request(
        method="call_tool",
        params={
            "name": "keyword_search",
            "arguments": {
                "keyword": "async",
                "root_paths": [examples_dir]
            }
        },
        request_id=4
    )

    print(f"\nRequest:")
    print(f"  Searching for 'async' in {examples_dir}")

    response = send_request(request)

    print(f"\nResponse:")
    if "result" in response:
        content = response["result"]["content"][0]
        if content["type"] == "text":
            result = json.loads(content["text"])
            summary = result.get("summary", {})
            print(f"  Total occurrences: {summary.get('total_occurrences', 0)}")
            print(f"  Files with matches: {summary.get('files_with_matches', 0)}")
    elif "error" in response:
        print(f"  Error: {response['error']['message']}")


def example_error_handling():
    """Example: Handle errors from the server."""
    print("\n" + "="*60)
    print("Example 5: Error Handling")
    print("="*60)

    # Try to analyze a non-existent file
    request = create_jsonrpc_request(
        method="call_tool",
        params={
            "name": "performance_check",
            "arguments": {
                "file_path": "/nonexistent/file.py"
            }
        },
        request_id=5
    )

    print(f"\nRequest: Analyze non-existent file")

    response = send_request(request)

    print(f"\nResponse:")
    if "error" in response:
        print(f"  Error Code: {response['error']['code']}")
        print(f"  Error Message: {response['error']['message']}")
    else:
        print(f"  Unexpected success: {response}")


def main():
    """Run all examples."""
    print("MCP Client Examples")
    print("==================")
    print("\nThis script demonstrates how to communicate with the MCP server")
    print("using JSON-RPC 2.0 over stdio with Content-Length framing.")

    try:
        example_initialize()
        example_list_tools()
        example_call_performance_check()
        example_call_keyword_search()
        example_error_handling()

        print("\n" + "="*60)
        print("All examples completed!")
        print("="*60)

    except subprocess.TimeoutExpired:
        print("\nError: Server timed out")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
