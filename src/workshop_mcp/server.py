"""
FastMCP-based MCP Server for Workshop Keyword Search Tool

This module implements an MCP server using FastMCP that exposes the
keyword search functionality as a tool for AI agents over stdio.

It preserves the original CLI entrypoint (workshop-mcp-server) while
simplifying protocol handling via FastMCP's high-level API.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import Context, FastMCP
from pydantic import Field

from .keyword_search import KeywordSearchTool

# Instantiate FastMCP server
mcp = FastMCP(
    name="workshop-mcp-server",
)

# Reuse a single instance of the tool
_keyword_search_tool = KeywordSearchTool()


@mcp.tool(
    name="keyword_search",
    description=(
        "Search for keyword occurrences across directory trees. "
        "Supports multiple text file formats (.py, .java, .js, .ts, "
        ".html, .css, .json, .xml, .md, .txt, .yml, .yaml, etc.) "
        "and provides detailed statistics about matches."
    ),
    annotations={
        "title": "Keyword Search",
        "readOnlyHint": True,
        "openWorldHint": True,
        "idempotentHint": True,
    },
)
async def keyword_search(
    keyword: Annotated[
        str,
        Field(description="The keyword to search for (case-sensitive)", min_length=1),
    ],
    root_paths: Annotated[
        list[str],
        Field(description="List of directory paths to search in", min_length=1),
    ],
    ctx: Context,
) -> dict[str, Any]:
    """Execute an asynchronous keyword search across one or more root paths.

    Parameters are validated and documented via type annotations; FastMCP will
    generate the input schema automatically. Returning a dict enables structured
    output in addition to traditional content blocks.
    """
    await ctx.info(
        f"Executing keyword search for '{keyword}' in {len(root_paths)} paths"
    )

    # Delegate to the existing async tool implementation
    result = await _keyword_search_tool.execute(keyword, root_paths)

    # FastMCP automatically sends structured content for dict-like results
    return result


def sync_main() -> None:
    """Synchronous entry point for the FastMCP server (stdio by default)."""
    # FastMCP defaults to stdio transport, preserving original behavior
    mcp.run()


if __name__ == "__main__":
    sync_main()
