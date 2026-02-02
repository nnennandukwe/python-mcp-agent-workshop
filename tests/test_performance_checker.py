"""Tests for the performance checker module."""

import pytest

from workshop_mcp.performance_profiler.patterns import IssueCategory, Severity
from workshop_mcp.performance_profiler.performance_checker import PerformanceChecker


class TestPerformanceCheckerInitialization:
    """Test performance checker initialization."""

    def test_init_with_source_and_file(self, tmp_path):
        """Test initialization with source code and file path."""
        source = "def hello(): pass"
        checker = PerformanceChecker(source_code=source)
        assert checker.analyzer.source_code == source

        file_path = tmp_path / "test.py"
        file_path.write_text(source)
        checker = PerformanceChecker(file_path=str(file_path))
        assert checker.analyzer.source_code == source

    def test_init_without_source_or_file(self):
        """Test initialization fails without source or file."""
        with pytest.raises(ValueError):
            PerformanceChecker()


class TestNPlusOneDetection:
    """Test N+1 query detection."""

    def test_detect_n_plus_one_patterns(self):
        """Test detection of N+1 query patterns in loops."""
        source = """
for user in User.objects.all():
    print(user.profile.name)

for item in items:
    result = session.query(Model).filter(Model.id == item.id).first()
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_n_plus_one_queries()

        assert len(issues) >= 2
        assert all(i.category == IssueCategory.N_PLUS_ONE_QUERY for i in issues)
        assert all(i.severity == Severity.HIGH for i in issues)

    def test_no_n_plus_one_outside_loop(self):
        """Test queries outside loops are not flagged."""
        source = """
def get_users():
    return User.objects.all()
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_n_plus_one_queries()
        assert len(issues) == 0


class TestBlockingIOInAsync:
    """Test blocking I/O detection in async functions."""

    def test_detect_blocking_io_in_async(self):
        """Test detection of blocking I/O in async functions."""
        source = """
import time
import requests

async def bad_async():
    with open('file.txt') as f:
        data = f.read()
    time.sleep(1)
    response = requests.get("http://example.com")
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_blocking_io_in_async()

        assert len(issues) >= 3
        assert all(i.category == IssueCategory.BLOCKING_IO_IN_ASYNC for i in issues)
        assert all(i.severity == Severity.CRITICAL for i in issues)

        # Verify suggestions
        suggestions = [i.suggestion for i in issues]
        assert any("aiofiles" in s for s in suggestions)
        assert any("asyncio.sleep" in s for s in suggestions)
        assert any("aiohttp" in s for s in suggestions)

    def test_blocking_io_in_sync_function_ok(self):
        """Test blocking I/O in sync functions is not flagged."""
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
        deep_loop = [
            i
            for i in issues
            if "nested" in i.description.lower() or "depth" in i.description.lower()
        ]
        assert len(deep_loop) > 0
        assert deep_loop[0].category == IssueCategory.INEFFICIENT_LOOP
        assert deep_loop[0].severity == Severity.MEDIUM

    def test_no_issue_with_simple_loop(self):
        """Test simple loops are not flagged."""
        source = """
for item in items:
    process(item)
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_inefficient_loops()
        assert len(issues) == 0


class TestMemoryInefficiencies:
    """Test memory inefficiency detection."""

    def test_detect_memory_inefficiencies(self):
        """Test detection of memory inefficiency patterns."""
        source = """
import json
import pickle

with open('large.txt') as f:
    data1 = f.read()

with open('data.json') as f:
    data2 = json.load(f)

with open('data.pkl', 'rb') as f:
    data3 = pickle.load(f)

with open('file.txt') as f:
    lines = f.readlines()
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_memory_inefficiencies()

        assert len(issues) >= 4
        assert all(i.category == IssueCategory.MEMORY_INEFFICIENCY for i in issues)
        assert all(i.severity == Severity.MEDIUM for i in issues)

    def test_no_false_positives(self):
        """Test no false positives for unrelated functions."""
        source = """
def thread_reader():
    pass

def spreadsheet_loader():
    pass
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_memory_inefficiencies()
        assert len(issues) == 0


class TestCheckAllAndHelpers:
    """Test check_all and helper methods."""

    def test_check_all_aggregates_issues(self):
        """Test check_all aggregates all detected issues."""
        source = """
import time

async def process():
    with open('file.txt') as f:
        f.read()
    for user in User.objects.all():
        print(user.profile.name)
    time.sleep(1)
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_all()

        assert len(issues) >= 3
        categories = {i.category for i in issues}
        assert len(categories) >= 2

    def test_get_issues_by_severity_and_category(self):
        """Test filtering issues by severity and category."""
        source = """
async def bad():
    time.sleep(1)
    open('file.txt')

for user in User.objects.all():
    print(user)
"""
        checker = PerformanceChecker(source_code=source)
        checker.check_all()

        critical = checker.get_issues_by_severity(Severity.CRITICAL)
        assert len(critical) > 0
        assert all(i.severity == Severity.CRITICAL for i in critical)

        blocking = checker.get_issues_by_category(IssueCategory.BLOCKING_IO_IN_ASYNC)
        assert len(blocking) > 0
        assert all(i.category == IssueCategory.BLOCKING_IO_IN_ASYNC for i in blocking)

    def test_has_issues_and_summary(self):
        """Test has_issues and get_summary methods."""
        good_checker = PerformanceChecker(source_code="def good(): pass")
        bad_checker = PerformanceChecker(source_code="async def bad(): open('f.txt')")

        assert not good_checker.has_issues()
        assert bad_checker.has_issues()

        summary = bad_checker.get_summary()
        assert "total_issues" in summary
        assert "by_severity" in summary
        assert "by_category" in summary


class TestExceptionInLoops:
    """Test exception-in-loop detection."""

    def test_detect_try_except_in_for_loop(self):
        """Test detection of try/except inside for loop."""
        source = """
for item in items:
    try:
        process(item)
    except ValueError:
        handle_error(item)
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_exception_in_loops()

        assert len(issues) == 1
        assert issues[0].category == IssueCategory.EXCEPTION_IN_LOOP
        assert issues[0].severity == Severity.MEDIUM
        assert "try/except" in issues[0].description.lower()

    def test_detect_try_except_in_while_loop(self):
        """Test detection of try/except inside while loop."""
        source = """
while running:
    try:
        data = fetch_data()
    except ConnectionError:
        retry()
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_exception_in_loops()

        assert len(issues) == 1
        assert issues[0].category == IssueCategory.EXCEPTION_IN_LOOP

    def test_no_issue_try_except_outside_loop(self):
        """Test try/except outside loops is not flagged."""
        source = """
try:
    for item in items:
        process(item)
except ValueError:
    handle_error()
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_exception_in_loops()
        assert len(issues) == 0

    def test_nested_loop_try_except(self):
        """Test try/except in nested loop is detected."""
        source = """
for i in range(10):
    for j in range(10):
        try:
            compute(i, j)
        except ZeroDivisionError:
            pass
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_exception_in_loops()

        assert len(issues) == 1
        assert issues[0].line_number == 4


class TestTypeConversionsInLoops:
    """Test type conversion in loop detection."""

    def test_detect_int_conversion_in_loop(self):
        """Test detection of int() conversion inside loop."""
        source = """
for item in items:
    value = int(item)
    process(value)
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_type_conversions_in_loops()

        assert len(issues) == 1
        assert issues[0].category == IssueCategory.TYPE_CONVERSION_IN_LOOP
        assert issues[0].severity == Severity.MEDIUM
        assert "int" in issues[0].description

    def test_detect_multiple_conversions_in_loop(self):
        """Test detection of multiple type conversions in loop."""
        source = """
for item in data:
    x = int(item['x'])
    y = float(item['y'])
    name = str(item['id'])
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_type_conversions_in_loops()

        assert len(issues) == 3
        assert all(i.category == IssueCategory.TYPE_CONVERSION_IN_LOOP for i in issues)

    def test_no_issue_conversion_outside_loop(self):
        """Test type conversions outside loops are not flagged."""
        source = """
value = int("42")
items = list(range(10))
data = dict(a=1, b=2)
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_type_conversions_in_loops()
        assert len(issues) == 0

    def test_detect_list_dict_set_tuple_in_loop(self):
        """Test detection of container type conversions in loop."""
        source = """
for item in items:
    a = list(item)
    b = dict(item)
    c = set(item)
    d = tuple(item)
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_type_conversions_in_loops()

        assert len(issues) == 4
        conversion_types = [i.description for i in issues]
        assert any("list" in d for d in conversion_types)
        assert any("dict" in d for d in conversion_types)
        assert any("set" in d for d in conversion_types)
        assert any("tuple" in d for d in conversion_types)


class TestGlobalMutations:
    """Test global mutation detection."""

    def test_detect_global_in_function(self):
        """Test detection of global statement in function."""
        source = """
counter = 0

def increment():
    global counter
    counter += 1
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_global_mutations()

        assert len(issues) == 1
        assert issues[0].category == IssueCategory.GLOBAL_MUTATION
        assert issues[0].severity == Severity.MEDIUM
        assert "counter" in issues[0].description
        assert issues[0].function_name == "increment"

    def test_detect_multiple_globals(self):
        """Test detection of multiple global variables."""
        source = """
x = 0
y = 0

def update_coords():
    global x, y
    x += 1
    y += 1
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_global_mutations()

        assert len(issues) == 1
        assert "x" in issues[0].description
        assert "y" in issues[0].description

    def test_no_issue_global_at_module_level(self):
        """Test global at module level (outside function) is not flagged."""
        source = """
global_var = 10

# This is at module level, not inside a function
x = global_var + 1
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_global_mutations()
        assert len(issues) == 0

    def test_global_in_nested_function(self):
        """Test global in nested function is detected."""
        source = """
config = {}

def outer():
    def inner():
        global config
        config['key'] = 'value'
    inner()
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_global_mutations()

        assert len(issues) == 1
        assert issues[0].function_name == "inner"

    def test_suggestion_recommends_parameters(self):
        """Test suggestion recommends using parameters instead."""
        source = """
total = 0

def add(value):
    global total
    total += value
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_global_mutations()

        assert len(issues) == 1
        assert "parameter" in issues[0].suggestion.lower()


class TestComplexScenarios:
    """Test complex real-world scenarios."""

    def test_django_view_with_multiple_issues(self):
        """Test Django view with multiple performance problems."""
        source = """
import time

async def user_list(request):
    for user in User.objects.all():
        profile = user.profile.get()
        time.sleep(0.1)
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_all()

        assert len(issues) >= 2
        categories = {i.category for i in issues}
        assert len(categories) >= 2
        assert any(i.severity == Severity.CRITICAL for i in issues)

    def test_well_written_async_code(self):
        """Test well-written async code has no blocking I/O issues."""
        source = """
import asyncio
import aiofiles

async def fetch_data():
    async with aiofiles.open('cache.txt') as f:
        cache = await f.read()
    await asyncio.sleep(1)
    return cache
"""
        checker = PerformanceChecker(source_code=source)
        blocking = checker.get_issues_by_category(IssueCategory.BLOCKING_IO_IN_ASYNC)
        assert len(blocking) == 0

    def test_empty_and_comment_only_files(self):
        """Test empty and comment-only files."""
        empty = PerformanceChecker(source_code="")
        assert len(empty.check_all()) == 0

        comments = PerformanceChecker(source_code="# comment\n'''docstring'''")
        assert len(comments.check_all()) == 0
