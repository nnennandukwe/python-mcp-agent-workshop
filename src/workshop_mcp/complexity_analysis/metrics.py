"""Function and class metric collectors for complexity analysis."""

from dataclasses import dataclass, field

import astroid

from ..core.ast_utils import extract_classes, extract_functions, parse_source
from .calculator import CognitiveCalculator, CyclomaticCalculator
from .patterns import (
    DEFAULT_COGNITIVE_THRESHOLD,
    DEFAULT_CYCLOMATIC_THRESHOLD,
    DEFAULT_MAX_CLASS_METHODS,
    DEFAULT_MAX_FUNCTION_LENGTH,
    DEFAULT_MAX_INHERITANCE_DEPTH,
    DEFAULT_MAX_NESTING_DEPTH,
    DEFAULT_MAX_PARAMETERS,
    ComplexityCategory,
    severity_for_cognitive,
    severity_for_cyclomatic,
)


@dataclass
class FunctionMetrics:
    """Aggregated metrics for a single function."""

    name: str
    line: int
    end_line: int
    cyclomatic: int
    cognitive: int
    length: int
    params: int
    nesting_depth: int


@dataclass
class ClassMetrics:
    """Aggregated metrics for a single class."""

    name: str
    line: int
    method_count: int
    inheritance_depth: int


@dataclass
class FileMetrics:
    """File-level summary statistics."""

    total_functions: int
    average_complexity: float
    max_complexity: int
    complex_functions: int  # functions exceeding cyclomatic threshold


@dataclass
class ComplexityIssue:
    """A complexity issue reported by the analyzer."""

    tool: str
    category: str
    severity: str
    message: str
    line: int
    function: str | None = None
    metrics: dict | None = None
    suggestion: str | None = None


@dataclass
class ComplexityResult:
    """Full result from complexity analysis."""

    issues: list[ComplexityIssue] = field(default_factory=list)
    file_metrics: FileMetrics | None = None
    function_metrics: list[FunctionMetrics] = field(default_factory=list)
    class_metrics: list[ClassMetrics] = field(default_factory=list)


def analyze_complexity(
    source_code: str,
    *,
    file_path: str | None = None,
    cyclomatic_threshold: int = DEFAULT_CYCLOMATIC_THRESHOLD,
    cognitive_threshold: int = DEFAULT_COGNITIVE_THRESHOLD,
    max_function_length: int = DEFAULT_MAX_FUNCTION_LENGTH,
) -> ComplexityResult:
    """Analyze complexity metrics for Python source code.

    Args:
        source_code: Python source code to analyze.
        file_path: Optional file path for context.
        cyclomatic_threshold: Threshold for cyclomatic complexity warnings.
        cognitive_threshold: Threshold for cognitive complexity warnings.
        max_function_length: Maximum function length before warning.

    Returns:
        ComplexityResult with issues, function metrics, and file-level summary.

    Raises:
        SyntaxError: If source code cannot be parsed.
    """
    tree = parse_source(source_code, file_path)
    result = ComplexityResult()

    cyclo_calc = CyclomaticCalculator()
    cog_calc = CognitiveCalculator()

    func_infos = extract_functions(tree)
    func_nodes = list(tree.nodes_of_class((astroid.FunctionDef, astroid.AsyncFunctionDef)))

    # Build a map from (name, line) to AST node for metric calculation
    node_map: dict[tuple[str, int], astroid.FunctionDef | astroid.AsyncFunctionDef] = {}
    for node in func_nodes:
        node_map[(node.name, node.lineno)] = node

    cyclomatic_scores: list[int] = []

    for func_info in func_infos:
        node = node_map.get((func_info.name, func_info.line_number))
        if node is None:
            continue

        cyclomatic = cyclo_calc.calculate(node)
        cognitive = cog_calc.calculate(node)
        length = func_info.end_line_number - func_info.line_number + 1
        params = len(func_info.parameters)
        nesting = _max_nesting_depth(node)

        fm = FunctionMetrics(
            name=func_info.name,
            line=func_info.line_number,
            end_line=func_info.end_line_number,
            cyclomatic=cyclomatic,
            cognitive=cognitive,
            length=length,
            params=params,
            nesting_depth=nesting,
        )
        result.function_metrics.append(fm)
        cyclomatic_scores.append(cyclomatic)

        metrics_dict = {
            "cyclomatic": cyclomatic,
            "cognitive": cognitive,
            "lines": length,
            "params": params,
            "nesting_depth": nesting,
        }

        # Check cyclomatic threshold
        if cyclomatic > cyclomatic_threshold:
            sev = severity_for_cyclomatic(cyclomatic, cyclomatic_threshold)
            result.issues.append(
                ComplexityIssue(
                    tool="complexity",
                    category=ComplexityCategory.HIGH_CYCLOMATIC_COMPLEXITY.value,
                    severity=sev,
                    message=(
                        f"Function '{func_info.name}' has cyclomatic complexity "
                        f"of {cyclomatic} (threshold: {cyclomatic_threshold})"
                    ),
                    line=func_info.line_number,
                    function=func_info.name,
                    metrics=metrics_dict,
                    suggestion="Consider breaking this function into smaller, focused functions",
                )
            )

        # Check cognitive threshold
        if cognitive > cognitive_threshold:
            sev = severity_for_cognitive(cognitive, cognitive_threshold)
            result.issues.append(
                ComplexityIssue(
                    tool="complexity",
                    category=ComplexityCategory.HIGH_COGNITIVE_COMPLEXITY.value,
                    severity=sev,
                    message=(
                        f"Function '{func_info.name}' has cognitive complexity "
                        f"of {cognitive} (threshold: {cognitive_threshold})"
                    ),
                    line=func_info.line_number,
                    function=func_info.name,
                    metrics=metrics_dict,
                    suggestion="Reduce nesting and simplify conditional logic",
                )
            )

        # Check function length
        if length > max_function_length:
            result.issues.append(
                ComplexityIssue(
                    tool="complexity",
                    category=ComplexityCategory.LONG_FUNCTION.value,
                    severity="warning",
                    message=(
                        f"Function '{func_info.name}' is {length} lines long "
                        f"(threshold: {max_function_length})"
                    ),
                    line=func_info.line_number,
                    function=func_info.name,
                    metrics=metrics_dict,
                    suggestion="Extract logic into helper functions",
                )
            )

        # Check parameter count
        if params > DEFAULT_MAX_PARAMETERS:
            result.issues.append(
                ComplexityIssue(
                    tool="complexity",
                    category=ComplexityCategory.TOO_MANY_PARAMETERS.value,
                    severity="warning",
                    message=(
                        f"Function '{func_info.name}' has {params} parameters "
                        f"(threshold: {DEFAULT_MAX_PARAMETERS})"
                    ),
                    line=func_info.line_number,
                    function=func_info.name,
                    metrics=metrics_dict,
                    suggestion="Group related parameters into a dataclass or dict",
                )
            )

        # Check nesting depth
        if nesting > DEFAULT_MAX_NESTING_DEPTH:
            result.issues.append(
                ComplexityIssue(
                    tool="complexity",
                    category=ComplexityCategory.DEEP_NESTING.value,
                    severity="warning",
                    message=(
                        f"Function '{func_info.name}' has nesting depth of {nesting} "
                        f"(threshold: {DEFAULT_MAX_NESTING_DEPTH})"
                    ),
                    line=func_info.line_number,
                    function=func_info.name,
                    metrics=metrics_dict,
                    suggestion="Use early returns or extract nested blocks into functions",
                )
            )

    # Class metrics
    class_infos = extract_classes(tree)
    class_nodes = list(tree.nodes_of_class(astroid.ClassDef))
    class_node_map: dict[tuple[str, int], astroid.ClassDef] = {}
    for cn in class_nodes:
        class_node_map[(cn.name, cn.lineno)] = cn

    for class_info in class_infos:
        cn = class_node_map.get((class_info.name, class_info.line_number))
        inheritance_depth = _inheritance_depth(cn) if cn else 0
        method_count = len(class_info.methods)

        cm = ClassMetrics(
            name=class_info.name,
            line=class_info.line_number,
            method_count=method_count,
            inheritance_depth=inheritance_depth,
        )
        result.class_metrics.append(cm)

        if method_count > DEFAULT_MAX_CLASS_METHODS:
            result.issues.append(
                ComplexityIssue(
                    tool="complexity",
                    category=ComplexityCategory.LARGE_CLASS.value,
                    severity="warning",
                    message=(
                        f"Class '{class_info.name}' has {method_count} methods "
                        f"(threshold: {DEFAULT_MAX_CLASS_METHODS})"
                    ),
                    line=class_info.line_number,
                    function=None,
                    suggestion="Consider splitting into smaller, focused classes",
                )
            )

        if inheritance_depth > DEFAULT_MAX_INHERITANCE_DEPTH:
            result.issues.append(
                ComplexityIssue(
                    tool="complexity",
                    category=ComplexityCategory.DEEP_INHERITANCE.value,
                    severity="warning",
                    message=(
                        f"Class '{class_info.name}' has inheritance depth of "
                        f"{inheritance_depth} (threshold: {DEFAULT_MAX_INHERITANCE_DEPTH})"
                    ),
                    line=class_info.line_number,
                    function=None,
                    suggestion="Prefer composition over deep inheritance hierarchies",
                )
            )

    # File-level summary
    total = len(cyclomatic_scores)
    avg = sum(cyclomatic_scores) / total if total else 0.0
    max_c = max(cyclomatic_scores, default=0)
    complex_count = sum(1 for s in cyclomatic_scores if s > cyclomatic_threshold)

    result.file_metrics = FileMetrics(
        total_functions=total,
        average_complexity=round(avg, 2),
        max_complexity=max_c,
        complex_functions=complex_count,
    )

    return result


def _max_nesting_depth(node: astroid.NodeNG, current: int = 0) -> int:
    """Calculate the maximum nesting depth inside a function."""
    max_depth = current

    for child in node.get_children():
        if isinstance(child, (astroid.If, astroid.For, astroid.While, astroid.With, astroid.Try)):
            child_depth = _max_nesting_depth(child, current + 1)
            max_depth = max(max_depth, child_depth)
        else:
            child_depth = _max_nesting_depth(child, current)
            max_depth = max(max_depth, child_depth)

    return max_depth


def _inheritance_depth(node: astroid.ClassDef) -> int:
    """Calculate the inheritance depth of a class."""
    try:
        ancestors = list(node.ancestors())
        return len(ancestors) if ancestors else 0
    except (astroid.InferenceError, StopIteration, RecursionError):
        return len(node.bases)
