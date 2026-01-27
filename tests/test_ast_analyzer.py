"""Tests for the AST analyzer module."""

import pytest
from workshop_mcp.performance_profiler.ast_analyzer import ASTAnalyzer


class TestASTAnalyzerInitialization:
    """Test AST analyzer initialization."""

    def test_init_with_source_and_file(self, tmp_path):
        """Test initialization with source code and file path."""
        source = "def hello(): pass"
        analyzer = ASTAnalyzer(source_code=source)
        assert analyzer.source_code == source
        assert analyzer.file_path is None

        file_path = tmp_path / "test.py"
        file_path.write_text(source)
        analyzer = ASTAnalyzer(file_path=str(file_path))
        assert analyzer.source_code == source
        assert analyzer.file_path == str(file_path)

    def test_init_errors(self):
        """Test initialization errors."""
        with pytest.raises(ValueError, match="Either source_code or file_path"):
            ASTAnalyzer()
        with pytest.raises(FileNotFoundError):
            ASTAnalyzer(file_path="/nonexistent/file.py")
        with pytest.raises(SyntaxError):
            ASTAnalyzer(source_code="def invalid syntax")


class TestFunctionExtraction:
    """Test function extraction functionality."""

    def test_extract_function_properties(self):
        """Test extraction of function with various properties."""
        source = '''
@property
@cached
def greet(name, age, city="NYC") -> str:
    """Greet a person."""
    return f"Hello {name}"

async def fetch_data():
    return await get_data()
'''
        analyzer = ASTAnalyzer(source_code=source)
        functions = analyzer.get_functions()

        assert len(functions) == 2

        greet = next(f for f in functions if f.name == "greet")
        assert greet.parameters == ["name", "age", "city"]
        assert greet.is_async is False
        assert "property" in greet.decorators
        assert greet.return_annotation == "str"
        assert greet.docstring == "Greet a person."

        fetch = next(f for f in functions if f.name == "fetch_data")
        assert fetch.is_async is True

    def test_nested_and_multiple_functions(self):
        """Test extraction of nested and multiple functions."""
        source = """
def outer():
    def inner():
        pass
    return inner

def func2():
    pass

async def func3():
    pass
"""
        analyzer = ASTAnalyzer(source_code=source)
        functions = analyzer.get_functions()

        assert len(functions) == 4
        assert {f.name for f in functions} == {"outer", "inner", "func2", "func3"}

        async_funcs = analyzer.get_async_functions()
        assert len(async_funcs) == 1
        assert async_funcs[0].name == "func3"

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

    def test_extract_loops_with_nesting(self):
        """Test extraction of loops with nesting levels."""
        source = """
def process_items(items):
    for i in range(10):
        for j in range(10):
            for k in range(10):
                print(i, j, k)

while True:
    break
"""
        analyzer = ASTAnalyzer(source_code=source)
        loops = analyzer.get_loops()

        assert len(loops) == 4
        for_loops = [l for l in loops if l.type == "for"]
        while_loops = [l for l in loops if l.type == "while"]
        assert len(for_loops) == 3
        assert len(while_loops) == 1

        # Check nesting levels
        nesting_levels = sorted([l.nesting_level for l in for_loops])
        assert nesting_levels == [0, 1, 2]

        # Check parent function
        loops_in_func = [l for l in loops if l.parent_function == "process_items"]
        assert len(loops_in_func) == 3

    def test_loop_in_async_function(self):
        """Test loop detection in async function."""
        source = """
async def fetch_all():
    for url in urls:
        await fetch(url)
"""
        analyzer = ASTAnalyzer(source_code=source)
        loops = analyzer.get_loops()
        assert len(loops) == 1
        assert loops[0].is_in_async_function is True

    def test_get_max_loop_nesting_depth(self):
        """Test calculating max loop nesting depth."""
        source = """
for i in range(10):
    for j in range(10):
        for k in range(10):
            pass
"""
        analyzer = ASTAnalyzer(source_code=source)
        assert analyzer.get_max_loop_nesting_depth() == 2

        empty_analyzer = ASTAnalyzer(source_code="def hello(): pass")
        assert empty_analyzer.get_max_loop_nesting_depth() == 0


class TestImportExtraction:
    """Test import extraction functionality."""

    def test_extract_imports(self):
        """Test extraction of various import types."""
        source = """
import os
import numpy as np
from os.path import join, exists
from datetime import datetime as dt
"""
        analyzer = ASTAnalyzer(source_code=source)
        imports = analyzer.get_imports()

        assert len(imports) == 4

        os_import = next(i for i in imports if i.module == "os" and not i.is_from_import)
        assert os_import.names == ["os"]

        np_import = next(i for i in imports if i.module == "numpy")
        assert np_import.aliases == {"numpy": "np"}

        path_import = next(i for i in imports if i.module == "os.path")
        assert set(path_import.names) == {"join", "exists"}
        assert path_import.is_from_import is True

        dt_import = next(i for i in imports if i.module == "datetime")
        assert dt_import.aliases == {"datetime": "dt"}


class TestCallExtraction:
    """Test function call extraction functionality."""

    def test_extract_calls(self):
        """Test extraction of various call types."""
        source = """
def greet():
    print("hello")

for i in range(10):
    process(i)

user.save()
"""
        analyzer = ASTAnalyzer(source_code=source)
        calls = analyzer.get_calls()

        print_call = next(c for c in calls if c.function_name == "print")
        assert print_call.parent_function == "greet"
        assert print_call.is_in_loop is False

        process_call = next(c for c in calls if c.function_name == "process")
        assert process_call.is_in_loop is True

        save_call = next(c for c in calls if c.function_name == "user.save")
        assert save_call is not None

    def test_has_blocking_calls_in_async(self):
        """Test detection of blocking calls in async functions."""
        source = """
async def bad_async():
    with open("file.txt") as f:
        data = f.read()
"""
        analyzer = ASTAnalyzer(source_code=source)
        assert analyzer.has_blocking_calls_in_async() is True


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


class TestComplexScenarios:
    """Test complex real-world scenarios."""

    def test_complex_async_code(self):
        """Test analysis of complex async code."""
        source = """
import asyncio
from typing import List

async def fetch_url(url: str) -> str:
    async with session.get(url) as response:
        return await response.text()

async def process_urls(urls: List[str]):
    for url in urls:
        content = await fetch_url(url)
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

    def test_empty_file(self):
        """Test analysis of empty file."""
        analyzer = ASTAnalyzer(source_code="")
        assert analyzer.get_functions() == []
        assert analyzer.get_loops() == []
        assert analyzer.get_imports() == []
        assert analyzer.get_calls() == []

    def test_caching_behavior(self):
        """Test that results are cached."""
        analyzer = ASTAnalyzer(source_code="def test(): pass")
        functions1 = analyzer.get_functions()
        functions2 = analyzer.get_functions()
        assert functions1 is functions2
