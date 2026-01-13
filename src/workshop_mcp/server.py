"""
MCP Server for Workshop Keyword Search Tool

This module implements a Model Context Protocol (MCP) server that exposes
the keyword search functionality as a tool for AI agents.
"""

import asyncio
import json
import logging
import sys
from typing import Any, Dict, List, Sequence

from mcp.server import Server
from mcp.server.lowlevel import NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    TextContent,
    Tool,
)

from .keyword_search import KeywordSearchTool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)

logger = logging.getLogger(__name__)


class WorkshopMCPServer:
    """
    MCP Server implementation for the Workshop Keyword Search Tool.

    This server exposes the keyword search functionality through the MCP protocol,
    allowing AI agents to search for keywords across directory trees.
    """

    def __init__(self) -> None:
        """Initialize the MCP server with keyword search tool."""
        self.server = Server("workshop-mcp-server")
        self.keyword_search_tool = KeywordSearchTool()
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Set up MCP protocol handlers."""

        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """
            Handle list_tools request - return available tools with their schemas.

            Returns:
                List of available tools with input schemas
            """
            return [
                Tool(
                    name="keyword_search",
                    description=(
                        "Search for keyword occurrences across directory trees. "
                        "Supports multiple text file formats (.py, .java, .js, .ts, "
                        ".html, .css, .json, .xml, .md, .txt, .yml, .yaml, etc.) "
                        "and provides detailed statistics about matches."
                    ),
                    inputSchema={
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
                )
            ]

        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: Dict[str, Any]
        ) -> List[TextContent]:
            """
            Handle call_tool request - execute the requested tool.

            Args:
                name: Name of the tool to execute
                arguments: Tool arguments

            Returns:
                List of text content with tool results

            Raises:
                ValueError: If tool name is unknown or arguments are invalid
            """
            if name != "keyword_search":
                raise ValueError(f"Unknown tool: {name}")

            try:
                # Validate required arguments
                if "keyword" not in arguments:
                    raise ValueError("Missing required argument: keyword")

                if "root_paths" not in arguments:
                    raise ValueError("Missing required argument: root_paths")

                keyword = arguments["keyword"]
                root_paths = arguments["root_paths"]

                # Validate argument types
                if not isinstance(keyword, str):
                    raise ValueError("keyword must be a string")

                if not isinstance(root_paths, list):
                    raise ValueError("root_paths must be a list")

                if not all(isinstance(path, str) for path in root_paths):
                    raise ValueError("All root_paths must be strings")

                # Execute keyword search
                logger.info(
                    f"Executing keyword search for '{keyword}' in {len(root_paths)} paths"
                )

                result = await self.keyword_search_tool.execute(keyword, root_paths)

                # Format result as JSON
                result_json = json.dumps(result, indent=2, ensure_ascii=False)

                logger.info(
                    f"Search completed successfully: "
                    f"{result['summary']['total_files_searched']} files searched, "
                    f"{result['summary']['total_occurrences']} occurrences found"
                )

                return [TextContent(type="text", text=result_json)]

            except Exception as e:
                error_msg = f"Error executing keyword_search: {str(e)}"
                logger.error(error_msg)

                # Return error as structured JSON
                error_result = {
                    "error": {
                        "type": type(e).__name__,
                        "message": str(e),
                        "tool": "keyword_search",
                        "arguments": arguments,
                    }
                }

                return [
                    TextContent(type="text", text=json.dumps(error_result, indent=2))
                ]

    async def run(self) -> None:
        """
        Run the MCP server with stdio transport.

        This method starts the server and handles the MCP protocol communication
        over stdin/stdout.
        """
        logger.info("Starting Workshop MCP Server")

        try:
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name="workshop-mcp-server",
                        server_version="0.1.0",
                        capabilities=self.server.get_capabilities(
                            notification_options=NotificationOptions(),
                            experimental_capabilities={},
                        ),
                    ),
                )
        except KeyboardInterrupt:
            logger.info("Server shutdown requested")
        except Exception as e:
            logger.error(f"Server error: {e}")
            raise


async def main() -> None:
    """
    Main entry point for the MCP server.

    Creates and runs the Workshop MCP Server instance.
    """
    server = WorkshopMCPServer()
    await server.run()


def sync_main() -> None:
    """
    Synchronous entry point for the MCP server.

    This function is used as the script entry point in pyproject.toml.
    """
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    sync_main()
