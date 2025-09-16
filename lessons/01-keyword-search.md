# Chapter 1: Building the Keyword Search Tool

## Objective
Create an async keyword search tool that can:
- Traverse directory trees efficiently
- Filter by file extensions  
- Count keyword occurrences
- Handle errors gracefully
- Provide detailed statistics

## Why Start Here?
Before we can build an AI agent, we need something useful for it to do! 
This tool will be the "brain" that does the actual work.

## Core Implementation

### Step 1: File Extension Filtering

We're going to build an asynchronous keyword search tool that searches for keywords across directory trees.
    
This Python class will support multiple text file formats and provide detailed statistics about keyword occurrences, file distribution, and search results.

Navigate to `/src/workshop_mcp/keyword_search.py`.

First, add all the imports we will use in this lesson at the top of the file.

```python
import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Set
import aiofiles

logger = logging.getLogger(__name__)
```

Next, let's create the `KeywordSearchTool` class.

```python
class KeywordSearchTool:
    
    # Supported text file extensions
    TEXT_EXTENSIONS: Set[str] = {
        '.py', '.java', '.js', '.ts', '.html', '.css', '.json', '.xml',
        '.md', '.txt', '.yml', '.yaml', '.c', '.cpp', '.h', '.hpp',
        '.go', '.rs', '.php', '.rb', '.swift', '.kt', '.scala'
    }
    
    def __init__(self) -> None:
        """Initialize the KeywordSearchTool."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def execute(self, keyword: str, root_paths: List[str]) -> Dict[str, Any]:
        """
        Execute keyword search across multiple root paths.
        
        Args:
            keyword: The keyword to search for (case-sensitive)
            root_paths: List of directory paths to search in
            
        Returns:
            Dictionary containing search results with file paths, occurrence counts,
            and summary statistics
            
        Raises:
            ValueError: If keyword is empty or root_paths is empty
            FileNotFoundError: If any root path doesn't exist
        """
        if not keyword.strip():
            raise ValueError("Keyword cannot be empty")
        
        if not root_paths:
            raise ValueError("At least one root path must be provided")
        
        # Initialize result structure
        result: Dict[str, Any] = {
            "keyword": keyword,
            "root_paths": root_paths,
            "files": {},
            "summary": {
                "total_files_searched": 0,
                "total_files_with_matches": 0,
                "total_occurrences": 0,
                "files_with_errors": 0,
                "most_frequent_file": None,
                "max_occurrences": 0
            }
        }
        
        # Search each root path
        search_tasks = []
        for root_path_str in root_paths:
            root_path = Path(root_path_str).resolve()
            if not root_path.exists():
                raise FileNotFoundError(f"Root path does not exist: {root_path}")
            
            if not root_path.is_dir():
                raise ValueError(f"Root path is not a directory: {root_path}")
            
            search_tasks.append(self._search_directory(root_path, keyword, result))
        
        # Execute all searches concurrently
        await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # Calculate final summary statistics
        self._calculate_summary(result)
        
        self.logger.info(
            f"Search completed: {result['summary']['total_files_searched']} files searched, "
            f"{result['summary']['total_files_with_matches']} files with matches, "
            f"{result['summary']['total_occurrences']} total occurrences"
        )
        
        return result
```

### Step 2: Async Directory Traversal Search

Next, implement a private, asynchronous directory traversal method.

```python
async def _search_directory(self, root_path: Path, keyword: str, result: Dict[str, Any]) -> None:
    """
    Recursively search a directory for keyword occurrences.
    
    Args:
        root_path: Path to the directory to search
        keyword: The keyword to search for
        result: Shared result dictionary to update
    """
    try:
        # Get all files recursively
        search_tasks = []
        
        for file_path in root_path.rglob("*"):
            if file_path.is_file() and self._is_text_file(file_path):
                search_tasks.append(self._search_file(file_path, keyword, result))
        
        # Process files concurrently in batches to avoid overwhelming the system
        batch_size = 50
        for i in range(0, len(search_tasks), batch_size):
            batch = search_tasks[i:i + batch_size]
            await asyncio.gather(*batch, return_exceptions=True)
            
    except PermissionError as e:
        self.logger.warning(f"Permission denied accessing directory {root_path}: {e}")
        result["summary"]["files_with_errors"] += 1
    except Exception as e:
        self.logger.error(f"Error searching directory {root_path}: {e}")
        result["summary"]["files_with_errors"] += 1
```

### Step 3: Process File Contents

Next, implement a method for searching files for keyword occurrences.

```python
async def _search_file(self, file_path: Path, keyword: str, result: Dict[str, Any]) -> None:
    """
    Search a single file for keyword occurrences.
    
    Args:
        file_path: Path to the file to search
        keyword: The keyword to search for
        result: Shared result dictionary to update
    """
    file_path_str = str(file_path)
    
    try:
        async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            content = await file.read()
            
            # Count occurrences (case-sensitive)
            occurrences = content.count(keyword)
            
            # Update result
            result["files"][file_path_str] = {
                "occurrences": occurrences,
                "size_bytes": file_path.stat().st_size,
                "extension": file_path.suffix.lower()
            }
            
            result["summary"]["total_files_searched"] += 1
            
            if occurrences > 0:
                result["summary"]["total_files_with_matches"] += 1
                result["summary"]["total_occurrences"] += occurrences
                
                self.logger.debug(f"Found {occurrences} occurrences in {file_path}")
            
    except PermissionError:
        self.logger.warning(f"Permission denied reading file: {file_path}")
        result["summary"]["files_with_errors"] += 1
    except UnicodeDecodeError:
        self.logger.debug(f"Skipping binary file: {file_path}")
        result["summary"]["files_with_errors"] += 1
    except Exception as e:
        self.logger.error(f"Error reading file {file_path}: {e}")
        result["summary"]["files_with_errors"] += 1
```

### Step 4: Add Helper Functions

Finally, add helper functions `_is_text_file` and `_calculate_summary` to be used by the methods we just created.

```python
def _is_text_file(self, file_path: Path) -> bool:
    """
    Check if a file is a supported text file based on its extension.
    
    Args:
        file_path: Path to the file to check
        
    Returns:
        True if the file is a supported text file, False otherwise
    """
    return file_path.suffix.lower() in self.TEXT_EXTENSIONS

    def _calculate_summary(self, result: Dict[str, Any]) -> None:
        """
        Calculate summary statistics for the search results.
        
        Args:
            result: Result dictionary to update with summary statistics
        """
        max_occurrences = 0
        most_frequent_file = None
        
        for file_path, file_data in result["files"].items():
            occurrences = file_data["occurrences"]
            if occurrences > max_occurrences:
                max_occurrences = occurrences
                most_frequent_file = file_path
        
        result["summary"]["max_occurrences"] = max_occurrences
        result["summary"]["most_frequent_file"] = most_frequent_file
        
        # Calculate additional statistics
        files_with_matches = result["summary"]["total_files_with_matches"]
        total_files = result["summary"]["total_files_searched"]
        
        result["summary"]["match_percentage"] = (
            (files_with_matches / total_files * 100) if total_files > 0 else 0.0
        )
        
        result["summary"]["average_occurrences_per_matching_file"] = (
            (result["summary"]["total_occurrences"] / files_with_matches) 
            if files_with_matches > 0 else 0.0
        )
```

Now that you have all the core and helper functions for implementing keyword search functionality in a codebase, run the unit test to confirm everything works correctly.

```bash
poetry run pytest tests/test_keyword_search.py -v
```


## Key Concepts Learned

- ✅ Async file operations for performance
- ✅ Batch processing to prevent resource exhaustion
- ✅ Comprehensive error handling
- ✅ Detailed statistics and analysis