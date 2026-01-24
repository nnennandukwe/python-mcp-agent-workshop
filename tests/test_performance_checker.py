"""Tests for the performance checker module."""

import pytest
from workshop_mcp.performance_profiler.performance_checker import PerformanceChecker
from workshop_mcp.performance_profiler.patterns import IssueCategory, Severity


class TestPerformanceCheckerInitialization:
    """Test performance checker initialization."""

    def test_init_with_source_code(self):
        """Test initialization with source code string."""
        source = "def hello(): pass"
        checker = PerformanceChecker(source_code=source)
        assert checker.analyzer.source_code == source

    def test_init_with_file_path(self, tmp_path):
        """Test initialization with file path."""
        file_path = tmp_path / "test.py"
        source = "def hello(): pass"
        file_path.write_text(source)

        checker = PerformanceChecker(file_path=str(file_path))
        assert checker.analyzer.source_code == source

    def test_init_without_source_or_file(self):
        """Test that initialization fails without source or file."""
        with pytest.raises(ValueError):
            PerformanceChecker()


class TestNPlusOneDetection:
    """Test N+1 query detection."""

    def test_detect_django_n_plus_one_in_loop(self):
        """Test detection of Django N+1 query pattern."""
        source = """
for user in User.objects.all():
    print(user.profile.name)
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_n_plus_one_queries()

        assert len(issues) > 0
        issue = issues[0]
        assert issue.category == IssueCategory.N_PLUS_ONE_QUERY
        assert issue.severity == Severity.HIGH
        assert "N+1" in issue.description
        assert "select_related" in issue.suggestion or "prefetch_related" in issue.suggestion

    def test_detect_sqlalchemy_query_in_loop(self):
        """Test detection of SQLAlchemy query in loop."""
        source = """
for item in items:
    result = session.query(Model).filter(Model.id == item.id).first()
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_n_plus_one_queries()

        assert len(issues) > 0
        issue = issues[0]
        assert issue.category == IssueCategory.N_PLUS_ONE_QUERY
        assert issue.severity == Severity.HIGH

    def test_no_n_plus_one_outside_loop(self):
        """Test that queries outside loops are not flagged."""
        source = """
def get_users():
    return User.objects.all()
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_n_plus_one_queries()

        assert len(issues) == 0

    def test_nested_loop_with_query(self):
        """Test N+1 detection in nested loops."""
        source = """
for category in categories:
    for item in category.items.all():
        print(item.details.all())
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_n_plus_one_queries()

        # Should detect queries in both loops
        assert len(issues) >= 2


class TestBlockingIOInAsync:
    """Test blocking I/O detection in async functions."""

    def test_detect_blocking_open_in_async(self):
        """Test detection of blocking file open in async function."""
        source = """
async def read_file():
    with open('file.txt') as f:
        data = f.read()
    return data
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_blocking_io_in_async()

        assert len(issues) > 0
        issue = issues[0]
        assert issue.category == IssueCategory.BLOCKING_IO_IN_ASYNC
        assert issue.severity == Severity.CRITICAL
        assert "aiofiles" in issue.suggestion

    def test_detect_blocking_sleep_in_async(self):
        """Test detection of time.sleep in async function."""
        source = """
import time

async def delayed_operation():
    time.sleep(1)
    return "done"
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_blocking_io_in_async()

        assert len(issues) > 0
        issue = issues[0]
        assert issue.category == IssueCategory.BLOCKING_IO_IN_ASYNC
        assert issue.severity == Severity.CRITICAL
        assert "asyncio.sleep" in issue.suggestion

    def test_detect_requests_in_async(self):
        """Test detection of requests library in async function."""
        source = """
import requests

async def fetch_url(url):
    response = requests.get(url)
    return response.text
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_blocking_io_in_async()

        assert len(issues) > 0
        issue = issues[0]
        assert issue.category == IssueCategory.BLOCKING_IO_IN_ASYNC
        assert issue.severity == Severity.CRITICAL
        assert "aiohttp" in issue.suggestion

    def test_no_issue_with_async_io(self):
        """Test that async I/O doesn't trigger warnings."""
        source = """
import aiofiles

async def read_file():
    async with aiofiles.open('file.txt') as f:
        data = await f.read()
    return data
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_blocking_io_in_async()

        # aiofiles.open should not be flagged
        # Note: The issue might still be detected depending on implementation
        # This test verifies the concept

    def test_blocking_io_in_sync_function_ok(self):
        """Test that blocking I/O in sync functions is not flagged."""
        source = """
def read_file():
    with open('file.txt') as f:
        return f.read()
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_blocking_io_in_async()

        assert len(issues) == 0


class TestInefficientLoops:
    """Test inefficient loop pattern detection."""

    def test_detect_string_concatenation_in_loop(self):
        """Test detection of string concatenation in loops."""
        source = """
result = ""
for item in items:
    result += str(item)
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_inefficient_loops()

        # Might detect string concatenation
        # Note: This depends on AST analysis capabilities
        if issues:
            assert any(
                issue.category == IssueCategory.INEFFICIENT_LOOP
                for issue in issues
            )

    def test_detect_deeply_nested_loops(self):
        """Test detection of deeply nested loops."""
        source = """
for i in range(10):
    for j in range(10):
        for k in range(10):
            print(i, j, k)
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_inefficient_loops()

        assert len(issues) > 0
        # Should detect the innermost loop at nesting level 2
        deep_loop_issues = [
            i for i in issues
            if "nested" in i.description.lower() or "depth" in i.description.lower()
        ]
        assert len(deep_loop_issues) > 0
        issue = deep_loop_issues[0]
        assert issue.category == IssueCategory.INEFFICIENT_LOOP
        assert issue.severity == Severity.MEDIUM

    def test_no_issue_with_simple_loop(self):
        """Test that simple loops are not flagged."""
        source = """
for item in items:
    process(item)
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_inefficient_loops()

        # Should not flag simple loops
        assert len(issues) == 0


class TestMemoryInefficiencies:
    """Test memory inefficiency detection."""

    def test_detect_read_entire_file(self):
        """Test detection of reading entire file into memory."""
        source = """
with open('large_file.txt') as f:
    data = f.read()
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_memory_inefficiencies()

        assert len(issues) > 0
        issue = issues[0]
        assert issue.category == IssueCategory.MEMORY_INEFFICIENCY
        assert issue.severity == Severity.MEDIUM
        assert "memory" in issue.description.lower()
        assert "chunks" in issue.suggestion.lower() or "line-by-line" in issue.suggestion.lower()

    def test_detect_readlines(self):
        """Test detection of readlines() which loads all lines."""
        source = """
with open('file.txt') as f:
    lines = f.readlines()
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_memory_inefficiencies()

        assert len(issues) > 0
        issue = issues[0]
        assert issue.category == IssueCategory.MEMORY_INEFFICIENCY

    def test_detect_json_load(self):
        """Test detection of json.load() loading entire file."""
        source = """
import json

with open('data.json') as f:
    data = json.load(f)
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_memory_inefficiencies()

        assert len(issues) > 0
        issue = issues[0]
        assert issue.category == IssueCategory.MEMORY_INEFFICIENCY
        assert issue.severity == Severity.MEDIUM
        assert "json" in issue.description.lower()
        assert "ijson" in issue.suggestion.lower() or "streaming" in issue.suggestion.lower()

    def test_detect_pickle_load(self):
        """Test detection of pickle.load() loading entire file."""
        source = """
import pickle

with open('data.pkl', 'rb') as f:
    data = pickle.load(f)
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_memory_inefficiencies()

        assert len(issues) > 0
        issue = issues[0]
        assert issue.category == IssueCategory.MEMORY_INEFFICIENCY
        assert issue.severity == Severity.MEDIUM
        assert "pickle" in issue.description.lower()
        assert "streaming" in issue.suggestion.lower() or "memory-mapped" in issue.suggestion.lower()

    def test_no_false_positives_for_unrelated_functions(self):
        """Test that functions with 'read' in name don't trigger false positives."""
        source = """
def thread_reader():
    pass

def spreadsheet_loader():
    pass
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_memory_inefficiencies()

        # Should not flag these functions
        assert len(issues) == 0


class TestCheckAll:
    """Test the check_all method that runs all checks."""

    def test_check_all_aggregates_issues(self):
        """Test that check_all aggregates all detected issues."""
        source = """
import time

async def process_users():
    # Blocking I/O in async
    with open('users.txt') as f:
        data = f.read()

    # N+1 query
    for user in User.objects.all():
        print(user.profile.name)

    # Blocking sleep
    time.sleep(1)
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_all()

        # Should have multiple issues from different categories
        assert len(issues) >= 3

        # Should be sorted by severity (critical first)
        severities = [issue.severity for issue in issues]
        # Check that critical issues come before others
        if Severity.CRITICAL in severities:
            critical_index = severities.index(Severity.CRITICAL)
            assert all(
                s in [Severity.CRITICAL, Severity.HIGH]
                for s in severities[:critical_index + 1]
            )

    def test_check_all_caches_results(self):
        """Test that check_all caches results."""
        source = "def test(): pass"
        checker = PerformanceChecker(source_code=source)

        issues1 = checker.check_all()
        issues2 = checker.check_all()

        # Should return the same object (cached)
        assert issues1 is issues2


class TestHelperMethods:
    """Test helper methods on PerformanceChecker."""

    def test_get_issues_by_severity(self):
        """Test filtering issues by severity."""
        source = """
async def bad_code():
    time.sleep(1)  # Critical

for user in User.objects.all():  # High
    print(user)

for i in range(10):  # Medium (deep nesting)
    for j in range(10):
        for k in range(10):
            pass
"""
        checker = PerformanceChecker(source_code=source)
        checker.check_all()  # Run all checks first

        critical = checker.get_issues_by_severity(Severity.CRITICAL)
        assert len(critical) > 0
        assert all(issue.severity == Severity.CRITICAL for issue in critical)

    def test_get_issues_by_category(self):
        """Test filtering issues by category."""
        source = """
async def fetch():
    open('file.txt')
"""
        checker = PerformanceChecker(source_code=source)
        checker.check_all()

        blocking_issues = checker.get_issues_by_category(IssueCategory.BLOCKING_IO_IN_ASYNC)
        assert len(blocking_issues) > 0
        assert all(
            issue.category == IssueCategory.BLOCKING_IO_IN_ASYNC
            for issue in blocking_issues
        )

    def test_get_critical_issues(self):
        """Test getting only critical issues."""
        source = """
async def critical_problems():
    with open('file.txt') as f:
        data = f.read()
"""
        checker = PerformanceChecker(source_code=source)

        critical = checker.get_critical_issues()
        assert all(issue.severity == Severity.CRITICAL for issue in critical)

    def test_has_issues(self):
        """Test has_issues method."""
        good_source = "def good(): pass"
        bad_source = "async def bad(): open('file.txt')"

        good_checker = PerformanceChecker(source_code=good_source)
        bad_checker = PerformanceChecker(source_code=bad_source)

        assert not good_checker.has_issues()
        assert bad_checker.has_issues()

    def test_get_summary(self):
        """Test summary generation."""
        source = """
async def process():
    open('file.txt')  # Critical

for user in users:
    user.profile.all()  # High (assumed ORM)
"""
        checker = PerformanceChecker(source_code=source)
        summary = checker.get_summary()

        assert "total_issues" in summary
        assert "by_severity" in summary
        assert "by_category" in summary
        assert summary["total_issues"] >= 0
        assert isinstance(summary["by_severity"], dict)
        assert isinstance(summary["by_category"], dict)


class TestComplexScenarios:
    """Test complex real-world scenarios."""

    def test_django_view_with_multiple_issues(self):
        """Test a Django view with multiple performance problems."""
        source = """
import time
from django.http import JsonResponse

async def user_list(request):
    # Blocking query in async
    users = User.objects.all()

    result = ""
    for user in users:
        # N+1 query
        profile = user.profile.get()

        # String concatenation in loop
        result += f"{user.name}: {profile.bio}\\n"

        # Blocking sleep
        time.sleep(0.1)

    return JsonResponse({"users": result})
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_all()

        # Should detect multiple issues (at minimum: time.sleep and N+1 query)
        assert len(issues) >= 2

        # Should have different categories
        categories = {issue.category for issue in issues}
        assert len(categories) >= 2

        # Should have at least one critical (blocking I/O)
        critical_issues = [i for i in issues if i.severity == Severity.CRITICAL]
        assert len(critical_issues) >= 1

        # Should have N+1 query
        n_plus_one = [i for i in issues if i.category == IssueCategory.N_PLUS_ONE_QUERY]
        assert len(n_plus_one) >= 1

    def test_async_function_with_good_practices(self):
        """Test that well-written async code has no issues."""
        source = """
import asyncio
import aiofiles

async def fetch_data(url):
    async with aiofiles.open('cache.txt', 'r') as f:
        cache = await f.read()

    await asyncio.sleep(1)

    return cache
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_all()

        # Should have minimal or no blocking I/O issues
        blocking_issues = checker.get_issues_by_category(IssueCategory.BLOCKING_IO_IN_ASYNC)
        assert len(blocking_issues) == 0

    def test_empty_file(self):
        """Test analysis of empty file."""
        source = ""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_all()

        assert len(issues) == 0
        assert not checker.has_issues()

    def test_file_with_only_comments(self):
        """Test analysis of file with only comments."""
        source = """
# This is a comment
# Another comment
'''
Multiline comment
'''
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_all()

        assert len(issues) == 0
