"""
MCP Server for Workshop Tools.

This module implements MCP over stdio without the official MCP SDK.
It handles JSON-RPC 2.0 parsing, Content-Length framing, and dispatches
requests to keyword search and performance profiler tools.
"""

import asyncio
import json
import logging
import sys
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional

from .keyword_search import KeywordSearchTool
from .performance_profiler import PerformanceChecker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)

logger = logging.getLogger(__name__)

JSONRPC_VERSION = "2.0"
DEFAULT_PROTOCOL_VERSION = "2024-11-05"


@dataclass
class JsonRpcError(Exception):
    code: int
    message: str
    data: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        return self.message


class WorkshopMCPServer:
    """
    MCP Server implementation for the Workshop Keyword Search Tool.

    This server exposes the keyword search functionality through the MCP protocol,
    allowing AI agents to search for keywords across directory trees.
    """

    def __init__(self) -> None:
        """Initialize the MCP server with keyword search tool."""
        self.keyword_search_tool = KeywordSearchTool()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def serve(self) -> None:
        """Run the server loop reading JSON-RPC messages from stdin."""
        logger.info("Starting Workshop MCP Server (from scratch)")
        stdin = sys.stdin.buffer
        stdout = sys.stdout.buffer

        try:
            while True:
                if not self._serve_once(stdin, stdout):
                    break
        finally:
            self.loop.close()
            logger.info("Server stopped and event loop closed")

    def serve_once(self, stdin: Any, stdout: Any) -> bool:
        """Public helper: process exactly one framed request from stdin.

        Returns:
            True if a message was processed (or an error response was written),
            False if EOF was reached before a full message could be read.
        """
        return self._serve_once(stdin, stdout)

    def _serve_once(self, stdin: Any, stdout: Any) -> bool:
        try:
            request = self._read_message(stdin)
            if request is None:
                return False

            response = self._handle_request(request)
            if response is not None:
                self._write_message(stdout, response)
            return True
        except JsonRpcError as err:
            # Best-effort: framing/parse errors before we have a request id
            self._write_message(stdout, self._error_response(None, err))
            return True
        except Exception as exc:
            logger.exception("Server loop error")
            self._write_message(
                stdout,
                self._error_response(
                    None,
                    JsonRpcError(-32603, "Internal error", {"details": str(exc)}),
                ),
            )
            return True

    def _read_message(self, stdin: Any) -> Optional[Dict[str, Any]]:
        headers: Dict[str, str] = {}
        while True:
            line = stdin.readline()
            if line == b"":
                return None
            if line in (b"\n", b"\r\n"):
                break
            decoded = line.decode("utf-8", errors="replace").strip()
            if not decoded:
                break
            if ":" not in decoded:
                continue
            key, value = decoded.split(":", 1)
            headers[key.strip().lower()] = value.strip()

        content_length_value = headers.get("content-length")
        if content_length_value is None:
            raise JsonRpcError(-32600, "Missing Content-Length header")

        try:
            content_length = int(content_length_value)
        except ValueError:
            raise JsonRpcError(-32600, "Invalid Content-Length header")

        body = stdin.read(content_length)
        if len(body) != content_length:
            return None

        try:
            return json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise JsonRpcError(-32700, "Parse error", {"details": str(exc)})

    def _write_message(self, stdout: Any, message: Dict[str, Any]) -> None:
        data = json.dumps(message, ensure_ascii=False)
        payload = data.encode("utf-8")
        header = f"Content-Length: {len(payload)}\r\n\r\n".encode("utf-8")
        stdout.write(header)
        stdout.write(payload)
        stdout.flush()

    def _handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(request, dict):
            return self._error_response(None, JsonRpcError(-32600, "Invalid Request"))

        if "error" in request and request.get("id") is None:
            return request

        jsonrpc = request.get("jsonrpc")
        method = request.get("method")

        # Notifications omit the "id" member entirely.
        if "id" not in request:
            return None

        request_id = request.get("id")

        # JSON-RPC 2.0: id MUST be string|number|null.
        if request_id is not None and not isinstance(request_id, (str, int)):
            return self._error_response(None, JsonRpcError(-32600, "Invalid Request"))

        if jsonrpc != JSONRPC_VERSION or not isinstance(method, str):
            return self._error_response(
                request_id, JsonRpcError(-32600, "Invalid Request")
            )

        if method == "initialize":
            return self._handle_initialize(request_id, request.get("params"))
        if method == "list_tools":
            return self._handle_list_tools(request_id)
        if method == "call_tool":
            return self._handle_call_tool(request_id, request.get("params"))

        return self._error_response(
            request_id,
            JsonRpcError(-32601, f"Method not found: {method}"),
        )

    def _handle_initialize(
        self, request_id: Any, params: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        if params is not None and not isinstance(params, dict):
            return self._error_response(
                request_id,
                JsonRpcError(-32602, "Invalid params", {"expected": "object"}),
            )

        params = params or {}
        protocol_version = params.get("protocolVersion", DEFAULT_PROTOCOL_VERSION)
        result = {
            "protocolVersion": protocol_version,
            "serverInfo": {"name": "workshop-mcp-server", "version": "0.1.0"},
            "capabilities": {"tools": {}},
        }
        return self._success_response(request_id, result)

    def _handle_list_tools(self, request_id: Any) -> Dict[str, Any]:
        result = {
            "tools": [
                {
                    "name": "keyword_search",
                    "description": (
                        "Search for keyword occurrences across directory trees. "
                        "Supports multiple text file formats (.py, .java, .js, .ts, "
                        ".html, .css, .json, .xml, .md, .txt, .yml, .yaml, etc.) "
                        "and provides detailed statistics about matches."
                    ),
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "keyword": {
                                "type": "string",
                                "description": "The keyword to search for (case-sensitive)",
                                "minLength": 1,
                            },
                            "root_paths": {
                                "type": "array",
                                "description": "List of directory paths to search in",
                                "items": {
                                    "type": "string",
                                    "description": "Directory path to search",
                                },
                                "minItems": 1,
                            },
                        },
                        "required": ["keyword", "root_paths"],
                    },
                },
                {
                    "name": "performance_check",
                    "description": (
                        "Analyze Python code for performance anti-patterns and inefficiencies. "
                        "Detects N+1 queries, blocking I/O in async functions, inefficient loops, "
                        "memory inefficiencies, and provides actionable suggestions for optimization."
                    ),
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the Python file to analyze",
                                "minLength": 1,
                            },
                            "source_code": {
                                "type": "string",
                                "description": "Optional Python source code string to analyze instead of file",
                            },
                        },
                        "oneOf": [
                            {"required": ["file_path"]},
                            {"required": ["source_code"]},
                        ],
                    },
                }
            ]
        }
        return self._success_response(request_id, result)

    def _handle_call_tool(
        self, request_id: Any, params: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        if not isinstance(params, dict):
            return self._error_response(
                request_id,
                JsonRpcError(-32602, "Invalid params", {"expected": "object"}),
            )

        name = params.get("name")
        arguments = params.get("arguments", {})

        if name == "keyword_search":
            return self._execute_keyword_search(request_id, arguments)
        elif name == "performance_check":
            return self._execute_performance_check(request_id, arguments)
        else:
            return self._error_response(
                request_id,
                JsonRpcError(-32602, "Unknown tool", {"tool": name}),
            )

    def _execute_keyword_search(
        self, request_id: Any, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return self._error_response(
                request_id,
                JsonRpcError(-32602, "Invalid params", {"expected": "object"}),
            )

        try:
            keyword = arguments["keyword"]
            root_paths = arguments["root_paths"]
        except KeyError as exc:
            return self._error_response(
                request_id,
                JsonRpcError(
                    -32602, "Missing required argument", {"missing": str(exc)}
                ),
            )

        if not isinstance(keyword, str):
            return self._error_response(
                request_id,
                JsonRpcError(-32602, "keyword must be a string"),
            )
        if not isinstance(root_paths, list) or not all(
            isinstance(path, str) for path in root_paths
        ):
            return self._error_response(
                request_id,
                JsonRpcError(-32602, "root_paths must be a list of strings"),
            )

        try:
            logger.info(
                "Executing keyword search for '%s' in %d paths",
                keyword,
                len(root_paths),
            )
            result = self.loop.run_until_complete(
                self.keyword_search_tool.execute(keyword, root_paths)
            )
            result_json = json.dumps(result, indent=2, ensure_ascii=False)
            payload = {
                "content": [{"type": "text", "text": result_json}],
            }
            return self._success_response(request_id, payload)
        except (ValueError, FileNotFoundError) as exc:
            # Parameter or resource error
            return self._error_response(
                request_id,
                JsonRpcError(-32602, str(exc)),
            )
        except Exception as exc:
            logger.exception("Error executing keyword_search")
            return self._error_response(
                request_id,
                JsonRpcError(
                    -32603,
                    "Internal error",
                    {"type": type(exc).__name__, "message": str(exc)},
                ),
            )

    def _execute_performance_check(
        self, request_id: Any, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return self._error_response(
                request_id,
                JsonRpcError(-32602, "Invalid params", {"expected": "object"}),
            )

        file_path = arguments.get("file_path")
        source_code = arguments.get("source_code")

        # Validate that exactly one is provided
        if not file_path and not source_code:
            return self._error_response(
                request_id,
                JsonRpcError(
                    -32602, "Either file_path or source_code must be provided"
                ),
            )
        if file_path and source_code:
            return self._error_response(
                request_id,
                JsonRpcError(
                    -32602, "Provide only one of file_path or source_code"
                ),
            )

        try:
            if file_path:
                logger.info("Executing performance check on file: %s", file_path)
                checker = PerformanceChecker(file_path=file_path)
            else:
                logger.info("Executing performance check on source code")
                checker = PerformanceChecker(source_code=source_code)

            # Run all performance checks
            issues = checker.check_all()

            # Get summary
            summary = checker.get_summary()

            # Format issues for output using list comprehension
            issues_data = [
                {
                    "category": issue.category.value,
                    "severity": issue.severity.value,
                    "line_number": issue.line_number,
                    "end_line_number": issue.end_line_number,
                    "description": issue.description,
                    "suggestion": issue.suggestion,
                    "code_snippet": issue.code_snippet,
                    "function_name": issue.function_name,
                }
                for issue in issues
            ]

            # Return structured result with schema-aligned fields
            result = {
                "content": [
                    {
                        "type": "json",
                        "json": {
                            "success": True,
                            "file_analyzed": file_path or "source_code",
                            "summary": summary,
                            "issues": issues_data,
                        },
                    }
                ],
            }
            return self._success_response(request_id, result)

        except (ValueError, FileNotFoundError, SyntaxError) as exc:
            # Parameter or resource error
            return self._error_response(
                request_id,
                JsonRpcError(-32602, str(exc)),
            )
        except Exception as exc:
            logger.exception("Error executing performance_check")
            return self._error_response(
                request_id,
                JsonRpcError(
                    -32603,
                    "Internal error",
                    {"type": type(exc).__name__, "message": str(exc)},
                ),
            )

    def _success_response(
        self, request_id: Any, result: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {"jsonrpc": JSONRPC_VERSION, "id": request_id, "result": result}

    def _error_response(self, request_id: Any, error: JsonRpcError) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "jsonrpc": JSONRPC_VERSION,
            "id": request_id,
            "error": {"code": error.code, "message": error.message},
        }
        if error.data is not None:
            payload["error"]["data"] = error.data
        return payload


def sync_main() -> None:
    """
    Synchronous entry point for the MCP server.

    This function is used as the script entry point in pyproject.toml.
    """
    server = WorkshopMCPServer()
    try:
        server.serve()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as exc:
        logger.error("Fatal error: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    sync_main()
