"""
Comprehensive test suite for KeywordSearchTool

Tests cover basic functionality, edge cases, error handling, and ReDoS protection.
"""

import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

from workshop_mcp.keyword_search import KeywordSearchTool


@pytest_asyncio.fixture
async def search_tool() -> KeywordSearchTool:
    return KeywordSearchTool()


@pytest_asyncio.fixture
async def temp_test_directory() -> Path:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        test_files = {
            "test.py": 'def hello_world():\n    return "world"\n\nclass WorldClass:\n    pass',
            "test.txt": "The world is beautiful.\nWelcome to our world!",
            "test.md": "# Hello World\n\n## World Section",
            "empty_file.py": "",
            "subdir/nested.py": '# Nested\ndef nested_world():\n    return "world"',
        }
        for file_path, content in test_files.items():
            full_path = temp_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
        yield temp_path


class TestKeywordSearchBasics:
    """Test basic keyword search functionality."""

    @pytest.mark.asyncio
    async def test_basic_keyword_search(self, search_tool, temp_test_directory):
        """Test basic search returns proper structure and finds matches."""
        result = await search_tool.execute("world", [str(temp_test_directory)])

        assert result["keyword"] == "world"
        assert str(temp_test_directory) in result["root_paths"]
        assert result["summary"]["total_files_searched"] > 0
        assert result["summary"]["total_files_with_matches"] > 0
        assert result["summary"]["total_occurrences"] > 0

    @pytest.mark.asyncio
    async def test_case_sensitivity_and_insensitive_option(self, search_tool, temp_test_directory):
        """Test case-sensitive vs case-insensitive search."""
        result_lower = await search_tool.execute("world", [str(temp_test_directory)])
        result_upper = await search_tool.execute("WORLD", [str(temp_test_directory)])
        result_ci = await search_tool.execute(
            "WORLD", [str(temp_test_directory)], case_insensitive=True
        )

        # Case-sensitive should find different counts
        assert (
            result_lower["summary"]["total_occurrences"]
            != result_upper["summary"]["total_occurrences"]
        )
        # Case-insensitive should find at least as many as lowercase
        assert (
            result_ci["summary"]["total_occurrences"]
            >= result_lower["summary"]["total_occurrences"]
        )

    @pytest.mark.asyncio
    async def test_regex_search(self, search_tool, temp_test_directory):
        """Test regex pattern matching."""
        result = await search_tool.execute(r"w.rld", [str(temp_test_directory)], use_regex=True)
        assert result["summary"]["total_occurrences"] > 0

    @pytest.mark.asyncio
    async def test_include_exclude_patterns(self, search_tool, temp_test_directory):
        """Test file filtering with include/exclude patterns."""
        include_result = await search_tool.execute(
            "world", [str(temp_test_directory)], include_patterns=["*.md"]
        )
        assert all(f.endswith(".md") for f in include_result["files"].keys())

        exclude_result = await search_tool.execute(
            "world", [str(temp_test_directory)], exclude_patterns=["*.md"]
        )
        assert all(not f.endswith(".md") for f in exclude_result["files"].keys())

    @pytest.mark.asyncio
    async def test_nested_directory_and_empty_file(self, search_tool, temp_test_directory):
        """Test nested directories are searched and empty files handled."""
        result = await search_tool.execute("world", [str(temp_test_directory)])

        # Find nested file
        nested = [f for f in result["files"].keys() if "nested.py" in f]
        assert len(nested) == 1
        assert result["files"][nested[0]]["occurrences"] > 0

        # Find empty file
        empty = [f for f in result["files"].keys() if "empty_file.py" in f]
        assert len(empty) == 1
        assert result["files"][empty[0]]["occurrences"] == 0


class TestKeywordSearchErrors:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_empty_keyword_raises_error(self, search_tool, temp_test_directory):
        """Test empty keyword raises ValueError."""
        with pytest.raises(ValueError, match="Keyword cannot be empty"):
            await search_tool.execute("", [str(temp_test_directory)])

    @pytest.mark.asyncio
    async def test_empty_root_paths_raises_error(self, search_tool):
        """Test empty root paths raises ValueError."""
        with pytest.raises(ValueError, match="At least one root path"):
            await search_tool.execute("test", [])

    @pytest.mark.asyncio
    async def test_nonexistent_path_raises_error(self, search_tool):
        """Test nonexistent path raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Root path does not exist"):
            await search_tool.execute("test", ["/nonexistent/path"])

    @pytest.mark.asyncio
    async def test_file_as_root_raises_error(self, search_tool, temp_test_directory):
        """Test providing file instead of directory raises ValueError."""
        test_file = temp_test_directory / "test.py"
        with pytest.raises(ValueError, match="not a directory"):
            await search_tool.execute("test", [str(test_file)])


class TestSummaryCalculations:
    """Test summary statistics calculations."""

    @pytest.mark.asyncio
    async def test_summary_statistics_correct(self, search_tool, temp_test_directory):
        """Test summary statistics are calculated correctly."""
        result = await search_tool.execute("world", [str(temp_test_directory)])
        summary = result["summary"]

        # Verify totals match sum of individual files
        calculated_total = sum(d["occurrences"] for d in result["files"].values())
        assert summary["total_occurrences"] == calculated_total

        calculated_matches = sum(1 for d in result["files"].values() if d["occurrences"] > 0)
        assert summary["total_files_with_matches"] == calculated_matches

    @pytest.mark.asyncio
    async def test_no_matches_found(self, search_tool, temp_test_directory):
        """Test behavior when no matches found."""
        result = await search_tool.execute("nonexistent_xyz", [str(temp_test_directory)])

        assert result["summary"]["total_files_searched"] > 0
        assert result["summary"]["total_files_with_matches"] == 0
        assert result["summary"]["total_occurrences"] == 0
        assert result["summary"]["most_frequent_file"] is None


class TestReDoSProtection:
    """Test ReDoS protection."""

    @pytest.mark.asyncio
    async def test_rejects_dangerous_patterns(self, search_tool, tmp_path):
        """Test dangerous regex patterns are rejected."""
        from workshop_mcp.security import RegexValidationError

        (tmp_path / "test.py").write_text("hello")

        # Nested quantifiers
        with pytest.raises(RegexValidationError, match="nested quantifiers"):
            await search_tool.execute("(a+)+", [str(tmp_path)], use_regex=True)

        # Pattern exceeding length limit
        with pytest.raises(RegexValidationError, match="maximum length"):
            await search_tool.execute("a" * 501, [str(tmp_path)], use_regex=True)

    @pytest.mark.asyncio
    async def test_accepts_valid_regex(self, search_tool, tmp_path):
        """Test valid regex patterns work normally."""
        (tmp_path / "test.py").write_text("test123\nfoo456")

        result = await search_tool.execute(r"[a-z]+\d+", [str(tmp_path)], use_regex=True)
        assert result["summary"]["total_occurrences"] >= 2

    @pytest.mark.asyncio
    async def test_non_regex_mode_allows_special_chars(self, search_tool, tmp_path):
        """Test non-regex mode treats pattern as literal string."""
        (tmp_path / "test.py").write_text("(a+)+ test")

        result = await search_tool.execute("(a+)+", [str(tmp_path)], use_regex=False)
        assert result["summary"]["total_occurrences"] == 1

    @pytest.mark.asyncio
    async def test_timeout_skips_file_continues_search(self, search_tool, tmp_path, monkeypatch):
        """Test timeout on one file skips it and continues search."""
        (tmp_path / "file1.py").write_text("hello")
        (tmp_path / "file2.py").write_text("hello")

        call_count = [0]
        original = search_tool._count_occurrences

        def mock_count(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise TimeoutError("regex timed out")
            return original(*args, **kwargs)

        monkeypatch.setattr(search_tool, "_count_occurrences", mock_count)

        result = await search_tool.execute("hello", [str(tmp_path)], use_regex=True)
        assert len(result["metadata"]["skipped_files"]) == 1
        assert result["summary"]["total_files_searched"] >= 1

    @pytest.mark.asyncio
    async def test_abort_when_majority_timeout(self, search_tool, tmp_path, monkeypatch):
        """Test RegexAbortError raised when >50% files timeout."""
        from workshop_mcp.security import RegexAbortError

        (tmp_path / "file1.py").write_text("hello")
        (tmp_path / "file2.py").write_text("hello")
        (tmp_path / "file3.py").write_text("hello")

        def mock_count(*args, **kwargs):
            raise TimeoutError("timeout")

        monkeypatch.setattr(search_tool, "_count_occurrences", mock_count)

        with pytest.raises(RegexAbortError, match="timed out on too many files"):
            await search_tool.execute("hello", [str(tmp_path)], use_regex=True)


class TestFileTypeFiltering:
    """Test file type filtering."""

    def test_is_text_file_method(self, search_tool):
        """Test _is_text_file method with various extensions."""
        supported = [
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
        ]
        unsupported = [".bin", ".exe", ".pdf", ".jpg", ".png", ".zip"]

        for ext in supported:
            assert search_tool._is_text_file(Path(f"test{ext}")), f"Should support {ext}"
        for ext in unsupported:
            assert not search_tool._is_text_file(Path(f"test{ext}")), f"Should not support {ext}"
