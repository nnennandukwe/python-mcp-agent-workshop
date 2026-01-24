"""
Keyword Search Tool for MCP Workshop

This module provides asynchronous keyword search functionality across directory trees,
supporting multiple text file formats with comprehensive error handling and statistics.
"""

import asyncio
import logging
import os
import re
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Dict, List, Optional, Pattern, Set

import aiofiles

logger = logging.getLogger(__name__)


class KeywordSearchTool:
    """
    Asynchronous keyword search tool that searches for keywords across directory trees.

    Supports multiple text file formats and provides detailed statistics about
    keyword occurrences, file distribution, and search results.
    """

    # Supported text file extensions
    TEXT_EXTENSIONS: Set[str] = {
        ".py",
        ".java",
        ".js",
        ".ts",
        ".html",
        ".css",
        ".json",
        ".xml",
        ".md",
        ".txt",
        ".yml",
        ".yaml",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".go",
        ".rs",
        ".php",
        ".rb",
        ".swift",
        ".kt",
        ".scala",
    }

    def __init__(self) -> None:
        """Initialize the KeywordSearchTool."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def execute(
        self,
        keyword: str,
        root_paths: List[str],
        *,
        case_insensitive: bool = False,
        use_regex: bool = False,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Execute keyword search across multiple root paths.

        Args:
            keyword: The keyword to search for (case-sensitive by default)
            root_paths: List of directory paths to search in
            case_insensitive: Whether to perform a case-insensitive search
            use_regex: Whether keyword is treated as a regular expression
            include_patterns: Optional list of glob patterns to include files
            exclude_patterns: Optional list of glob patterns to exclude files

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

        if include_patterns is not None and not all(
            isinstance(pattern, str) for pattern in include_patterns
        ):
            raise ValueError("include_patterns must be a list of strings")

        if exclude_patterns is not None and not all(
            isinstance(pattern, str) for pattern in exclude_patterns
        ):
            raise ValueError("exclude_patterns must be a list of strings")

        pattern = self._build_pattern(keyword, case_insensitive, use_regex)

        # Initialize result structure
        result: Dict[str, Any] = {
            "keyword": keyword,
            "root_paths": root_paths,
            "options": {
                "case_insensitive": case_insensitive,
                "use_regex": use_regex,
                "include_patterns": include_patterns or [],
                "exclude_patterns": exclude_patterns or [],
            },
            "files": {},
            "summary": {
                "total_files_searched": 0,
                "total_files_with_matches": 0,
                "total_occurrences": 0,
                "files_with_errors": 0,
                "most_frequent_file": None,
                "max_occurrences": 0,
            },
        }

        # Search each root path
        search_tasks = []
        for root_path_str in root_paths:
            root_path = Path(root_path_str).resolve()
            if not root_path.exists():
                raise FileNotFoundError(f"Root path does not exist: {root_path}")

            if not root_path.is_dir():
                raise ValueError(f"Root path is not a directory: {root_path}")

            search_tasks.append(
                self._search_directory(
                    root_path,
                    keyword,
                    pattern,
                    result,
                    include_patterns,
                    exclude_patterns,
                    case_insensitive,
                )
            )

        # Execute all searches concurrently
        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        for search_result in search_results:
            if isinstance(search_result, asyncio.CancelledError):
                raise search_result
            if isinstance(search_result, Exception):
                result["summary"]["files_with_errors"] += 1
                self.logger.error(
                    "Search task for a root path failed: %s",
                    search_result,
                    exc_info=True,
                )

                result.setdefault("search_errors", []).append(
                    f"Search task for a root path failed: {search_result}"
                )

        # Calculate final summary statistics
        self._calculate_summary(result)

        self.logger.info(
            f"Search completed: {result['summary']['total_files_searched']} files searched, "
            f"{result['summary']['total_files_with_matches']} files with matches, "
            f"{result['summary']['total_occurrences']} total occurrences"
        )

        return result

    async def _search_directory(
        self,
        root_path: Path,
        keyword: str,
        pattern: Optional[Pattern[str]],
        result: Dict[str, Any],
        include_patterns: Optional[List[str]],
        exclude_patterns: Optional[List[str]],
        case_insensitive: bool,
    ) -> None:
        """
        Recursively search a directory for keyword occurrences.

        Args:
            root_path: Path to the directory to search
            keyword: The keyword to search for
            pattern: Compiled regex pattern when use_regex is enabled
            result: Shared result dictionary to update
            include_patterns: Optional list of glob patterns to include files
            exclude_patterns: Optional list of glob patterns to exclude files
            case_insensitive: Whether to perform a case-insensitive search
        """
        try:
            # Use os.walk for efficient directory traversal with pruning
            search_tasks = []

            for dirpath, dirnames, filenames in os.walk(root_path):
                # Prune excluded directories to avoid traversing them
                # Modify dirnames in-place to prevent descent into excluded dirs
                if exclude_patterns:
                    dirnames[:] = [
                        d for d in dirnames
                        if not self._should_exclude_dir(d, dirpath, exclude_patterns)
                    ]

                for filename in filenames:
                    file_path = Path(dirpath) / filename

                    if not self._is_text_file(file_path):
                        continue
                    if not self._matches_filters(
                        file_path, include_patterns, exclude_patterns
                    ):
                        continue

                    search_tasks.append(
                        self._search_file(
                            file_path, keyword, pattern, result, case_insensitive
                        )
                    )

            # Process files concurrently in batches to avoid overwhelming the system
            batch_size = 50
            for i in range(0, len(search_tasks), batch_size):
                batch = search_tasks[i : i + batch_size]
                await asyncio.gather(*batch, return_exceptions=True)

        except PermissionError as e:
            self.logger.warning(
                f"Permission denied accessing directory {root_path}: {e}"
            )
            result["summary"]["files_with_errors"] += 1
        except Exception as e:
            self.logger.error(f"Error searching directory {root_path}: {e}")
            result["summary"]["files_with_errors"] += 1

    async def _search_file(
        self,
        file_path: Path,
        keyword: str,
        pattern: Optional[Pattern[str]],
        result: Dict[str, Any],
        case_insensitive: bool,
    ) -> None:
        """
        Search a single file for keyword occurrences.

        Args:
            file_path: Path to the file to search
            keyword: The keyword to search for
            pattern: Compiled regex pattern when use_regex is enabled
            result: Shared result dictionary to update
            case_insensitive: Whether to perform a case-insensitive search
        """
        file_path_str = str(file_path)

        try:
            async with aiofiles.open(
                file_path, "r", encoding="utf-8", errors="ignore"
            ) as file:
                content = await file.read()

                occurrences = self._count_occurrences(
                    content, keyword, pattern, case_insensitive
                )

                # Update result
                try:
                    size_bytes = file_path.stat().st_size
                except FileNotFoundError:
                    self.logger.warning("File disappeared before stat(): %s", file_path)
                    result["summary"]["files_with_errors"] += 1
                    return

                result["files"][file_path_str] = {
                    "occurrences": occurrences,
                    "size_bytes": size_bytes,
                    "extension": file_path.suffix.lower(),
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

    def _is_text_file(self, file_path: Path) -> bool:
        """
        Check if a file is a supported text file based on its extension.

        Args:
            file_path: Path to the file to check

        Returns:
            True if the file is a supported text file, False otherwise
        """
        return file_path.suffix.lower() in self.TEXT_EXTENSIONS

    def _build_pattern(
        self, keyword: str, case_insensitive: bool, use_regex: bool
    ) -> Optional[Pattern[str]]:
        if not use_regex:
            return None

        # Basic ReDoS protection: reject patterns with nested quantifiers
        # that could cause catastrophic backtracking (e.g., (a+)+, (.*)*)
        dangerous_patterns = [
            r'\([^)]*[+*][^)]*\)[+*]',  # Nested quantifiers like (a+)+
            r'\([^)]*\|[^)]*\)[+*]',     # Alternation with quantifier like (a|b)+
        ]
        for dangerous in dangerous_patterns:
            if re.search(dangerous, keyword):
                raise ValueError(
                    "Regex pattern rejected: potentially unsafe pattern detected"
                )

        flags = re.IGNORECASE if case_insensitive else 0
        try:
            return re.compile(keyword, flags=flags)
        except re.error:
            raise ValueError("Invalid regex pattern")

    def _count_occurrences(
        self,
        content: str,
        keyword: str,
        pattern: Optional[Pattern[str]],
        case_insensitive: bool,
    ) -> int:
        if pattern is not None:
            return len(pattern.findall(content))
        if case_insensitive:
            # Use re.findall with IGNORECASE instead of content.lower()
            # to avoid creating a full lowercase copy of large files
            return len(re.findall(re.escape(keyword), content, re.IGNORECASE))
        return content.count(keyword)

    def _should_exclude_dir(
        self,
        dirname: str,
        parent_path: str,
        exclude_patterns: List[str],
    ) -> bool:
        """Check if a directory should be excluded from traversal."""
        dir_path = Path(parent_path) / dirname
        dir_path_str = dir_path.as_posix()

        return any(
            fnmatch(dir_path_str, pattern) or fnmatch(dirname, pattern)
            for pattern in exclude_patterns
        )

    def _matches_filters(
        self,
        file_path: Path,
        include_patterns: Optional[List[str]],
        exclude_patterns: Optional[List[str]],
    ) -> bool:
        file_path_str = file_path.as_posix()
        file_name = file_path.name

        if include_patterns:
            if not any(
                fnmatch(file_path_str, pattern) or fnmatch(file_name, pattern)
                for pattern in include_patterns
            ):
                return False

        if exclude_patterns:
            if any(
                fnmatch(file_path_str, pattern) or fnmatch(file_name, pattern)
                for pattern in exclude_patterns
            ):
                return False

        return True

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
            if files_with_matches > 0
            else 0.0
        )
