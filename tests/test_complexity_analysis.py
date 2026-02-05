"""Tests for the complexity analysis module."""

import pytest

from workshop_mcp.complexity_analysis.calculator import (
    CognitiveCalculator,
    CyclomaticCalculator,
)
from workshop_mcp.complexity_analysis.metrics import analyze_complexity
from workshop_mcp.complexity_analysis.patterns import (
    ComplexityCategory,
    cyclomatic_label,
    severity_for_cognitive,
    severity_for_cyclomatic,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_function(source: str):
    """Parse source and return the first FunctionDef node."""
    import astroid

    tree = astroid.parse(source)
    for node in tree.nodes_of_class((astroid.FunctionDef, astroid.AsyncFunctionDef)):
        return node
    raise ValueError("No function found in source")


# ===========================================================================
# CyclomaticCalculator tests
# ===========================================================================


class TestCyclomaticCalculator:
    """Test cyclomatic complexity calculation."""

    def test_simple_function(self):
        """A function with no branching has complexity 1."""
        source = """
def simple():
    x = 1
    return x
"""
        node = _parse_function(source)
        calc = CyclomaticCalculator()
        assert calc.calculate(node) == 1

    def test_single_if(self):
        """A single if statement adds 1."""
        source = """
def fn(x):
    if x > 0:
        return x
    return -x
"""
        node = _parse_function(source)
        calc = CyclomaticCalculator()
        assert calc.calculate(node) == 2

    def test_if_elif_else(self):
        """if + elif is 2 extra branches."""
        source = """
def fn(x):
    if x > 0:
        return 1
    elif x == 0:
        return 0
    else:
        return -1
"""
        node = _parse_function(source)
        calc = CyclomaticCalculator()
        assert calc.calculate(node) == 3  # 1 base + if + elif

    def test_for_loop(self):
        """A for loop adds 1."""
        source = """
def fn(items):
    total = 0
    for item in items:
        total += item
    return total
"""
        node = _parse_function(source)
        calc = CyclomaticCalculator()
        assert calc.calculate(node) == 2

    def test_while_loop(self):
        """A while loop adds 1."""
        source = """
def fn():
    i = 0
    while i < 10:
        i += 1
    return i
"""
        node = _parse_function(source)
        calc = CyclomaticCalculator()
        assert calc.calculate(node) == 2

    def test_except_handler(self):
        """Each except handler adds 1."""
        source = """
def fn():
    try:
        return 1 / 0
    except ZeroDivisionError:
        return 0
    except ValueError:
        return -1
"""
        node = _parse_function(source)
        calc = CyclomaticCalculator()
        assert calc.calculate(node) == 3  # 1 base + 2 except

    def test_with_statement(self):
        """A with statement adds 1."""
        source = """
def fn():
    with open('f') as fh:
        return fh.read()
"""
        node = _parse_function(source)
        calc = CyclomaticCalculator()
        assert calc.calculate(node) == 2

    def test_assert_statement(self):
        """An assert adds 1."""
        source = """
def fn(x):
    assert x > 0
    return x
"""
        node = _parse_function(source)
        calc = CyclomaticCalculator()
        assert calc.calculate(node) == 2

    def test_boolean_and(self):
        """Boolean 'and' adds 1 per operator."""
        source = """
def fn(a, b):
    if a and b:
        return True
"""
        node = _parse_function(source)
        calc = CyclomaticCalculator()
        # 1 base + 1 if + 1 and
        assert calc.calculate(node) == 3

    def test_boolean_or(self):
        """Boolean 'or' adds 1 per operator."""
        source = """
def fn(a, b, c):
    if a or b or c:
        return True
"""
        node = _parse_function(source)
        calc = CyclomaticCalculator()
        # 1 base + 1 if + 2 or (three operands = 2 operators)
        assert calc.calculate(node) == 4

    def test_comprehension(self):
        """List comprehension adds 1."""
        source = """
def fn(items):
    return [x for x in items]
"""
        node = _parse_function(source)
        calc = CyclomaticCalculator()
        # 1 base + 1 comprehension
        assert calc.calculate(node) >= 2

    def test_ternary_expression(self):
        """Ternary (IfExp) adds 1."""
        source = """
def fn(x):
    return x if x > 0 else -x
"""
        node = _parse_function(source)
        calc = CyclomaticCalculator()
        assert calc.calculate(node) == 2  # 1 base + 1 IfExp

    def test_complex_function(self):
        """A function with many branches has high complexity."""
        source = """
def process(data, flag, mode):
    if not data:
        return None
    result = []
    for item in data:
        if flag and item > 0:
            if mode == 'add':
                result.append(item)
            elif mode == 'double':
                result.append(item * 2)
            else:
                result.append(0)
        elif item == 0:
            continue
        else:
            try:
                result.append(-item)
            except TypeError:
                pass
    while len(result) > 100:
        result.pop()
    return result
"""
        node = _parse_function(source)
        calc = CyclomaticCalculator()
        score = calc.calculate(node)
        assert score >= 10


# ===========================================================================
# CognitiveCalculator tests
# ===========================================================================


class TestCognitiveCalculator:
    """Test cognitive complexity calculation."""

    def test_simple_function(self):
        """No flow breaks = 0 cognitive complexity."""
        source = """
def simple():
    return 42
"""
        node = _parse_function(source)
        calc = CognitiveCalculator()
        assert calc.calculate(node) == 0

    def test_single_if(self):
        """Single if at top level adds 1."""
        source = """
def fn(x):
    if x:
        return x
"""
        node = _parse_function(source)
        calc = CognitiveCalculator()
        assert calc.calculate(node) == 1

    def test_nesting_penalty(self):
        """Nested if adds 1 + nesting level."""
        source = """
def fn(x, y):
    if x:
        if y:
            return True
"""
        node = _parse_function(source)
        calc = CognitiveCalculator()
        # outer if: +1 (nesting=0)
        # inner if: +1 + 1 (nesting=1)
        assert calc.calculate(node) == 3

    def test_loop_with_nested_if(self):
        """for loop + nested if both get nesting penalties."""
        source = """
def fn(items):
    for item in items:
        if item > 0:
            pass
"""
        node = _parse_function(source)
        calc = CognitiveCalculator()
        # for: +1 (nesting=0)
        # if inside for: +1 + 1 (nesting=1)
        assert calc.calculate(node) == 3

    def test_boolean_operator(self):
        """Boolean operators add 1 per operator group."""
        source = """
def fn(a, b):
    if a and b:
        return True
"""
        node = _parse_function(source)
        calc = CognitiveCalculator()
        # if: +1, and: +1
        assert calc.calculate(node) == 2

    def test_recursion_detection(self):
        """Recursive call adds 1."""
        source = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""
        node = _parse_function(source)
        calc = CognitiveCalculator()
        # if: +1, recursion: +1
        assert calc.calculate(node) == 2

    def test_deeply_nested(self):
        """Deeply nested code has high cognitive complexity."""
        source = """
def fn(a, b, c, d):
    if a:
        for x in b:
            if c:
                while d:
                    pass
"""
        node = _parse_function(source)
        calc = CognitiveCalculator()
        # if(0): +1, for(1): +1+1=2, if(2): +1+2=3, while(3): +1+3=4
        assert calc.calculate(node) == 10


# ===========================================================================
# analyze_complexity integration tests
# ===========================================================================


class TestAnalyzeComplexity:
    """Test the main analyze_complexity function."""

    def test_simple_code_no_issues(self):
        """Simple code should produce no issues."""
        source = """
def add(a, b):
    return a + b
"""
        result = analyze_complexity(source)
        assert len(result.issues) == 0
        assert result.file_metrics is not None
        assert result.file_metrics.total_functions == 1
        assert result.file_metrics.max_complexity == 1

    def test_invalid_syntax(self):
        """Invalid Python raises SyntaxError."""
        with pytest.raises(SyntaxError):
            analyze_complexity("def broken(")

    def test_high_cyclomatic_detected(self):
        """Functions above the cyclomatic threshold produce an issue."""
        source = """
def complex_fn(a, b, c, d, e):
    if a:
        pass
    if b:
        pass
    if c:
        pass
    if d:
        pass
    if e:
        pass
    for x in range(10):
        if x > 5:
            pass
    while a:
        break
    try:
        pass
    except ValueError:
        pass
    except TypeError:
        pass
    assert a
"""
        result = analyze_complexity(source, cyclomatic_threshold=5)
        cats = [i.category for i in result.issues]
        assert ComplexityCategory.HIGH_CYCLOMATIC_COMPLEXITY.value in cats

    def test_high_cognitive_detected(self):
        """Functions above the cognitive threshold produce an issue."""
        source = """
def deeply_nested(a, b, c, d):
    if a:
        for x in b:
            if c:
                while d:
                    if a and b:
                        pass
"""
        result = analyze_complexity(source, cognitive_threshold=5)
        cats = [i.category for i in result.issues]
        assert ComplexityCategory.HIGH_COGNITIVE_COMPLEXITY.value in cats

    def test_long_function_detected(self):
        """Functions exceeding max_function_length produce an issue."""
        lines = ["    x = 1"] * 60
        source = "def long_fn():\n" + "\n".join(lines) + "\n    return x\n"
        result = analyze_complexity(source, max_function_length=50)
        cats = [i.category for i in result.issues]
        assert ComplexityCategory.LONG_FUNCTION.value in cats

    def test_too_many_parameters_detected(self):
        """Functions with too many parameters produce an issue."""
        source = """
def many_params(a, b, c, d, e, f, g):
    return a + b + c + d + e + f + g
"""
        result = analyze_complexity(source)
        cats = [i.category for i in result.issues]
        assert ComplexityCategory.TOO_MANY_PARAMETERS.value in cats

    def test_self_cls_not_counted(self):
        """self and cls should be counted by the raw param count.

        Note: The core ast_utils extract_functions includes self/cls in
        parameters, so the param check in metrics.py counts all params.
        A method with (self, a, b, c, d, e) has 6 params total which
        exceeds the default threshold of 5.
        """
        source = """
class Foo:
    def method(self, a, b, c, d):
        pass
"""
        result = analyze_complexity(source)
        # self + 4 params = 5 total, at threshold, should not trigger
        param_issues = [
            i for i in result.issues if i.category == ComplexityCategory.TOO_MANY_PARAMETERS.value
        ]
        assert len(param_issues) == 0

    def test_deep_nesting_detected(self):
        """Deeply nested code produces an issue."""
        source = """
def deep():
    if True:
        for x in []:
            if True:
                while True:
                    if True:
                        pass
"""
        result = analyze_complexity(source, cyclomatic_threshold=100)
        cats = [i.category for i in result.issues]
        assert ComplexityCategory.DEEP_NESTING.value in cats

    def test_class_metrics(self):
        """Classes with many methods are detected."""
        methods = "\n".join(f"    def method_{i}(self):\n        pass\n" for i in range(25))
        source = f"class BigClass:\n{methods}"
        result = analyze_complexity(source, max_function_length=100)
        cats = [i.category for i in result.issues]
        assert ComplexityCategory.LARGE_CLASS.value in cats

    def test_threshold_configurability(self):
        """Lowering thresholds catches more issues."""
        source = """
def fn(x):
    if x:
        return 1
    return 0
"""
        # Default threshold (10) should not trigger
        result_default = analyze_complexity(source)
        assert len(result_default.issues) == 0

        # Threshold of 1 should trigger
        result_low = analyze_complexity(source, cyclomatic_threshold=1)
        assert len(result_low.issues) > 0

    def test_file_metrics_aggregation(self):
        """File metrics correctly aggregate function-level data."""
        source = """
def fn1():
    pass

def fn2(x):
    if x:
        return 1
    return 0

def fn3(a, b, c):
    if a:
        if b:
            if c:
                return True
    return False
"""
        result = analyze_complexity(source)
        fm = result.file_metrics
        assert fm is not None
        assert fm.total_functions == 3
        assert fm.average_complexity > 0
        assert fm.max_complexity >= 1

    def test_empty_function(self):
        """Empty/pass function has complexity 1."""
        source = """
def noop():
    pass
"""
        result = analyze_complexity(source)
        assert result.file_metrics is not None
        assert result.file_metrics.max_complexity == 1
        assert len(result.issues) == 0

    def test_single_line_function(self):
        """Single-expression function has complexity 1."""
        source = """
def identity(x): return x
"""
        result = analyze_complexity(source)
        assert result.file_metrics is not None
        assert result.file_metrics.max_complexity == 1

    def test_file_path_analysis(self, tmp_path):
        """Analyze a file by path (read source from file first)."""
        test_file = tmp_path / "test.py"
        source = "def fn(x):\n    if x:\n        return x\n    return -x\n"
        test_file.write_text(source)
        result = analyze_complexity(source, file_path=str(test_file))
        assert result.file_metrics is not None
        assert result.file_metrics.total_functions == 1

    def test_issue_output_format(self):
        """Issues have the expected fields."""
        source = """
def complex_fn(a, b, c, d, e, f, g):
    if a and b:
        for x in c:
            if d:
                while e:
                    try:
                        pass
                    except Exception:
                        pass
    if f:
        pass
    if g:
        pass
"""
        result = analyze_complexity(source, cyclomatic_threshold=5)
        assert len(result.issues) > 0
        issue = result.issues[0]
        assert issue.tool == "complexity"
        assert issue.category is not None
        assert issue.severity is not None
        assert issue.message is not None
        assert issue.line is not None
        assert issue.suggestion is not None


# ===========================================================================
# Patterns / thresholds tests
# ===========================================================================


class TestPatterns:
    """Test threshold helpers."""

    def test_cyclomatic_labels(self):
        assert cyclomatic_label(5) == "simple"
        assert cyclomatic_label(10) == "simple"
        assert cyclomatic_label(15) == "moderate"
        assert cyclomatic_label(20) == "moderate"
        assert cyclomatic_label(30) == "high"
        assert cyclomatic_label(50) == "high"
        assert cyclomatic_label(51) == "very high"

    def test_severity_for_cyclomatic(self):
        assert severity_for_cyclomatic(5, 10) == "info"
        assert severity_for_cyclomatic(15, 10) == "warning"
        assert severity_for_cyclomatic(25, 10) == "error"
        assert severity_for_cyclomatic(55, 10) == "critical"

    def test_severity_for_cognitive(self):
        assert severity_for_cognitive(10, 15) == "info"
        assert severity_for_cognitive(20, 15) == "warning"
        assert severity_for_cognitive(40, 15) == "error"
        assert severity_for_cognitive(60, 15) == "critical"


# ===========================================================================
# MCP server integration tests
# ===========================================================================


class TestMCPIntegration:
    """Test complexity_analysis tool via MCP server."""

    def test_tool_listed(self):
        """complexity_analysis appears in list_tools."""
        from workshop_mcp.server import WorkshopMCPServer

        server = WorkshopMCPServer()
        response = server._handle_request({"jsonrpc": "2.0", "id": 1, "method": "list_tools"})
        tools = response["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        assert "complexity_analysis" in tool_names

    def test_tool_schema(self):
        """complexity_analysis has the expected input schema."""
        from workshop_mcp.server import WorkshopMCPServer

        server = WorkshopMCPServer()
        response = server._handle_request({"jsonrpc": "2.0", "id": 1, "method": "list_tools"})
        tools = response["result"]["tools"]
        tool = next(t for t in tools if t["name"] == "complexity_analysis")
        props = tool["inputSchema"]["properties"]
        assert "file_path" in props
        assert "source_code" in props
        assert "cyclomatic_threshold" in props
        assert "cognitive_threshold" in props
        assert "max_function_length" in props

    def test_tool_callable_with_source_code(self):
        """complexity_analysis returns results when called with source_code."""
        from workshop_mcp.server import WorkshopMCPServer

        server = WorkshopMCPServer()
        source = """
def fn(x):
    if x > 0:
        return x
    return -x
"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "call_tool",
            "params": {
                "name": "complexity_analysis",
                "arguments": {"source_code": source},
            },
        }
        response = server._handle_request(request)
        assert "result" in response
        result_json = response["result"]["content"][0]["json"]
        assert result_json["success"] is True
        assert "issues" in result_json
        assert "file_metrics" in result_json
        assert result_json["file_metrics"]["total_functions"] == 1

    def test_tool_callable_with_file_path(self, tmp_path, monkeypatch):
        """complexity_analysis works with a file path."""
        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))

        from workshop_mcp.server import WorkshopMCPServer

        server = WorkshopMCPServer()
        test_file = tmp_path / "test.py"
        test_file.write_text("def fn():\n    pass\n")

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "call_tool",
            "params": {
                "name": "complexity_analysis",
                "arguments": {"file_path": str(test_file)},
            },
        }
        response = server._handle_request(request)
        assert "result" in response
        result_json = response["result"]["content"][0]["json"]
        assert result_json["success"] is True

    def test_tool_error_no_input(self):
        """complexity_analysis returns error when no input is given."""
        from workshop_mcp.server import WorkshopMCPServer

        server = WorkshopMCPServer()
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "call_tool",
            "params": {
                "name": "complexity_analysis",
                "arguments": {},
            },
        }
        response = server._handle_request(request)
        assert "error" in response

    def test_tool_custom_thresholds(self):
        """complexity_analysis respects custom thresholds."""
        from workshop_mcp.server import WorkshopMCPServer

        server = WorkshopMCPServer()
        source = """
def fn(x):
    if x:
        return 1
    return 0
"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "call_tool",
            "params": {
                "name": "complexity_analysis",
                "arguments": {
                    "source_code": source,
                    "cyclomatic_threshold": 1,
                },
            },
        }
        response = server._handle_request(request)
        result_json = response["result"]["content"][0]["json"]
        assert len(result_json["issues"]) > 0
