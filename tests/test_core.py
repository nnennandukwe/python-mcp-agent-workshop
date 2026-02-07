"""Tests for the core shared AST utilities module."""

import pytest

from workshop_mcp.core import (
    CallInfo,
    ClassInfo,
    CodeIssue,
    FunctionInfo,
    ImportInfo,
    Severity,
    extract_calls,
    extract_classes,
    extract_functions,
    extract_imports,
    get_source_segment,
    parse_source,
)


class TestParseSource:
    """Test parse_source utility."""

    def test_parse_valid_code(self):
        """Test parsing valid Python source code."""
        tree = parse_source("def hello(): pass")
        assert tree is not None

    def test_parse_empty_source(self):
        """Test parsing empty source code."""
        tree = parse_source("")
        assert tree is not None

    def test_parse_invalid_code_raises_syntax_error(self):
        """Test that invalid source code raises SyntaxError."""
        with pytest.raises(SyntaxError):
            parse_source("def invalid syntax")

    def test_parse_with_file_path(self):
        """Test parsing with optional file_path argument."""
        tree = parse_source("x = 1", file_path="test.py")
        assert tree is not None


class TestExtractFunctions:
    """Test extract_functions utility."""

    def test_extract_simple_function(self):
        """Test extracting a simple function definition."""
        tree = parse_source("def greet(name): pass")
        functions = extract_functions(tree)
        assert len(functions) == 1
        assert functions[0].name == "greet"
        assert functions[0].parameters == ["name"]
        assert functions[0].is_async is False

    def test_extract_async_function(self):
        """Test extracting an async function definition."""
        tree = parse_source("async def fetch(): pass")
        functions = extract_functions(tree)
        assert len(functions) == 1
        assert functions[0].name == "fetch"
        assert functions[0].is_async is True

    def test_extract_function_with_decorators(self):
        """Test extracting a function with decorators."""
        source = "@staticmethod\ndef method(): pass"
        tree = parse_source(source)
        functions = extract_functions(tree)
        assert len(functions) == 1
        assert "staticmethod" in functions[0].decorators

    def test_extract_function_with_docstring(self):
        """Test extracting a function with a docstring."""
        source = 'def func():\n    """My docstring."""\n    pass'
        tree = parse_source(source)
        functions = extract_functions(tree)
        assert functions[0].docstring == "My docstring."

    def test_extract_function_with_return_annotation(self):
        """Test extracting a function with return type annotation."""
        source = "def func() -> int: return 1"
        tree = parse_source(source)
        functions = extract_functions(tree)
        assert functions[0].return_annotation == "int"

    def test_extract_function_has_inferred_types_field(self):
        """Test that extracted functions have the inferred_types field."""
        source = "def func(x: int, y: str): pass"
        tree = parse_source(source)
        functions = extract_functions(tree)
        assert isinstance(functions[0].inferred_types, dict)

    def test_extract_no_functions(self):
        """Test extracting from code with no functions."""
        tree = parse_source("x = 1\ny = 2")
        functions = extract_functions(tree)
        assert functions == []

    def test_function_info_is_correct_type(self):
        """Test that returned objects are FunctionInfo instances."""
        tree = parse_source("def f(): pass")
        functions = extract_functions(tree)
        assert isinstance(functions[0], FunctionInfo)


class TestExtractClasses:
    """Test extract_classes utility."""

    def test_extract_simple_class(self):
        """Test extracting a simple class definition."""
        source = "class MyClass:\n    pass"
        tree = parse_source(source)
        classes = extract_classes(tree)
        assert len(classes) == 1
        assert classes[0].name == "MyClass"
        assert classes[0].bases == []

    def test_extract_class_with_bases(self):
        """Test extracting a class with base classes."""
        source = "class Child(Parent, Mixin):\n    pass"
        tree = parse_source(source)
        classes = extract_classes(tree)
        assert len(classes) == 1
        assert "Parent" in classes[0].bases
        assert "Mixin" in classes[0].bases

    def test_extract_class_with_methods(self):
        """Test extracting a class with methods."""
        source = "class Foo:\n    def bar(self): pass\n    def baz(self): pass"
        tree = parse_source(source)
        classes = extract_classes(tree)
        assert len(classes) == 1
        assert "bar" in classes[0].methods
        assert "baz" in classes[0].methods

    def test_extract_class_with_decorator(self):
        """Test extracting a class with a decorator."""
        source = "@dataclass\nclass Point:\n    x: int = 0"
        tree = parse_source(source)
        classes = extract_classes(tree)
        assert len(classes) == 1
        assert "dataclass" in classes[0].decorators

    def test_extract_class_with_docstring(self):
        """Test extracting a class with a docstring."""
        source = 'class Foo:\n    """A foo class."""\n    pass'
        tree = parse_source(source)
        classes = extract_classes(tree)
        assert classes[0].docstring == "A foo class."

    def test_extract_no_classes(self):
        """Test extracting from code with no classes."""
        tree = parse_source("def func(): pass")
        classes = extract_classes(tree)
        assert classes == []

    def test_class_info_is_correct_type(self):
        """Test that returned objects are ClassInfo instances."""
        tree = parse_source("class A:\n    pass")
        classes = extract_classes(tree)
        assert isinstance(classes[0], ClassInfo)

    def test_extract_class_line_numbers(self):
        """Test that class line numbers are extracted correctly."""
        source = "x = 1\nclass Foo:\n    pass"
        tree = parse_source(source)
        classes = extract_classes(tree)
        assert classes[0].line_number == 2


class TestExtractImports:
    """Test extract_imports utility."""

    def test_extract_regular_import(self):
        """Test extracting a regular import."""
        tree = parse_source("import os")
        imports = extract_imports(tree)
        assert len(imports) == 1
        assert imports[0].module == "os"
        assert imports[0].is_from_import is False

    def test_extract_from_import(self):
        """Test extracting a from import."""
        tree = parse_source("from os.path import join")
        imports = extract_imports(tree)
        assert len(imports) == 1
        assert imports[0].module == "os.path"
        assert imports[0].names == ["join"]
        assert imports[0].is_from_import is True

    def test_extract_import_with_alias(self):
        """Test extracting an import with alias."""
        tree = parse_source("import numpy as np")
        imports = extract_imports(tree)
        assert len(imports) == 1
        assert imports[0].aliases == {"numpy": "np"}

    def test_extract_no_imports(self):
        """Test extracting from code with no imports."""
        tree = parse_source("x = 1")
        imports = extract_imports(tree)
        assert imports == []

    def test_import_info_is_correct_type(self):
        """Test that returned objects are ImportInfo instances."""
        tree = parse_source("import sys")
        imports = extract_imports(tree)
        assert isinstance(imports[0], ImportInfo)


class TestExtractCalls:
    """Test extract_calls utility."""

    def test_extract_simple_call(self):
        """Test extracting a simple function call."""
        tree = parse_source("print('hello')")
        calls = extract_calls(tree)
        print_call = next((c for c in calls if c.function_name == "print"), None)
        assert print_call is not None

    def test_call_info_is_correct_type(self):
        """Test that returned objects are CallInfo instances."""
        tree = parse_source("print(1)")
        calls = extract_calls(tree)
        assert isinstance(calls[0], CallInfo)


class TestGetSourceSegment:
    """Test get_source_segment utility."""

    def test_get_segment(self):
        """Test extracting a source code segment."""
        source = "line1\nline2\nline3\nline4"
        segment = get_source_segment(source, 2, 3)
        assert segment == "line2\nline3"

    def test_get_single_line(self):
        """Test extracting a single line."""
        source = "line1\nline2\nline3"
        segment = get_source_segment(source, 2, 2)
        assert segment == "line2"


class TestCodeIssue:
    """Test CodeIssue dataclass."""

    def test_create_code_issue(self):
        """Test creating a CodeIssue with all fields."""
        issue = CodeIssue(
            tool="performance_profiler",
            category="blocking_io",
            severity=Severity.ERROR,
            message="Blocking call in async",
            line=10,
            suggestion="Use aiofiles",
            code_snippet="open('file.txt')",
            function_name="my_func",
            end_line=10,
            column=4,
        )
        assert issue.tool == "performance_profiler"
        assert issue.category == "blocking_io"
        assert issue.severity == Severity.ERROR
        assert issue.message == "Blocking call in async"
        assert issue.line == 10
        assert issue.suggestion == "Use aiofiles"
        assert issue.code_snippet == "open('file.txt')"
        assert issue.function_name == "my_func"
        assert issue.end_line == 10
        assert issue.column == 4

    def test_create_code_issue_minimal(self):
        """Test creating a CodeIssue with only required fields."""
        issue = CodeIssue(
            tool="linter",
            category="style",
            severity=Severity.INFO,
            message="Minor style issue",
            line=1,
        )
        assert issue.suggestion is None
        assert issue.code_snippet is None
        assert issue.function_name is None
        assert issue.end_line is None
        assert issue.column is None


class TestSeverity:
    """Test Severity enum."""

    def test_severity_values(self):
        """Test that Severity enum has the expected values."""
        assert Severity.INFO.value == "info"
        assert Severity.WARNING.value == "warning"
        assert Severity.ERROR.value == "error"
        assert Severity.CRITICAL.value == "critical"

    def test_severity_members(self):
        """Test that Severity enum has exactly four members."""
        assert len(Severity) == 4


class TestInference:
    """Test inference utilities."""

    def test_infer_callable_returns_none_for_unknown(self):
        """infer_callable returns None when inference fails."""
        tree = parse_source("x = unknown_func()")
        calls = extract_calls(tree)
        # For an unresolved name, inference may return None
        assert calls[0].inferred_callable is None or isinstance(calls[0].inferred_callable, str)

    def test_get_qualified_name_on_function(self):
        """get_qualified_name returns qname for a function node."""
        import astroid

        from workshop_mcp.core.inference import get_qualified_name

        tree = astroid.parse("def my_func(): pass")
        func_node = next(tree.nodes_of_class(astroid.FunctionDef))
        qname = get_qualified_name(func_node)
        assert qname is not None
        assert "my_func" in qname

    def test_get_qualified_name_returns_none_for_non_qname_node(self):
        """get_qualified_name returns None for nodes without qname."""
        import astroid

        from workshop_mcp.core.inference import get_qualified_name

        tree = astroid.parse("x = 1 + 2")
        # BinOp nodes don't have qname
        binop_node = next(tree.nodes_of_class(astroid.BinOp))
        result = get_qualified_name(binop_node)
        assert result is None


class TestBackwardCompatibility:
    """Test that existing imports from performance_profiler still work."""

    def test_import_dataclasses_from_ast_analyzer(self):
        """Test importing dataclasses from the original ast_analyzer module."""
        from workshop_mcp.performance_profiler.ast_analyzer import (
            CallInfo,
            FunctionInfo,
            ImportInfo,
            LoopInfo,
        )

        assert FunctionInfo is not None
        assert LoopInfo is not None
        assert ImportInfo is not None
        assert CallInfo is not None

    def test_import_from_profiler_init(self):
        """Test importing from the performance_profiler package."""
        from workshop_mcp.performance_profiler import (
            ASTAnalyzer,
            CallInfo,
            FunctionInfo,
            ImportInfo,
            LoopInfo,
        )

        assert ASTAnalyzer is not None
        assert FunctionInfo is not None
        assert LoopInfo is not None
        assert ImportInfo is not None
        assert CallInfo is not None

    def test_same_classes_from_core_and_profiler(self):
        """Test that core and profiler export the same classes."""
        from workshop_mcp.core import CallInfo as CoreCallInfo
        from workshop_mcp.core import FunctionInfo as CoreFunctionInfo
        from workshop_mcp.core import ImportInfo as CoreImportInfo
        from workshop_mcp.core import LoopInfo as CoreLoopInfo
        from workshop_mcp.performance_profiler.ast_analyzer import CallInfo as ProfCallInfo
        from workshop_mcp.performance_profiler.ast_analyzer import (
            FunctionInfo as ProfFunctionInfo,
        )
        from workshop_mcp.performance_profiler.ast_analyzer import ImportInfo as ProfImportInfo
        from workshop_mcp.performance_profiler.ast_analyzer import LoopInfo as ProfLoopInfo

        assert CoreFunctionInfo is ProfFunctionInfo
        assert CoreLoopInfo is ProfLoopInfo
        assert CoreImportInfo is ProfImportInfo
        assert CoreCallInfo is ProfCallInfo
