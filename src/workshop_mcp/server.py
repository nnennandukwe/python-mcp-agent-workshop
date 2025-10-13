"""
MCP Server for Workshop Keyword Search Tool

This module implements a Model Context Protocol (MCP) server using FastMCP
that exposes the keyword search functionality as a tool for AI agents.
"""

import logging
import sys
from typing import Any, Dict, List

from fastmcp import FastMCP

from .keyword_search import KeywordSearchTool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)

logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("workshop-mcp-server")

# Initialize keyword search tool
keyword_search_tool = KeywordSearchTool()


@mcp.tool()
async def keyword_search(keyword: str, root_paths: List[str]) -> Dict[str, Any]:
    """
    Search for keyword occurrences across directory trees.
    
    Supports multiple text file formats (.py, .java, .js, .ts, .html, .css, 
    .json, .xml, .md, .txt, .yml, .yaml, etc.) and provides detailed 
    statistics about matches.
    
    Args:
        keyword: The keyword to search for (case-sensitive)
        root_paths: List of directory paths to search in
        
    Returns:
        Dictionary containing search results with file paths, occurrence counts,
        and summary statistics including:
        - keyword: The searched keyword
        - root_paths: List of searched directories
        - files: Dictionary mapping file paths to occurrence data
        - summary: Statistics including total files searched, matches found,
                  total occurrences, and most frequent file
                  
    Raises:
        ValueError: If keyword is empty or root_paths is empty
        FileNotFoundError: If any root path doesn't exist
    """
    try:
        logger.info(f"Executing keyword search for '{keyword}' in {len(root_paths)} paths")
        
        result = await keyword_search_tool.execute(keyword, root_paths)
        
        logger.info(
            f"Search completed successfully: "
            f"{result['summary']['total_files_searched']} files searched, "
            f"{result['summary']['total_occurrences']} occurrences found"
        )
        
        return result
        
    except Exception as e:
        error_msg = f"Error executing keyword_search: {str(e)}"
        logger.error(error_msg)
        raise


def sync_main() -> None:
    """
    Synchronous entry point for the MCP server.
    
    This function is used as the script entry point in pyproject.toml.
    """
    try:
        logger.info("Starting Workshop MCP Server with FastMCP")
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    sync_main()
