"""
Comprehensive test suite for KeywordSearchTool

Tests cover basic functionality, edge cases, error handling, and performance
scenarios to ensure robust keyword search implementation.
"""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest
import pytest_asyncio

from workshop_mcp.keyword_search import KeywordSearchTool


class TestKeywordSearchTool:
    """Test suite for KeywordSearchTool functionality."""

    @pytest_asyncio.fixture
    async def search_tool(self) -> KeywordSearchTool:
        """Create a KeywordSearchTool instance for testing."""
        return KeywordSearchTool()

    @pytest_asyncio.fixture
    async def temp_test_directory(self) -> Path:
        """Create a temporary directory with test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files with different extensions and content
            test_files = {
                "test.py": """
def hello_world():
    print("Hello, world!")
    return "world"

class WorldClass:
    def __init__(self):
        self.world = "world"
""",
                "test.java": """
public class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello, world!");
        String world = "world";
    }
}
""",
                "test.txt": """
This is a simple text file.
It contains the word world multiple times.
The world is a beautiful place.
Welcome to our world!
""",
                "test.json": """
{
    "message": "Hello, world!",
    "data": {
        "world": "Earth",
        "greeting": "world"
    }
}
""",
                "test.md": """
# Hello World

This is a markdown file about the world.

## World Section

The world is full of possibilities.
""",
                "binary_file.bin": b"\x00\x01\x02\x03\x04\x05",  # Binary content
                "empty_file.py": "",  # Empty file
                "subdir/nested.py": """
# Nested file in subdirectory
def nested_world():
    return "nested world"
""",
            }

            # Create files
            for file_path, content in test_files.items():
                full_path = temp_path / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)

                if isinstance(content, bytes):
                    full_path.write_bytes(content)
                else:
                    full_path.write_text(content, encoding="utf-8")

            yield temp_path

    @pytest.mark.asyncio
    async def test_basic_keyword_search(
        self, search_tool: KeywordSearchTool, temp_test_directory: Path
    ):
        """Test basic keyword search functionality."""
        result = await search_tool.execute("world", [str(temp_test_directory)])

        # Verify result structure
        assert "keyword" in result
        assert "root_paths" in result
        assert "files" in result
        assert "summary" in result

        # Verify keyword and paths
        assert result["keyword"] == "world"
        assert str(temp_test_directory) in result["root_paths"]

        # Verify summary statistics
        summary = result["summary"]
        assert summary["total_files_searched"] > 0
        assert summary["total_files_with_matches"] > 0
        assert summary["total_occurrences"] > 0
        assert summary["most_frequent_file"] is not None
        assert summary["max_occurrences"] > 0

        # Verify specific file results
        files_with_world = [
            file_path
            for file_path, data in result["files"].items()
            if data["occurrences"] > 0
        ]
        assert len(files_with_world) > 0

        # Check that we found occurrences in expected files
        found_extensions = set()
        for file_path, data in result["files"].items():
            if data["occurrences"] > 0:
                found_extensions.add(Path(file_path).suffix)

        expected_extensions = {".py", ".java", ".txt", ".json", ".md"}
        assert found_extensions.intersection(expected_extensions)

    @pytest.mark.asyncio
    async def test_case_sensitivity(
        self, search_tool: KeywordSearchTool, temp_test_directory: Path
    ):
        """Test that keyword search is case-sensitive."""
        # Search for lowercase "world"
        result_lower = await search_tool.execute("world", [str(temp_test_directory)])

        # Search for uppercase "WORLD"
        result_upper = await search_tool.execute("WORLD", [str(temp_test_directory)])

        # Results should be different due to case sensitivity
        assert (
            result_lower["summary"]["total_occurrences"]
            != result_upper["summary"]["total_occurrences"]
        )

        # Lowercase should have more matches in our test files
        assert (
            result_lower["summary"]["total_occurrences"]
            > result_upper["summary"]["total_occurrences"]
        )

    @pytest.mark.asyncio
    async def test_case_insensitive_option(
        self, search_tool: KeywordSearchTool, temp_test_directory: Path
    ):
        """Test that case-insensitive search finds matches across cases."""
        result_lower = await search_tool.execute("world", [str(temp_test_directory)])
        result_upper = await search_tool.execute(
            "WORLD", [str(temp_test_directory)], case_insensitive=True
        )

        # Case-insensitive search should find *at least* the matches of a
        # case-sensitive search, and may find more if the corpus contains
        # different casings (e.g., "World").
        assert (
            result_upper["summary"]["total_occurrences"]
            >= result_lower["summary"]["total_occurrences"]
        )

        # Also verify that case-insensitive search is independent of the
        # provided casing of the keyword.
        result_lower_ci = await search_tool.execute(
            "world", [str(temp_test_directory)], case_insensitive=True
        )
        assert (
            result_upper["summary"]["total_occurrences"]
            == result_lower_ci["summary"]["total_occurrences"]
        )

    @pytest.mark.asyncio
    async def test_regex_option(
        self, search_tool: KeywordSearchTool, temp_test_directory: Path
    ):
        """Test that regex search finds pattern matches."""
        result = await search_tool.execute(
            r"w.rld", [str(temp_test_directory)], use_regex=True
        )

        assert result["summary"]["total_occurrences"] > 0

    @pytest.mark.asyncio
    async def test_regex_redos_protection(
        self, search_tool: KeywordSearchTool, temp_test_directory: Path
    ):
        """Test that dangerous regex patterns are rejected to prevent ReDoS."""
        # Pattern with nested quantifiers that could cause catastrophic backtracking
        dangerous_patterns = [
            r"(a+)+",      # Classic ReDoS pattern
            r"(.*)*",      # Nested star quantifiers
            r"(a|b)+",     # Alternation with quantifier
        ]

        for pattern in dangerous_patterns:
            with pytest.raises(ValueError, match="potentially unsafe pattern"):
                await search_tool.execute(
                    pattern, [str(temp_test_directory)], use_regex=True
                )

    @pytest.mark.asyncio
    async def test_include_exclude_patterns(
        self, search_tool: KeywordSearchTool, temp_test_directory: Path
    ):
        """Test that include/exclude patterns filter files."""
        include_result = await search_tool.execute(
            "world", [str(temp_test_directory)], include_patterns=["*.md"]
        )

        assert include_result["summary"]["total_files_searched"] > 0
        assert all(
            file_path.endswith(".md")
            for file_path in include_result["files"].keys()
        )

        exclude_result = await search_tool.execute(
            "world", [str(temp_test_directory)], exclude_patterns=["*.md"]
        )
        assert all(
            not file_path.endswith(".md")
            for file_path in exclude_result["files"].keys()
        )

    @pytest.mark.asyncio
    async def test_multiple_root_paths(
        self, search_tool: KeywordSearchTool, temp_test_directory: Path
    ):
        """Test searching across multiple root paths."""
        # Create a second temporary directory
        with tempfile.TemporaryDirectory() as temp_dir2:
            temp_path2 = Path(temp_dir2)

            # Create additional test file
            test_file = temp_path2 / "additional.py"
            test_file.write_text(
                "# Additional file with world keyword\nworld_var = 'world'"
            )

            # Search both directories
            result = await search_tool.execute(
                "world", [str(temp_test_directory), str(temp_path2)]
            )

            # Verify both paths are included
            assert str(temp_test_directory) in result["root_paths"]
            assert str(temp_path2) in result["root_paths"]

            # Verify we found files from both directories
            file_paths = list(result["files"].keys())
            paths_from_dir1 = [p for p in file_paths if str(temp_test_directory) in p]
            paths_from_dir2 = [p for p in file_paths if str(temp_path2) in p]

            assert len(paths_from_dir1) > 0
            assert len(paths_from_dir2) > 0

    @pytest.mark.asyncio
    async def test_empty_keyword_error(
        self, search_tool: KeywordSearchTool, temp_test_directory: Path
    ):
        """Test that empty keyword raises ValueError."""
        with pytest.raises(ValueError, match="Keyword cannot be empty"):
            await search_tool.execute("", [str(temp_test_directory)])

        with pytest.raises(ValueError, match="Keyword cannot be empty"):
            await search_tool.execute("   ", [str(temp_test_directory)])

    @pytest.mark.asyncio
    async def test_empty_root_paths_error(self, search_tool: KeywordSearchTool):
        """Test that empty root paths list raises ValueError."""
        with pytest.raises(ValueError, match="At least one root path must be provided"):
            await search_tool.execute("test", [])

    @pytest.mark.asyncio
    async def test_nonexistent_path_error(self, search_tool: KeywordSearchTool):
        """Test that nonexistent path raises FileNotFoundError."""
        nonexistent_path = "/path/that/does/not/exist"

        with pytest.raises(FileNotFoundError, match="Root path does not exist"):
            await search_tool.execute("test", [nonexistent_path])

    @pytest.mark.asyncio
    async def test_file_as_root_path_error(
        self, search_tool: KeywordSearchTool, temp_test_directory: Path
    ):
        """Test that providing a file instead of directory raises ValueError."""
        # Create a test file
        test_file = temp_test_directory / "test_file.txt"
        test_file.write_text("test content")

        with pytest.raises(ValueError, match="Root path is not a directory"):
            await search_tool.execute("test", [str(test_file)])

    @pytest.mark.asyncio
    async def test_no_matches_found(
        self, search_tool: KeywordSearchTool, temp_test_directory: Path
    ):
        """Test behavior when no matches are found."""
        result = await search_tool.execute(
            "nonexistent_keyword_xyz", [str(temp_test_directory)]
        )

        # Verify structure is still correct
        assert result["summary"]["total_files_searched"] > 0
        assert result["summary"]["total_files_with_matches"] == 0
        assert result["summary"]["total_occurrences"] == 0
        assert result["summary"]["most_frequent_file"] is None
        assert result["summary"]["max_occurrences"] == 0
        assert result["summary"]["match_percentage"] == 0.0
        assert result["summary"]["average_occurrences_per_matching_file"] == 0.0

    @pytest.mark.asyncio
    async def test_file_extension_filtering(
        self, search_tool: KeywordSearchTool, temp_test_directory: Path
    ):
        """Test that only supported text file extensions are processed."""
        result = await search_tool.execute("world", [str(temp_test_directory)])

        # Check that binary files are not included in results
        binary_files = [
            file_path
            for file_path in result["files"].keys()
            if file_path.endswith(".bin")
        ]
        assert len(binary_files) == 0

        # Check that text files are included
        text_files = [
            file_path
            for file_path in result["files"].keys()
            if any(
                file_path.endswith(ext)
                for ext in [".py", ".java", ".txt", ".json", ".md"]
            )
        ]
        assert len(text_files) > 0

    @pytest.mark.asyncio
    async def test_empty_file_handling(
        self, search_tool: KeywordSearchTool, temp_test_directory: Path
    ):
        """Test that empty files are handled correctly."""
        result = await search_tool.execute("world", [str(temp_test_directory)])

        # Find the empty file in results
        empty_file_path = None
        for file_path, data in result["files"].items():
            if file_path.endswith("empty_file.py"):
                empty_file_path = file_path
                break

        assert empty_file_path is not None
        assert result["files"][empty_file_path]["occurrences"] == 0
        assert result["files"][empty_file_path]["size_bytes"] == 0

    @pytest.mark.asyncio
    async def test_nested_directory_search(
        self, search_tool: KeywordSearchTool, temp_test_directory: Path
    ):
        """Test that nested directories are searched correctly."""
        result = await search_tool.execute("world", [str(temp_test_directory)])

        # Find the nested file
        nested_file_path = None
        for file_path in result["files"].keys():
            if "nested.py" in file_path:
                nested_file_path = file_path
                break

        assert nested_file_path is not None
        assert result["files"][nested_file_path]["occurrences"] > 0

    @pytest.mark.asyncio
    async def test_summary_calculations(
        self, search_tool: KeywordSearchTool, temp_test_directory: Path
    ):
        """Test that summary statistics are calculated correctly."""
        result = await search_tool.execute("world", [str(temp_test_directory)])

        summary = result["summary"]

        # Verify total occurrences matches sum of individual file occurrences
        calculated_total = sum(data["occurrences"] for data in result["files"].values())
        assert summary["total_occurrences"] == calculated_total

        # Verify files with matches count
        calculated_matches = sum(
            1 for data in result["files"].values() if data["occurrences"] > 0
        )
        assert summary["total_files_with_matches"] == calculated_matches

        # Verify match percentage calculation
        expected_percentage = (
            (calculated_matches / summary["total_files_searched"] * 100)
            if summary["total_files_searched"] > 0
            else 0.0
        )
        assert abs(summary["match_percentage"] - expected_percentage) < 0.01

        # Verify average occurrences calculation
        expected_average = (
            (calculated_total / calculated_matches) if calculated_matches > 0 else 0.0
        )
        assert (
            abs(summary["average_occurrences_per_matching_file"] - expected_average)
            < 0.01
        )

    @pytest.mark.asyncio
    async def test_most_frequent_file_identification(
        self, search_tool: KeywordSearchTool, temp_test_directory: Path
    ):
        """Test that the most frequent file is identified correctly."""
        result = await search_tool.execute("world", [str(temp_test_directory)])

        summary = result["summary"]
        most_frequent_file = summary["most_frequent_file"]
        max_occurrences = summary["max_occurrences"]

        if most_frequent_file:
            # Verify the most frequent file actually has the max occurrences
            assert result["files"][most_frequent_file]["occurrences"] == max_occurrences

            # Verify no other file has more occurrences
            for file_path, data in result["files"].items():
                assert data["occurrences"] <= max_occurrences

    @pytest.mark.asyncio
    async def test_concurrent_search_performance(self, search_tool: KeywordSearchTool):
        """Test that concurrent searches work correctly and efficiently."""
        # Create multiple temporary directories with files
        temp_dirs = []
        try:
            for i in range(3):
                temp_dir = tempfile.mkdtemp()
                temp_path = Path(temp_dir)
                temp_dirs.append(temp_path)

                # Create multiple files in each directory
                for j in range(5):
                    test_file = temp_path / f"test_{j}.py"
                    test_file.write_text(
                        f"# File {j} with world keyword\nworld_var_{j} = 'world'"
                    )

            # Run concurrent searches
            search_tasks = [
                search_tool.execute("world", [str(temp_dir)]) for temp_dir in temp_dirs
            ]

            results = await asyncio.gather(*search_tasks)

            # Verify all searches completed successfully
            assert len(results) == 3

            for result in results:
                assert result["summary"]["total_files_searched"] == 5
                assert result["summary"]["total_occurrences"] > 0

        finally:
            # Clean up temporary directories
            import shutil

            for temp_dir in temp_dirs:
                shutil.rmtree(temp_dir, ignore_errors=True)

    def test_is_text_file_method(self, search_tool: KeywordSearchTool):
        """Test the _is_text_file method with various file extensions."""
        # Test supported extensions
        supported_files = [
            Path("test.py"),
            Path("test.java"),
            Path("test.js"),
            Path("test.ts"),
            Path("test.html"),
            Path("test.css"),
            Path("test.json"),
            Path("test.xml"),
            Path("test.md"),
            Path("test.txt"),
            Path("test.yml"),
            Path("test.yaml"),
        ]

        for file_path in supported_files:
            assert search_tool._is_text_file(
                file_path
            ), f"Should support {file_path.suffix}"

        # Test unsupported extensions
        unsupported_files = [
            Path("test.bin"),
            Path("test.exe"),
            Path("test.pdf"),
            Path("test.jpg"),
            Path("test.png"),
            Path("test.zip"),
            Path("test.tar.gz"),
        ]

        for file_path in unsupported_files:
            assert not search_tool._is_text_file(
                file_path
            ), f"Should not support {file_path.suffix}"
