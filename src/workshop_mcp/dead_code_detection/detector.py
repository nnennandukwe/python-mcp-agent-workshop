"""Main dead code detector that orchestrates all checks."""

import re
from dataclasses import dataclass, field
from pathlib import Path

import astroid

from ..core.ast_utils import extract_imports, parse_source
from .patterns import (
    EXTERNALLY_USED_DECORATORS,
    IGNORED_PARAMETERS,
    DeadCodeCategory,
    DeadCodeIssue,
    Severity,
)
from .usage_graph import build_usage_graph


@dataclass
class DeadCodeSummary:
    """Summary counts by category."""

    unused_imports: int = 0
    unused_functions: int = 0
    unused_variables: int = 0
    unused_parameters: int = 0
    unreachable_blocks: int = 0
    redundant_conditions: int = 0


@dataclass
class DeadCodeResult:
    """Full result from dead code detection."""

    issues: list[DeadCodeIssue] = field(default_factory=list)
    summary: DeadCodeSummary = field(default_factory=DeadCodeSummary)


class DeadCodeDetector:
    """Detects dead code patterns in Python source code."""

    def __init__(
        self,
        source_code: str | None = None,
        *,
        file_path: str | None = None,
        check_imports: bool = True,
        check_variables: bool = True,
        check_functions: bool = True,
        ignore_patterns: list[str] | None = None,
    ):
        """Initialize the detector.

        Args:
            source_code: Python source code to analyze.
            file_path: Path to a Python file to analyze.
            check_imports: Whether to check for unused imports.
            check_variables: Whether to check for unused variables.
            check_functions: Whether to check for unused functions.
            ignore_patterns: Regex patterns for names to skip.

        Raises:
            ValueError: If neither source_code nor file_path is provided.
            FileNotFoundError: If file_path doesn't exist.
            SyntaxError: If source code cannot be parsed.
        """
        if source_code is None and file_path is None:
            raise ValueError("Either source_code or file_path must be provided")

        if file_path and source_code is None:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            source_code = path.read_text(encoding="utf-8")

        self.source_code = source_code
        self.file_path = file_path
        self.tree = parse_source(source_code, file_path)
        self.graph = build_usage_graph(self.tree)
        self.check_imports = check_imports
        self.check_variables = check_variables
        self.check_functions = check_functions
        self._ignore_res = [re.compile(p) for p in (ignore_patterns or [])]

    def detect_all(self) -> DeadCodeResult:
        """Run all enabled dead code checks.

        Returns:
            DeadCodeResult with issues and summary.
        """
        result = DeadCodeResult()

        if self.check_imports:
            issues = self._detect_unused_imports()
            result.issues.extend(issues)
            result.summary.unused_imports = len(issues)

        if self.check_variables:
            issues = self._detect_unused_variables()
            result.issues.extend(issues)
            result.summary.unused_variables = len(issues)

        if self.check_functions:
            issues = self._detect_unused_functions()
            result.issues.extend(issues)
            result.summary.unused_functions = len(issues)

        param_issues = self._detect_unused_parameters()
        result.issues.extend(param_issues)
        result.summary.unused_parameters = len(param_issues)

        unreachable_issues = self._detect_unreachable_code()
        result.issues.extend(unreachable_issues)
        result.summary.unreachable_blocks = len(unreachable_issues)

        redundant_issues = self._detect_redundant_conditions()
        result.issues.extend(redundant_issues)
        result.summary.redundant_conditions = len(redundant_issues)

        result.issues.sort(key=lambda i: i.line)
        return result

    def _should_ignore(self, name: str) -> bool:
        """Check if a name matches any ignore pattern."""
        return any(r.fullmatch(name) for r in self._ignore_res)

    # ------------------------------------------------------------------
    # Unused imports
    # ------------------------------------------------------------------
    def _detect_unused_imports(self) -> list[DeadCodeIssue]:
        issues: list[DeadCodeIssue] = []
        imports = extract_imports(self.tree)

        for imp in imports:
            for name in imp.names:
                local_name = imp.aliases.get(name, name)

                if self._should_ignore(local_name):
                    continue
                if self.graph.is_in_all(local_name):
                    continue
                if not self.graph.is_referenced(local_name):
                    if imp.is_from_import:
                        msg = f"Import '{name}' from '{imp.module}' is never used"
                    else:
                        msg = f"Import '{name}' is never used"
                    issues.append(
                        DeadCodeIssue(
                            category=DeadCodeCategory.UNUSED_IMPORT,
                            severity=Severity.INFO,
                            message=msg,
                            line=imp.line_number,
                            name=local_name,
                            suggestion="Remove unused import or use '# noqa' if intentional",
                        )
                    )
        return issues

    # ------------------------------------------------------------------
    # Unused variables
    # ------------------------------------------------------------------
    def _detect_unused_variables(self) -> list[DeadCodeIssue]:
        issues: list[DeadCodeIssue] = []

        for node in self.tree.nodes_of_class(astroid.Assign):
            for target in node.targets:
                if isinstance(target, astroid.AssignName):
                    name = target.name
                    if name.startswith("_"):
                        continue
                    if self._should_ignore(name):
                        continue
                    if self.graph.is_in_all(name):
                        continue
                    if not self.graph.is_referenced(name):
                        issues.append(
                            DeadCodeIssue(
                                category=DeadCodeCategory.UNUSED_VARIABLE,
                                severity=Severity.WARNING,
                                message=f"Variable '{name}' is assigned but never used",
                                line=target.lineno,
                                name=name,
                                suggestion="Remove the assignment or use the variable",
                            )
                        )
        return issues

    # ------------------------------------------------------------------
    # Unused functions
    # ------------------------------------------------------------------
    def _detect_unused_functions(self) -> list[DeadCodeIssue]:
        issues: list[DeadCodeIssue] = []

        # Only check top-level and class-level functions (not nested)
        for node in self.tree.body:
            if isinstance(node, (astroid.FunctionDef, astroid.AsyncFunctionDef)):
                self._check_function_unused(node, issues)
            elif isinstance(node, astroid.ClassDef):
                for item in node.body:
                    if isinstance(item, (astroid.FunctionDef, astroid.AsyncFunctionDef)):
                        self._check_function_unused(item, issues)

        return issues

    def _check_function_unused(
        self,
        node: astroid.FunctionDef | astroid.AsyncFunctionDef,
        issues: list[DeadCodeIssue],
    ) -> None:
        """Check if a single function is unused and add issue if so."""
        name = node.name

        if name.startswith("test_"):
            return
        if name.startswith("__") and name.endswith("__"):
            return
        decorators = (
            [self._decorator_name(d) for d in node.decorators.nodes] if node.decorators else []
        )
        if any(d in EXTERNALLY_USED_DECORATORS for d in decorators):
            return
        if self._should_ignore(name):
            return
        if self.graph.is_in_all(name):
            return

        if not self.graph.is_referenced(name):
            sev = Severity.INFO if not name.startswith("_") else Severity.WARNING
            issues.append(
                DeadCodeIssue(
                    category=DeadCodeCategory.UNUSED_FUNCTION,
                    severity=sev,
                    message=f"Function '{name}' is defined but never called",
                    line=node.lineno,
                    name=name,
                    suggestion="Remove unused function or verify it's used externally",
                )
            )

    # ------------------------------------------------------------------
    # Unused parameters
    # ------------------------------------------------------------------
    def _detect_unused_parameters(self) -> list[DeadCodeIssue]:
        issues: list[DeadCodeIssue] = []

        for node in self.tree.nodes_of_class((astroid.FunctionDef, astroid.AsyncFunctionDef)):
            if self._is_stub_function(node):
                continue
            decorators = (
                [self._decorator_name(d) for d in node.decorators.nodes] if node.decorators else []
            )
            if any(d in EXTERNALLY_USED_DECORATORS for d in decorators):
                continue

            body_refs: set[str] = set()
            for child in node.get_children():
                self._collect_names(child, body_refs)

            for arg in node.args.args:
                name = arg.name
                if name in IGNORED_PARAMETERS:
                    continue
                if name.startswith("_"):
                    continue
                if self._should_ignore(name):
                    continue
                if name not in body_refs:
                    issues.append(
                        DeadCodeIssue(
                            category=DeadCodeCategory.UNUSED_PARAMETER,
                            severity=Severity.INFO,
                            message=f"Parameter '{name}' in function '{node.name}' is never used",
                            line=node.lineno,
                            name=name,
                            suggestion=f"Remove parameter or prefix with underscore: _{name}",
                        )
                    )

        return issues

    # ------------------------------------------------------------------
    # Unreachable code
    # ------------------------------------------------------------------
    def _detect_unreachable_code(self) -> list[DeadCodeIssue]:
        issues: list[DeadCodeIssue] = []
        self._find_unreachable(self.tree, issues)
        return issues

    def _find_unreachable(self, node: astroid.NodeNG, issues: list[DeadCodeIssue]) -> None:
        """Recursively find code after return/raise/break/continue."""
        if hasattr(node, "body") and isinstance(node.body, list):
            self._check_block_for_unreachable(node.body, issues)

        for attr in ("orelse", "handlers", "finalbody"):
            block = getattr(node, attr, None)
            if isinstance(block, list):
                self._check_block_for_unreachable(block, issues)

        for child in node.get_children():
            if isinstance(child, (astroid.FunctionDef, astroid.AsyncFunctionDef, astroid.ClassDef)):
                self._find_unreachable(child, issues)
            elif hasattr(child, "body"):
                self._find_unreachable(child, issues)

    def _check_block_for_unreachable(
        self, stmts: list[astroid.NodeNG], issues: list[DeadCodeIssue]
    ) -> None:
        """Check a list of statements for code after terminating statements."""
        terminal_types = (astroid.Return, astroid.Raise, astroid.Break, astroid.Continue)

        for i, stmt in enumerate(stmts):
            if isinstance(stmt, terminal_types) and i < len(stmts) - 1:
                next_stmt = stmts[i + 1]
                kind = type(stmt).__name__.lower()
                issues.append(
                    DeadCodeIssue(
                        category=DeadCodeCategory.UNREACHABLE_CODE,
                        severity=Severity.WARNING,
                        message=f"Code after '{kind}' statement is unreachable",
                        line=next_stmt.lineno,
                        name=f"after_{kind}",
                        suggestion="Remove unreachable code",
                    )
                )
                break

    # ------------------------------------------------------------------
    # Redundant conditions
    # ------------------------------------------------------------------
    def _detect_redundant_conditions(self) -> list[DeadCodeIssue]:
        issues: list[DeadCodeIssue] = []

        for node in self.tree.nodes_of_class(astroid.If):
            if isinstance(node.test, astroid.Const):
                if node.test.value is True:
                    issues.append(
                        DeadCodeIssue(
                            category=DeadCodeCategory.REDUNDANT_CONDITION,
                            severity=Severity.WARNING,
                            message="Condition is always True",
                            line=node.lineno,
                            name="if True",
                            suggestion="Remove the if statement and keep only the body",
                        )
                    )
                elif node.test.value is False:
                    issues.append(
                        DeadCodeIssue(
                            category=DeadCodeCategory.REDUNDANT_CONDITION,
                            severity=Severity.WARNING,
                            message="Condition is always False — block never executes",
                            line=node.lineno,
                            name="if False",
                            suggestion="Remove the dead code block",
                        )
                    )

        for node in self.tree.nodes_of_class(astroid.While):
            if isinstance(node.test, astroid.Const) and node.test.value is False:
                issues.append(
                    DeadCodeIssue(
                        category=DeadCodeCategory.REDUNDANT_CONDITION,
                        severity=Severity.WARNING,
                        message="while False loop never executes",
                        line=node.lineno,
                        name="while False",
                        suggestion="Remove the dead loop",
                    )
                )

        return issues

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _is_stub_function(node: astroid.FunctionDef) -> bool:
        """Check if a function body is just pass/Ellipsis/docstring (stub)."""
        body = node.body
        if len(body) == 0:
            return True
        if len(body) == 1:
            stmt = body[0]
            if isinstance(stmt, astroid.Pass):
                return True
            if isinstance(stmt, astroid.Expr) and isinstance(stmt.value, astroid.Const):
                return True
        if len(body) == 2:
            if isinstance(body[0], astroid.Expr) and isinstance(body[1], astroid.Pass):
                return True
        return False

    @staticmethod
    def _decorator_name(dec: astroid.NodeNG) -> str:
        if isinstance(dec, astroid.Name):
            return dec.name
        if isinstance(dec, astroid.Attribute):
            return dec.as_string()
        if isinstance(dec, astroid.Call):
            if isinstance(dec.func, astroid.Name):
                return dec.func.name
            if isinstance(dec.func, astroid.Attribute):
                return dec.func.as_string()
        return ""

    @staticmethod
    def _collect_names(node: astroid.NodeNG, names: set[str]) -> None:
        """Collect all Name references in a subtree."""
        if isinstance(node, astroid.Name):
            names.add(node.name)
        for child in node.get_children():
            DeadCodeDetector._collect_names(child, names)


def detect_dead_code(
    source_code: str | None = None,
    *,
    file_path: str | None = None,
    check_imports: bool = True,
    check_variables: bool = True,
    check_functions: bool = True,
    ignore_patterns: list[str] | None = None,
) -> DeadCodeResult:
    """Convenience function to run dead code detection.

    Args:
        source_code: Python source code to analyze.
        file_path: Path to a Python file to analyze.
        check_imports: Whether to check for unused imports.
        check_variables: Whether to check for unused variables.
        check_functions: Whether to check for unused functions.
        ignore_patterns: Regex patterns for names to skip.

    Returns:
        DeadCodeResult with issues and summary.

    Raises:
        ValueError: If neither source_code nor file_path is provided.
        SyntaxError: If source code cannot be parsed.
    """
    detector = DeadCodeDetector(
        source_code=source_code,
        file_path=file_path,
        check_imports=check_imports,
        check_variables=check_variables,
        check_functions=check_functions,
        ignore_patterns=ignore_patterns,
    )
    return detector.detect_all()
