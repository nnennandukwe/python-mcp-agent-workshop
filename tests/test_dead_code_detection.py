"""Tests for the dead code detection module."""

import pytest

from workshop_mcp.dead_code_detection.detector import (
    DeadCodeDetector,
    DeadCodeResult,
    detect_dead_code,
)
from workshop_mcp.dead_code_detection.patterns import DeadCodeCategory, Severity


class TestDeadCodeDetectorInitialization:
    """Test detector initialization."""

    def test_init_with_source_code(self):
        """Test initialization with source code string."""
        detector = DeadCodeDetector("x = 1\nprint(x)")
        assert detector.source_code is not None

    def test_init_with_syntax_error(self):
        """Test initialization fails with invalid syntax."""
        with pytest.raises(SyntaxError):
            DeadCodeDetector("def foo(:\n  pass")


class TestUnusedImports:
    """Test unused import detection."""

    def test_unused_import_x(self):
        """Detect 'import os' when os is never used."""
        source = "import os\nx = 1\nprint(x)\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        import_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_IMPORT]
        assert len(import_issues) == 1
        assert import_issues[0].name == "os"
        assert import_issues[0].severity == Severity.INFO

    def test_unused_from_import(self):
        """Detect 'from typing import List, Dict' where Dict is unused."""
        source = "from typing import List, Dict\nx: List[int] = []\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        import_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_IMPORT]
        assert len(import_issues) == 1
        assert import_issues[0].name == "Dict"

    def test_used_import_not_flagged(self):
        """Used imports should not be flagged."""
        source = "import os\nprint(os.path.join('a', 'b'))\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        import_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_IMPORT]
        assert len(import_issues) == 0

    def test_aliased_import_checks_alias(self):
        """Aliased import should check alias, not original name."""
        source = "import numpy as np\nx = np.array([1, 2, 3])\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        import_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_IMPORT]
        assert len(import_issues) == 0

    def test_unused_aliased_import(self):
        """Unused aliased import should be flagged with the alias name."""
        source = "import numpy as np\nx = 1\nprint(x)\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        import_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_IMPORT]
        assert len(import_issues) == 1
        assert import_issues[0].name == "np"

    def test_import_in_all_not_flagged(self):
        """Imports listed in __all__ should not be flagged."""
        source = 'import os\n__all__ = ["os"]\n'
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        import_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_IMPORT]
        assert len(import_issues) == 0

    def test_check_imports_disabled(self):
        """When check_imports=False, no import issues should be reported."""
        source = "import os\nx = 1\nprint(x)\n"
        detector = DeadCodeDetector(source, check_imports=False)
        result = detector.detect_all()
        import_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_IMPORT]
        assert len(import_issues) == 0

    def test_from_import_multiple_names(self):
        """From import with multiple names, some used and some not."""
        source = "from os.path import join, exists\nprint(join('a', 'b'))\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        import_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_IMPORT]
        assert len(import_issues) == 1
        assert import_issues[0].name == "exists"


class TestUnusedVariables:
    """Test unused variable detection."""

    def test_unused_variable(self):
        """Detect variable assigned but never read."""
        source = "x = 42\ny = 10\nprint(y)\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        var_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_VARIABLE]
        assert len(var_issues) == 1
        assert var_issues[0].name == "x"
        assert var_issues[0].severity == Severity.WARNING

    def test_used_variable_not_flagged(self):
        """Used variables should not be flagged."""
        source = "x = 42\nprint(x)\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        var_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_VARIABLE]
        assert len(var_issues) == 0

    def test_underscore_prefixed_variable_not_flagged(self):
        """Underscore-prefixed variables should be skipped."""
        source = "_private = 42\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        var_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_VARIABLE]
        assert len(var_issues) == 0

    def test_dunder_variable_not_flagged(self):
        """Dunder variables like __version__ should be skipped."""
        source = '__version__ = "1.0"\n'
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        var_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_VARIABLE]
        assert len(var_issues) == 0

    def test_check_variables_disabled(self):
        """When check_variables=False, no variable issues should be reported."""
        source = "x = 42\ny = 10\nprint(y)\n"
        detector = DeadCodeDetector(source, check_variables=False)
        result = detector.detect_all()
        var_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_VARIABLE]
        assert len(var_issues) == 0

    def test_augmented_assignment_counts_as_reference(self):
        """x += 1 should count x as referenced."""
        source = "x = 0\nx += 1\nprint(x)\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        var_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_VARIABLE]
        assert len(var_issues) == 0


class TestUnusedFunctions:
    """Test unused function detection."""

    def test_unused_function(self):
        """Detect function defined but never called."""
        source = "def foo():\n    return 1\n\ndef bar():\n    return 2\n\nbar()\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        func_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_FUNCTION]
        assert len(func_issues) == 1
        assert func_issues[0].name == "foo"

    def test_called_function_not_flagged(self):
        """Called functions should not be flagged."""
        source = "def foo():\n    return 1\n\nfoo()\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        func_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_FUNCTION]
        assert len(func_issues) == 0

    def test_test_function_not_flagged(self):
        """Functions prefixed with test_ should not be flagged."""
        source = "def test_something():\n    assert True\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        func_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_FUNCTION]
        assert len(func_issues) == 0

    def test_dunder_method_not_flagged(self):
        """Dunder methods like __init__ should not be flagged."""
        source = "class Foo:\n    def __init__(self):\n        pass\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        func_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_FUNCTION]
        func_names = [i.name for i in func_issues]
        assert "__init__" not in func_names

    def test_decorated_property_not_flagged(self):
        """Functions with @property decorator should not be flagged."""
        source = "class Foo:\n    @property\n    def bar(self):\n        return 1\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        func_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_FUNCTION]
        func_names = [i.name for i in func_issues]
        assert "bar" not in func_names

    def test_function_in_all_not_flagged(self):
        """Functions in __all__ should not be flagged."""
        source = 'def foo():\n    return 1\n\n__all__ = ["foo"]\n'
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        func_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_FUNCTION]
        assert len(func_issues) == 0

    def test_public_function_lower_confidence(self):
        """Public unused functions should have INFO severity (lower confidence)."""
        source = "def public_func():\n    return 1\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        func_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_FUNCTION]
        assert len(func_issues) == 1
        assert func_issues[0].severity == Severity.INFO

    def test_private_function_higher_confidence(self):
        """Private unused functions should have WARNING severity (higher confidence)."""
        source = "def _private_func():\n    return 1\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        func_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_FUNCTION]
        assert len(func_issues) == 1
        assert func_issues[0].severity == Severity.WARNING

    def test_check_functions_disabled(self):
        """When check_functions=False, no function issues should be reported."""
        source = "def foo():\n    return 1\n"
        detector = DeadCodeDetector(source, check_functions=False)
        result = detector.detect_all()
        func_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_FUNCTION]
        assert len(func_issues) == 0


class TestUnusedParameters:
    """Test unused parameter detection."""

    def test_unused_parameter(self):
        """Detect parameter never used in function body."""
        source = "def foo(x, y):\n    return x\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        param_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_PARAMETER]
        assert len(param_issues) == 1
        assert param_issues[0].name == "y"
        assert param_issues[0].category == DeadCodeCategory.UNUSED_PARAMETER

    def test_used_parameter_not_flagged(self):
        """Used parameters should not be flagged."""
        source = "def foo(x, y):\n    return x + y\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        param_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_PARAMETER]
        assert len(param_issues) == 0

    def test_self_not_flagged(self):
        """self parameter should never be flagged."""
        source = "class Foo:\n    def bar(self):\n        return 1\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        param_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_PARAMETER]
        assert len(param_issues) == 0

    def test_cls_not_flagged(self):
        """cls parameter should never be flagged."""
        source = "class Foo:\n    @classmethod\n    def bar(cls):\n        return 1\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        param_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_PARAMETER]
        assert len(param_issues) == 0

    def test_stub_function_not_flagged(self):
        """Parameters in stub functions (pass) should not be flagged."""
        source = "def foo(x, y):\n    pass\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        param_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_PARAMETER]
        assert len(param_issues) == 0

    def test_ellipsis_stub_not_flagged(self):
        """Parameters in functions with only Ellipsis should not be flagged."""
        source = "def foo(x, y):\n    ...\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        param_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_PARAMETER]
        assert len(param_issues) == 0

    def test_docstring_plus_pass_stub_not_flagged(self):
        """Parameters in functions with docstring + pass should not be flagged."""
        source = 'def foo(x, y):\n    """Docs."""\n    pass\n'
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        param_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_PARAMETER]
        assert len(param_issues) == 0


class TestUnreachableCode:
    """Test unreachable code detection."""

    def test_code_after_return(self):
        """Detect code after return statement."""
        source = "def foo():\n    return 1\n    x = 2\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        unreach = [i for i in result.issues if i.category == DeadCodeCategory.UNREACHABLE_CODE]
        assert len(unreach) == 1
        assert "return" in unreach[0].message

    def test_code_after_raise(self):
        """Detect code after raise statement."""
        source = "def foo():\n    raise ValueError('err')\n    x = 2\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        unreach = [i for i in result.issues if i.category == DeadCodeCategory.UNREACHABLE_CODE]
        assert len(unreach) == 1
        assert "raise" in unreach[0].message

    def test_code_after_break(self):
        """Detect code after break statement."""
        source = "for i in range(10):\n    break\n    x = 2\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        unreach = [i for i in result.issues if i.category == DeadCodeCategory.UNREACHABLE_CODE]
        assert len(unreach) == 1
        assert "break" in unreach[0].message

    def test_code_after_continue(self):
        """Detect code after continue statement."""
        source = "for i in range(10):\n    continue\n    x = 2\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        unreach = [i for i in result.issues if i.category == DeadCodeCategory.UNREACHABLE_CODE]
        assert len(unreach) == 1
        assert "continue" in unreach[0].message

    def test_no_unreachable_code(self):
        """No unreachable code should produce no issues."""
        source = "def foo():\n    x = 1\n    return x\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        unreach = [i for i in result.issues if i.category == DeadCodeCategory.UNREACHABLE_CODE]
        assert len(unreach) == 0


class TestRedundantConditions:
    """Test redundant condition detection."""

    def test_if_true(self):
        """Detect 'if True:' as always-true condition."""
        source = "if True:\n    x = 1\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        redundant = [i for i in result.issues if i.category == DeadCodeCategory.REDUNDANT_CONDITION]
        assert len(redundant) == 1
        assert "True" in redundant[0].message

    def test_if_false(self):
        """Detect 'if False:' as never-executed block."""
        source = "if False:\n    x = 1\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        redundant = [i for i in result.issues if i.category == DeadCodeCategory.REDUNDANT_CONDITION]
        assert len(redundant) == 1
        assert "False" in redundant[0].message

    def test_while_false(self):
        """Detect 'while False:' as never-executed loop."""
        source = "while False:\n    x = 1\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        redundant = [i for i in result.issues if i.category == DeadCodeCategory.REDUNDANT_CONDITION]
        assert len(redundant) == 1
        assert "False" in redundant[0].message

    def test_normal_if_not_flagged(self):
        """Normal if conditions should not be flagged."""
        source = "x = 1\nif x > 0:\n    print(x)\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        redundant = [i for i in result.issues if i.category == DeadCodeCategory.REDUNDANT_CONDITION]
        assert len(redundant) == 0


class TestIgnorePatterns:
    """Test ignore_patterns parameter."""

    def test_ignore_patterns_imports(self):
        """Ignore patterns should skip matching imports."""
        source = "import os\nimport sys\nx = 1\nprint(x)\n"
        detector = DeadCodeDetector(source, ignore_patterns=["os"])
        result = detector.detect_all()
        import_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_IMPORT]
        names = [i.name for i in import_issues]
        assert "os" not in names
        assert "sys" in names

    def test_ignore_patterns_functions(self):
        """Ignore patterns should skip matching functions."""
        source = "def handler_foo():\n    return 1\n\ndef helper_bar():\n    return 2\n"
        detector = DeadCodeDetector(source, ignore_patterns=["handler_foo"])
        result = detector.detect_all()
        func_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_FUNCTION]
        names = [i.name for i in func_issues]
        assert "handler_foo" not in names
        assert "helper_bar" in names

    def test_ignore_patterns_variables(self):
        """Ignore patterns should skip matching variables."""
        source = "CONSTANT = 42\ntemp = 10\nprint(temp)\n"
        detector = DeadCodeDetector(source, ignore_patterns=["CONSTANT"])
        result = detector.detect_all()
        var_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_VARIABLE]
        names = [i.name for i in var_issues]
        assert "CONSTANT" not in names


class TestDetectAll:
    """Test the combined detect_all method."""

    def test_empty_module(self):
        """Empty module should produce no issues."""
        detector = DeadCodeDetector("")
        result = detector.detect_all()
        assert len(result.issues) == 0

    def test_all_used_module(self):
        """Module with all symbols used should produce no issues."""
        source = "import os\npath = os.path.join('a', 'b')\nprint(path)\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        assert len(result.issues) == 0

    def test_multiple_issue_types(self):
        """Test detecting multiple types of issues at once."""
        source = (
            "import os\n"
            "import sys\n"
            "def unused_func():\n"
            "    return 1\n"
            "dead_var = 42\n"
            "print(sys.argv)\n"
        )
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        categories = {i.category for i in result.issues}
        assert DeadCodeCategory.UNUSED_IMPORT in categories
        assert DeadCodeCategory.UNUSED_FUNCTION in categories
        assert DeadCodeCategory.UNUSED_VARIABLE in categories

    def test_result_has_summary(self):
        """detect_all should return DeadCodeResult with summary."""
        source = "import os\nimport sys\ndead_var = 42\nprint(sys.argv)\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        assert isinstance(result, DeadCodeResult)
        assert result.summary.unused_imports == 1
        assert result.summary.unused_variables == 1

    def test_empty_summary(self):
        """Summary of clean code should have all zeros."""
        source = "import os\nprint(os.getcwd())\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        assert result.summary.unused_imports == 0
        assert result.summary.unused_variables == 0
        assert result.summary.unused_functions == 0
        assert result.summary.unreachable_blocks == 0
        assert result.summary.redundant_conditions == 0


class TestConvenienceFunction:
    """Test the detect_dead_code convenience function."""

    def test_returns_dead_code_result(self):
        """Convenience function should return DeadCodeResult."""
        result = detect_dead_code("import os\nx = 1\nprint(x)\n")
        assert isinstance(result, DeadCodeResult)
        assert len(result.issues) == 1
        assert result.issues[0].category == DeadCodeCategory.UNUSED_IMPORT

    def test_convenience_function_with_options(self):
        """Convenience function should accept optional parameters."""
        result = detect_dead_code("import os\nx = 1\nprint(x)\n", check_imports=False)
        import_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_IMPORT]
        assert len(import_issues) == 0


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_decorated_with_fixture(self):
        """Functions decorated with @pytest.fixture should not be flagged."""
        source = "import pytest\n\n@pytest.fixture\ndef my_fixture():\n    return 42\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        func_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_FUNCTION]
        func_names = [i.name for i in func_issues]
        assert "my_fixture" not in func_names

    def test_decorated_with_staticmethod(self):
        """Functions decorated with @staticmethod should not be flagged."""
        source = "class Foo:\n    @staticmethod\n    def bar():\n        return 1\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        func_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_FUNCTION]
        func_names = [i.name for i in func_issues]
        assert "bar" not in func_names

    def test_class_not_flagged_as_function(self):
        """Classes should not be reported as unused functions."""
        source = "class Foo:\n    pass\n"
        detector = DeadCodeDetector(source)
        result = detector.detect_all()
        func_issues = [i for i in result.issues if i.category == DeadCodeCategory.UNUSED_FUNCTION]
        names = [i.name for i in func_issues]
        assert "Foo" not in names


class TestMCPIntegration:
    """Test dead_code_detection tool via MCP server."""

    def test_tool_listed(self):
        """dead_code_detection appears in list_tools."""
        from workshop_mcp.server import WorkshopMCPServer

        server = WorkshopMCPServer()
        response = server._handle_request({"jsonrpc": "2.0", "id": 1, "method": "list_tools"})
        tools = response["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        assert "dead_code_detection" in tool_names

    def test_tool_schema(self):
        """dead_code_detection has the expected input schema."""
        from workshop_mcp.server import WorkshopMCPServer

        server = WorkshopMCPServer()
        response = server._handle_request({"jsonrpc": "2.0", "id": 1, "method": "list_tools"})
        tools = response["result"]["tools"]
        tool = next(t for t in tools if t["name"] == "dead_code_detection")
        props = tool["inputSchema"]["properties"]
        assert "file_path" in props
        assert "source_code" in props
        assert "check_imports" in props
        assert "check_variables" in props
        assert "check_functions" in props
        assert "ignore_patterns" in props

    def test_tool_callable_with_source_code(self):
        """dead_code_detection returns results when called with source_code."""
        from workshop_mcp.server import WorkshopMCPServer

        server = WorkshopMCPServer()
        source = "import os\nx = 1\nprint(x)\n"
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "call_tool",
            "params": {
                "name": "dead_code_detection",
                "arguments": {"source_code": source},
            },
        }
        response = server._handle_request(request)
        assert "result" in response
        result_json = response["result"]["content"][0]["json"]
        assert result_json["success"] is True
        assert "issues" in result_json
        assert "summary" in result_json
        assert len(result_json["issues"]) == 1
        assert result_json["issues"][0]["category"] == "unused_import"
        assert result_json["summary"]["unused_imports"] == 1

    def test_tool_callable_with_file_path(self, tmp_path, monkeypatch):
        """dead_code_detection works with a file path."""
        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))

        from workshop_mcp.server import WorkshopMCPServer

        server = WorkshopMCPServer()
        test_file = tmp_path / "test.py"
        test_file.write_text("import os\nprint(os.getcwd())\n")

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "call_tool",
            "params": {
                "name": "dead_code_detection",
                "arguments": {"file_path": str(test_file)},
            },
        }
        response = server._handle_request(request)
        assert "result" in response
        result_json = response["result"]["content"][0]["json"]
        assert result_json["success"] is True

    def test_tool_error_no_input(self):
        """dead_code_detection returns error when no input is given."""
        from workshop_mcp.server import WorkshopMCPServer

        server = WorkshopMCPServer()
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "call_tool",
            "params": {
                "name": "dead_code_detection",
                "arguments": {},
            },
        }
        response = server._handle_request(request)
        assert "error" in response

    def test_tool_error_syntax(self):
        """dead_code_detection returns error for invalid syntax."""
        from workshop_mcp.server import WorkshopMCPServer

        server = WorkshopMCPServer()
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "call_tool",
            "params": {
                "name": "dead_code_detection",
                "arguments": {"source_code": "def broken(:"},
            },
        }
        response = server._handle_request(request)
        assert "error" in response

    def test_tool_with_check_options(self):
        """dead_code_detection respects check_imports=False."""
        from workshop_mcp.server import WorkshopMCPServer

        server = WorkshopMCPServer()
        source = "import os\nx = 1\nprint(x)\n"
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "call_tool",
            "params": {
                "name": "dead_code_detection",
                "arguments": {
                    "source_code": source,
                    "check_imports": False,
                },
            },
        }
        response = server._handle_request(request)
        result_json = response["result"]["content"][0]["json"]
        assert result_json["summary"]["unused_imports"] == 0

    def test_tool_error_both_inputs(self):
        """dead_code_detection returns error when both file_path and source_code are given."""
        from workshop_mcp.server import WorkshopMCPServer

        server = WorkshopMCPServer()
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "call_tool",
            "params": {
                "name": "dead_code_detection",
                "arguments": {"file_path": "/tmp/x.py", "source_code": "x = 1"},
            },
        }
        response = server._handle_request(request)
        assert "error" in response

    def test_tool_error_invalid_ignore_patterns(self):
        """dead_code_detection returns error for non-list ignore_patterns."""
        from workshop_mcp.server import WorkshopMCPServer

        server = WorkshopMCPServer()
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "call_tool",
            "params": {
                "name": "dead_code_detection",
                "arguments": {"source_code": "x = 1", "ignore_patterns": "not_a_list"},
            },
        }
        response = server._handle_request(request)
        assert "error" in response

    def test_tool_error_file_path_not_string(self):
        """dead_code_detection returns error when file_path is not a string."""
        from workshop_mcp.server import WorkshopMCPServer

        server = WorkshopMCPServer()
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "call_tool",
            "params": {
                "name": "dead_code_detection",
                "arguments": {"file_path": 123},
            },
        }
        response = server._handle_request(request)
        assert "error" in response
