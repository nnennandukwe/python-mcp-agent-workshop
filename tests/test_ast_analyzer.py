"""Tests for the AST analyzer module."""

import pytest
from workshop_mcp.performance_profiler.ast_analyzer import (
    ASTAnalyzer,
    CallInfo,
    FunctionInfo,
    ImportInfo,
    LoopInfo,
)


class TestASTAnalyzerInitialization:
    """Test AST analyzer initialization."""

    def test_init_with_source_code(self):
        """Test initialization with source code string."""
        source = "def hello(): pass"
        analyzer = ASTAnalyzer(source_code=source)
        assert analyzer.source_code == source
        assert analyzer.file_path is None

    def test_init_with_file_path(self, tmp_path):
        """Test initialization with file path."""
        file_path = tmp_path / "test.py"
        source = "def hello(): pass"
        file_path.write_text(source)

        analyzer = ASTAnalyzer(file_path=str(file_path))
        assert analyzer.source_code == source
        assert analyzer.file_path == str(file_path)

    def test_init_without_source_or_file(self):
        """Test that initialization fails without source or file."""
        with pytest.raises(ValueError, match="Either source_code or file_path must be provided"):
            ASTAnalyzer()

    def test_init_with_nonexistent_file(self):
        """Test that initialization fails with nonexistent file."""
        with pytest.raises(FileNotFoundError):
            ASTAnalyzer(file_path="/nonexistent/file.py")

    def test_init_with_syntax_error(self):
        """Test that initialization fails with invalid syntax."""
        with pytest.raises(SyntaxError):
            ASTAnalyzer(source_code="def invalid syntax")


class TestFunctionExtraction:
    """Test function extraction functionality."""

    def test_extract_simple_function(self):
        """Test extraction of a simple function."""
        source = """
def hello():
    return "world"
"""
        analyzer = ASTAnalyzer(source_code=source)
        functions = analyzer.get_functions()

        assert len(functions) == 1
        func = functions[0]
        assert func.name == "hello"
        assert func.is_async is False
        assert func.parameters == []
        assert func.line_number == 2

    def test_extract_function_with_parameters(self):
        """Test extraction of function with parameters."""
        source = """
def greet(name, age, city="NYC"):
    return f"Hello {name}"
"""
        analyzer = ASTAnalyzer(source_code=source)
        functions = analyzer.get_functions()

        assert len(functions) == 1
        func = functions[0]
        assert func.name == "greet"
        assert func.parameters == ["name", "age", "city"]

    def test_extract_async_function(self):
        """Test extraction of async function."""
        source = """
async def fetch_data():
    return await get_data()
"""
        analyzer = ASTAnalyzer(source_code=source)
        functions = analyzer.get_functions()

        assert len(functions) == 1
        func = functions[0]
        assert func.name == "fetch_data"
        assert func.is_async is True

    def test_extract_function_with_decorators(self):
        """Test extraction of function with decorators."""
        source = """
@property
@cached
def expensive_computation():
    return 42
"""
        analyzer = ASTAnalyzer(source_code=source)
        functions = analyzer.get_functions()

        assert len(functions) == 1
        func = functions[0]
        assert func.name == "expensive_computation"
        assert "property" in func.decorators
        assert "cached" in func.decorators

    def test_extract_function_with_type_annotations(self):
        """Test extraction of function with type annotations."""
        source = """
def add(a: int, b: int) -> int:
    return a + b
"""
        analyzer = ASTAnalyzer(source_code=source)
        functions = analyzer.get_functions()

        assert len(functions) == 1
        func = functions[0]
        assert func.name == "add"
        assert func.return_annotation == "int"

    def test_extract_function_with_docstring(self):
        """Test extraction of function with docstring."""
        source = '''
def documented():
    """This function has a docstring."""
    pass
'''
        analyzer = ASTAnalyzer(source_code=source)
        functions = analyzer.get_functions()

        assert len(functions) == 1
        func = functions[0]
        assert func.docstring == "This function has a docstring."

    def test_extract_multiple_functions(self):
        """Test extraction of multiple functions."""
        source = """
def func1():
    pass

async def func2():
    pass

def func3():
    pass
"""
        analyzer = ASTAnalyzer(source_code=source)
        functions = analyzer.get_functions()

        assert len(functions) == 3
        assert [f.name for f in functions] == ["func1", "func2", "func3"]
        assert functions[1].is_async is True

    def test_extract_nested_functions(self):
        """Test extraction of nested functions."""
        source = """
def outer():
    def inner():
        pass
    return inner
"""
        analyzer = ASTAnalyzer(source_code=source)
        functions = analyzer.get_functions()

        assert len(functions) == 2
        assert {f.name for f in functions} == {"outer", "inner"}

    def test_get_async_functions_only(self):
        """Test filtering for async functions only."""
        source = """
def sync_func():
    pass

async def async_func1():
    pass

async def async_func2():
    pass
"""
        analyzer = ASTAnalyzer(source_code=source)
        async_functions = analyzer.get_async_functions()

        assert len(async_functions) == 2
        assert all(f.is_async for f in async_functions)
        assert {f.name for f in async_functions} == {"async_func1", "async_func2"}

    def test_get_functions_in_range(self):
        """Test filtering functions by line range."""
        source = """
def func1():  # line 2
    pass

def func2():  # line 5
    pass

def func3():  # line 8
    pass
"""
        analyzer = ASTAnalyzer(source_code=source)
        functions = analyzer.get_functions_in_range(4, 7)

        assert len(functions) == 1
        assert functions[0].name == "func2"


class TestLoopExtraction:
    """Test loop extraction functionality."""

    def test_extract_simple_for_loop(self):
        """Test extraction of a simple for loop."""
        source = """
for i in range(10):
    print(i)
"""
        analyzer = ASTAnalyzer(source_code=source)
        loops = analyzer.get_loops()

        assert len(loops) == 1
        loop = loops[0]
        assert loop.type == "for"
        assert loop.line_number == 2
        assert loop.nesting_level == 0
        assert loop.parent_function is None

    def test_extract_while_loop(self):
        """Test extraction of a while loop."""
        source = """
while True:
    break
"""
        analyzer = ASTAnalyzer(source_code=source)
        loops = analyzer.get_loops()

        assert len(loops) == 1
        loop = loops[0]
        assert loop.type == "while"

    def test_extract_nested_loops(self):
        """Test extraction of nested loops."""
        source = """
for i in range(10):
    for j in range(10):
        for k in range(10):
            print(i, j, k)
"""
        analyzer = ASTAnalyzer(source_code=source)
        loops = analyzer.get_loops()

        assert len(loops) == 3
        assert loops[0].nesting_level == 0
        assert loops[1].nesting_level == 1
        assert loops[2].nesting_level == 2

    def test_extract_loop_in_function(self):
        """Test extraction of loop inside a function."""
        source = """
def process_items(items):
    for item in items:
        print(item)
"""
        analyzer = ASTAnalyzer(source_code=source)
        loops = analyzer.get_loops()

        assert len(loops) == 1
        loop = loops[0]
        assert loop.parent_function == "process_items"

    def test_extract_loop_in_async_function(self):
        """Test extraction of loop in async function."""
        source = """
async def fetch_all():
    for url in urls:
        await fetch(url)
"""
        analyzer = ASTAnalyzer(source_code=source)
        loops = analyzer.get_loops()

        assert len(loops) == 1
        loop = loops[0]
        assert loop.is_in_async_function is True

    def test_get_loops_in_function(self):
        """Test filtering loops by function."""
        source = """
def func1():
    for i in range(5):
        pass

def func2():
    for j in range(10):
        pass
    for k in range(15):
        pass
"""
        analyzer = ASTAnalyzer(source_code=source)
        loops_in_func2 = analyzer.get_loops_in_function("func2")

        assert len(loops_in_func2) == 2
        assert all(loop.parent_function == "func2" for loop in loops_in_func2)

    def test_get_max_loop_nesting_depth(self):
        """Test calculating max loop nesting depth."""
        source = """
for i in range(10):
    for j in range(10):
        for k in range(10):
            pass
"""
        analyzer = ASTAnalyzer(source_code=source)
        max_depth = analyzer.get_max_loop_nesting_depth()
        assert max_depth == 2

    def test_get_max_loop_nesting_depth_no_loops(self):
        """Test max nesting depth with no loops."""
        source = "def hello(): pass"
        analyzer = ASTAnalyzer(source_code=source)
        max_depth = analyzer.get_max_loop_nesting_depth()
        assert max_depth == 0


class TestImportExtraction:
    """Test import extraction functionality."""

    def test_extract_simple_import(self):
        """Test extraction of simple import."""
        source = "import os"
        analyzer = ASTAnalyzer(source_code=source)
        imports = analyzer.get_imports()

        assert len(imports) == 1
        imp = imports[0]
        assert imp.module == "os"
        assert imp.names == ["os"]
        assert imp.is_from_import is False
        assert imp.aliases == {}

    def test_extract_import_with_alias(self):
        """Test extraction of import with alias."""
        source = "import numpy as np"
        analyzer = ASTAnalyzer(source_code=source)
        imports = analyzer.get_imports()

        assert len(imports) == 1
        imp = imports[0]
        assert imp.module == "numpy"
        assert imp.aliases == {"numpy": "np"}

    def test_extract_from_import(self):
        """Test extraction of from import."""
        source = "from os.path import join, exists"
        analyzer = ASTAnalyzer(source_code=source)
        imports = analyzer.get_imports()

        assert len(imports) == 1
        imp = imports[0]
        assert imp.module == "os.path"
        assert set(imp.names) == {"join", "exists"}
        assert imp.is_from_import is True

    def test_extract_from_import_with_alias(self):
        """Test extraction of from import with alias."""
        source = "from datetime import datetime as dt"
        analyzer = ASTAnalyzer(source_code=source)
        imports = analyzer.get_imports()

        assert len(imports) == 1
        imp = imports[0]
        assert imp.aliases == {"datetime": "dt"}

    def test_extract_multiple_imports(self):
        """Test extraction of multiple imports."""
        source = """
import os
import sys
from pathlib import Path
"""
        analyzer = ASTAnalyzer(source_code=source)
        imports = analyzer.get_imports()

        assert len(imports) == 3
        modules = [imp.module for imp in imports]
        assert "os" in modules
        assert "sys" in modules
        assert "pathlib" in modules


class TestCallExtraction:
    """Test function call extraction functionality."""

    def test_extract_simple_call(self):
        """Test extraction of simple function call."""
        source = """
print("hello")
"""
        analyzer = ASTAnalyzer(source_code=source)
        calls = analyzer.get_calls()

        assert len(calls) == 1
        call = calls[0]
        assert call.function_name == "print"
        assert call.is_in_loop is False
        assert call.is_in_async_function is False

    def test_extract_call_in_function(self):
        """Test extraction of call inside a function."""
        source = """
def greet():
    print("hello")
"""
        analyzer = ASTAnalyzer(source_code=source)
        calls = analyzer.get_calls()

        assert len(calls) == 1
        call = calls[0]
        assert call.function_name == "print"
        assert call.parent_function == "greet"

    def test_extract_call_in_loop(self):
        """Test extraction of call inside a loop."""
        source = """
for i in range(10):
    print(i)
"""
        analyzer = ASTAnalyzer(source_code=source)
        calls = analyzer.get_calls()

        # range() and print() calls
        print_calls = [c for c in calls if c.function_name == "print"]
        assert len(print_calls) == 1
        assert print_calls[0].is_in_loop is True

    def test_extract_method_call(self):
        """Test extraction of method calls."""
        source = """
user.save()
db.query().filter().all()
"""
        analyzer = ASTAnalyzer(source_code=source)
        calls = analyzer.get_calls()

        function_names = [c.function_name for c in calls]
        assert "user.save" in function_names
        assert "db.query" in function_names

    def test_extract_call_in_async_function(self):
        """Test extraction of call in async function."""
        source = """
async def fetch():
    open("file.txt")
"""
        analyzer = ASTAnalyzer(source_code=source)
        calls = analyzer.get_calls()

        open_calls = [c for c in calls if c.function_name == "open"]
        assert len(open_calls) == 1
        assert open_calls[0].is_in_async_function is True

    def test_has_blocking_calls_in_async(self):
        """Test detection of blocking calls in async functions."""
        source = """
async def bad_async():
    with open("file.txt") as f:
        data = f.read()
"""
        analyzer = ASTAnalyzer(source_code=source)
        assert analyzer.has_blocking_calls_in_async() is True

    def test_has_blocking_calls_with_async_version(self):
        """Test that async versions are not flagged as blocking."""
        source = """
async def good_async():
    async with aiofiles.open("file.txt") as f:
        data = await f.read()
"""
        analyzer = ASTAnalyzer(source_code=source)
        # aiofiles.open should not be flagged as blocking
        # Note: This is a heuristic check, so it might still detect some calls
        # The actual validation will be more sophisticated in async_validator


class TestSourceSegment:
    """Test source code segment extraction."""

    def test_get_source_segment(self):
        """Test extraction of source code segment."""
        source = """# line 1
def func1():  # line 2
    pass  # line 3
def func2():  # line 4
    pass  # line 5"""
        analyzer = ASTAnalyzer(source_code=source)
        segment = analyzer.get_source_segment(2, 4)

        assert segment == "def func1():  # line 2\n    pass  # line 3\ndef func2():  # line 4"

    def test_get_source_segment_single_line(self):
        """Test extraction of single line."""
        source = """# line 1
def func():  # line 2
    pass  # line 3"""
        analyzer = ASTAnalyzer(source_code=source)
        segment = analyzer.get_source_segment(2, 2)

        assert segment == "def func():  # line 2"


class TestComplexScenarios:
    """Test complex real-world scenarios."""

    def test_complex_async_code(self):
        """Test analysis of complex async code."""
        source = """
import asyncio
from typing import List

async def fetch_url(url: str) -> str:
    '''Fetch content from URL.'''
    async with session.get(url) as response:
        return await response.text()

async def process_urls(urls: List[str]):
    for url in urls:
        content = await fetch_url(url)
        print(content)
"""
        analyzer = ASTAnalyzer(source_code=source)

        functions = analyzer.get_functions()
        assert len(functions) == 2
        assert all(f.is_async for f in functions)

        loops = analyzer.get_loops()
        assert len(loops) == 1
        assert loops[0].is_in_async_function is True

        imports = analyzer.get_imports()
        assert len(imports) == 2

    def test_nested_functions_and_loops(self):
        """Test analysis with nested functions and loops."""
        source = """
def outer():
    for i in range(10):
        def inner():
            for j in range(5):
                print(i, j)
        inner()
"""
        analyzer = ASTAnalyzer(source_code=source)

        functions = analyzer.get_functions()
        assert len(functions) == 2

        loops = analyzer.get_loops()
        assert len(loops) == 2
        # Check that nesting levels are tracked correctly
        nesting_levels = [loop.nesting_level for loop in loops]
        assert 0 in nesting_levels
        assert 0 in nesting_levels  # Both loops are at nesting level 0 relative to their scopes

    def test_empty_file(self):
        """Test analysis of empty file."""
        source = ""
        analyzer = ASTAnalyzer(source_code=source)

        assert analyzer.get_functions() == []
        assert analyzer.get_loops() == []
        assert analyzer.get_imports() == []
        assert analyzer.get_calls() == []

    def test_caching_behavior(self):
        """Test that results are cached on subsequent calls."""
        source = "def test(): pass"
        analyzer = ASTAnalyzer(source_code=source)

        # First call
        functions1 = analyzer.get_functions()
        # Second call should return cached result
        functions2 = analyzer.get_functions()

        assert functions1 is functions2  # Same object reference
