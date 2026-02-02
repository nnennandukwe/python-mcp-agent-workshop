"""Pythonic code checker using Astroid for AST analysis."""

from pathlib import Path

import astroid

from .patterns import (
    APPEND_IN_LOOP_MSG,
    APPEND_IN_LOOP_SUGGESTION,
    BARE_EXCEPT_MSG,
    BARE_EXCEPT_SUGGESTION,
    DICT_KEYS_ITERATION_MSG,
    DICT_KEYS_SUGGESTION,
    DICT_SETITEM_IN_LOOP_MSG,
    DICT_SETITEM_IN_LOOP_SUGGESTION,
    EQUALITY_FALSE_MSG,
    EQUALITY_FALSE_SUGGESTION,
    EQUALITY_NONE_MSG,
    EQUALITY_NONE_SUGGESTION,
    EQUALITY_TRUE_MSG,
    EQUALITY_TRUE_SUGGESTION,
    INEQUALITY_NONE_MSG,
    INEQUALITY_NONE_SUGGESTION,
    LEN_NONZERO_CHECK_MSG,
    LEN_NONZERO_SUGGESTION,
    LEN_ZERO_CHECK_MSG,
    LEN_ZERO_SUGGESTION,
    MUTABLE_DEFAULT_DICT_MSG,
    MUTABLE_DEFAULT_DICT_SUGGESTION,
    MUTABLE_DEFAULT_LIST_MSG,
    MUTABLE_DEFAULT_LIST_SUGGESTION,
    MUTABLE_DEFAULT_SET_MSG,
    MUTABLE_DEFAULT_SET_SUGGESTION,
    RANGE_LEN_PATTERN_MSG,
    RANGE_LEN_SUGGESTION,
    REDUNDANT_BOOL_RETURN_MSG,
    REDUNDANT_BOOL_RETURN_SUGGESTION,
    STRING_CONCAT_IN_LOOP_MSG,
    STRING_CONCAT_IN_LOOP_SUGGESTION,
    TYPE_COMPARISON_MSG,
    TYPE_COMPARISON_SUGGESTION,
    IssueCategory,
    PythonicIssue,
    Severity,
)


class PythonicChecker:
    """Analyzes Python code for non-idiomatic patterns and suggests Pythonic alternatives."""

    def __init__(self, source_code: str | None = None, file_path: str | None = None) -> None:
        """
        Initialize the Pythonic checker.

        Args:
            source_code: Python source code as a string
            file_path: Path to a Python file to analyze

        Raises:
            ValueError: If neither source_code nor file_path is provided
            SyntaxError: If the source code has syntax errors
            FileNotFoundError: If file_path doesn't exist
        """
        if source_code is None and file_path is None:
            raise ValueError("Either source_code or file_path must be provided")

        if file_path:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            source_code = path.read_text(encoding="utf-8")
            self.file_path = str(file_path)
        else:
            self.file_path = None

        self.source_code = source_code
        self._source_lines = source_code.splitlines()

        try:
            self.tree = astroid.parse(source_code, path=file_path)
        except astroid.AstroidSyntaxError as e:
            raise SyntaxError(str(e)) from e

        self._issues: list[PythonicIssue] = []

    def check_all(self) -> list[PythonicIssue]:
        """
        Run all Pythonic checks on the code.

        Returns:
            List of PythonicIssue objects for all detected issues
        """
        self._issues = []

        self._check_loop_patterns()
        self._check_comparison_patterns()
        self._check_mutable_defaults()
        self._check_collection_building()
        self._check_redundant_code()
        self._check_exception_patterns()

        return self._issues

    def get_summary(self) -> dict:
        """
        Get a summary of detected issues.

        Returns:
            Dictionary with total_issues and by_category counts
        """
        by_category: dict[str, int] = {}
        for issue in self._issues:
            cat = issue.category.value
            by_category[cat] = by_category.get(cat, 0) + 1

        return {
            "total_issues": len(self._issues),
            "by_category": by_category,
        }

    def _get_source_line(self, lineno: int) -> str | None:
        """Get a source line by line number (1-indexed)."""
        if 1 <= lineno <= len(self._source_lines):
            return self._source_lines[lineno - 1]
        return None

    def _check_loop_patterns(self) -> None:
        """Check for non-idiomatic loop patterns."""
        for node in self.tree.nodes_of_class(astroid.For):
            self._check_range_len(node)
            self._check_dict_keys_iteration(node)

    def _check_range_len(self, node: astroid.For) -> None:
        """Check for range(len(x)) pattern."""
        # Look for: for i in range(len(something))
        if not isinstance(node.iter, astroid.Call):
            return

        func = node.iter.func
        if not isinstance(func, astroid.Name) or func.name != "range":
            return

        if not node.iter.args:
            return

        first_arg = node.iter.args[0]
        if not isinstance(first_arg, astroid.Call):
            return

        len_func = first_arg.func
        if isinstance(len_func, astroid.Name) and len_func.name == "len":
            # Found range(len(...))
            iterable_name = first_arg.args[0].as_string() if first_arg.args else "items"
            self._issues.append(
                PythonicIssue(
                    tool="pythonic",
                    category=IssueCategory.NON_IDIOMATIC_LOOP,
                    severity=Severity.WARNING,
                    message=RANGE_LEN_PATTERN_MSG,
                    line=node.lineno,
                    column=node.col_offset,
                    suggestion=RANGE_LEN_SUGGESTION.format(iterable=iterable_name),
                    code_snippet=self._get_source_line(node.lineno),
                )
            )

    def _check_dict_keys_iteration(self, node: astroid.For) -> None:
        """Check for iterating over dict.keys() directly."""
        # Look for: for key in d.keys()
        if not isinstance(node.iter, astroid.Call):
            return

        func = node.iter.func
        if not isinstance(func, astroid.Attribute):
            return

        if func.attrname != "keys":
            return

        # Found .keys() iteration
        dict_name = func.expr.as_string() if hasattr(func.expr, "as_string") else "d"
        self._issues.append(
            PythonicIssue(
                tool="pythonic",
                category=IssueCategory.NON_IDIOMATIC_LOOP,
                severity=Severity.INFO,
                message=DICT_KEYS_ITERATION_MSG,
                line=node.lineno,
                column=node.col_offset,
                suggestion=DICT_KEYS_SUGGESTION.format(dict_name=dict_name),
                code_snippet=self._get_source_line(node.lineno),
            )
        )

    def _check_comparison_patterns(self) -> None:
        """Check for non-idiomatic comparison patterns."""
        for node in self.tree.nodes_of_class(astroid.Compare):
            self._check_none_comparison(node)
            self._check_bool_comparison(node)
            self._check_type_comparison(node)
            self._check_len_comparison(node)

    def _check_none_comparison(self, node: astroid.Compare) -> None:
        """Check for == None or != None."""
        if len(node.ops) != 1:
            return

        op, comparator = node.ops[0]

        if not isinstance(comparator, astroid.Const) or comparator.value is not None:
            return

        if op == "==":
            self._issues.append(
                PythonicIssue(
                    tool="pythonic",
                    category=IssueCategory.NON_IDIOMATIC_COMPARISON,
                    severity=Severity.WARNING,
                    message=EQUALITY_NONE_MSG,
                    line=node.lineno,
                    column=node.col_offset,
                    suggestion=EQUALITY_NONE_SUGGESTION,
                    code_snippet=self._get_source_line(node.lineno),
                )
            )
        elif op == "!=":
            self._issues.append(
                PythonicIssue(
                    tool="pythonic",
                    category=IssueCategory.NON_IDIOMATIC_COMPARISON,
                    severity=Severity.WARNING,
                    message=INEQUALITY_NONE_MSG,
                    line=node.lineno,
                    column=node.col_offset,
                    suggestion=INEQUALITY_NONE_SUGGESTION,
                    code_snippet=self._get_source_line(node.lineno),
                )
            )

    def _check_bool_comparison(self, node: astroid.Compare) -> None:
        """Check for == True or == False."""
        if len(node.ops) != 1:
            return

        op, comparator = node.ops[0]

        if not isinstance(comparator, astroid.Const):
            return

        if op != "==":
            return

        if comparator.value is True:
            self._issues.append(
                PythonicIssue(
                    tool="pythonic",
                    category=IssueCategory.NON_IDIOMATIC_COMPARISON,
                    severity=Severity.WARNING,
                    message=EQUALITY_TRUE_MSG,
                    line=node.lineno,
                    column=node.col_offset,
                    suggestion=EQUALITY_TRUE_SUGGESTION,
                    code_snippet=self._get_source_line(node.lineno),
                )
            )
        elif comparator.value is False:
            self._issues.append(
                PythonicIssue(
                    tool="pythonic",
                    category=IssueCategory.NON_IDIOMATIC_COMPARISON,
                    severity=Severity.WARNING,
                    message=EQUALITY_FALSE_MSG,
                    line=node.lineno,
                    column=node.col_offset,
                    suggestion=EQUALITY_FALSE_SUGGESTION,
                    code_snippet=self._get_source_line(node.lineno),
                )
            )

    def _check_type_comparison(self, node: astroid.Compare) -> None:
        """Check for type(x) == SomeClass instead of isinstance()."""
        if len(node.ops) != 1:
            return

        op, _ = node.ops[0]
        if op != "==":
            return

        # Check if left side is type() call
        if not isinstance(node.left, astroid.Call):
            return

        func = node.left.func
        if isinstance(func, astroid.Name) and func.name == "type":
            self._issues.append(
                PythonicIssue(
                    tool="pythonic",
                    category=IssueCategory.NON_IDIOMATIC_COMPARISON,
                    severity=Severity.WARNING,
                    message=TYPE_COMPARISON_MSG,
                    line=node.lineno,
                    column=node.col_offset,
                    suggestion=TYPE_COMPARISON_SUGGESTION,
                    code_snippet=self._get_source_line(node.lineno),
                )
            )

    def _check_len_comparison(self, node: astroid.Compare) -> None:
        """Check for len(x) == 0 or len(x) > 0 patterns."""
        if len(node.ops) != 1:
            return

        op, comparator = node.ops[0]

        # Check if left side is len() call
        if not isinstance(node.left, astroid.Call):
            return

        func = node.left.func
        if not (isinstance(func, astroid.Name) and func.name == "len"):
            return

        # Check comparator is 0
        if not isinstance(comparator, astroid.Const) or comparator.value != 0:
            return

        if op == "==":
            self._issues.append(
                PythonicIssue(
                    tool="pythonic",
                    category=IssueCategory.NON_IDIOMATIC_COMPARISON,
                    severity=Severity.INFO,
                    message=LEN_ZERO_CHECK_MSG,
                    line=node.lineno,
                    column=node.col_offset,
                    suggestion=LEN_ZERO_SUGGESTION,
                    code_snippet=self._get_source_line(node.lineno),
                )
            )
        elif op in (">", "!="):
            self._issues.append(
                PythonicIssue(
                    tool="pythonic",
                    category=IssueCategory.NON_IDIOMATIC_COMPARISON,
                    severity=Severity.INFO,
                    message=LEN_NONZERO_CHECK_MSG,
                    line=node.lineno,
                    column=node.col_offset,
                    suggestion=LEN_NONZERO_SUGGESTION,
                    code_snippet=self._get_source_line(node.lineno),
                )
            )

    def _check_mutable_defaults(self) -> None:
        """Check for mutable default arguments."""
        for node in self.tree.nodes_of_class((astroid.FunctionDef, astroid.AsyncFunctionDef)):
            self._check_function_mutable_defaults(node)

    def _check_function_mutable_defaults(
        self, node: astroid.FunctionDef | astroid.AsyncFunctionDef
    ) -> None:
        """Check a function for mutable default arguments."""
        defaults = node.args.defaults + node.args.kw_defaults

        for default in defaults:
            if default is None:
                continue

            if isinstance(default, astroid.List):
                self._issues.append(
                    PythonicIssue(
                        tool="pythonic",
                        category=IssueCategory.MUTABLE_DEFAULT_ARGUMENT,
                        severity=Severity.ERROR,
                        message=MUTABLE_DEFAULT_LIST_MSG,
                        line=default.lineno,
                        column=default.col_offset,
                        suggestion=MUTABLE_DEFAULT_LIST_SUGGESTION,
                        code_snippet=self._get_source_line(default.lineno),
                    )
                )
            elif isinstance(default, astroid.Dict):
                self._issues.append(
                    PythonicIssue(
                        tool="pythonic",
                        category=IssueCategory.MUTABLE_DEFAULT_ARGUMENT,
                        severity=Severity.ERROR,
                        message=MUTABLE_DEFAULT_DICT_MSG,
                        line=default.lineno,
                        column=default.col_offset,
                        suggestion=MUTABLE_DEFAULT_DICT_SUGGESTION,
                        code_snippet=self._get_source_line(default.lineno),
                    )
                )
            elif isinstance(default, astroid.Set):
                self._issues.append(
                    PythonicIssue(
                        tool="pythonic",
                        category=IssueCategory.MUTABLE_DEFAULT_ARGUMENT,
                        severity=Severity.ERROR,
                        message=MUTABLE_DEFAULT_SET_MSG,
                        line=default.lineno,
                        column=default.col_offset,
                        suggestion=MUTABLE_DEFAULT_SET_SUGGESTION,
                        code_snippet=self._get_source_line(default.lineno),
                    )
                )

    def _check_collection_building(self) -> None:
        """Check for inefficient collection building patterns."""
        for node in self.tree.nodes_of_class(astroid.For):
            self._check_append_in_loop(node)
            self._check_string_concat_in_loop(node)
            self._check_dict_setitem_in_loop(node)

    def _check_append_in_loop(self, node: astroid.For) -> None:
        """Check for list.append() in a loop that could be a comprehension."""
        for stmt in node.body:
            if not isinstance(stmt, astroid.Expr):
                continue

            if not isinstance(stmt.value, astroid.Call):
                continue

            func = stmt.value.func
            if isinstance(func, astroid.Attribute) and func.attrname == "append":
                self._issues.append(
                    PythonicIssue(
                        tool="pythonic",
                        category=IssueCategory.INEFFICIENT_COLLECTION_BUILDING,
                        severity=Severity.INFO,
                        message=APPEND_IN_LOOP_MSG,
                        line=stmt.lineno,
                        column=stmt.col_offset,
                        suggestion=APPEND_IN_LOOP_SUGGESTION,
                        code_snippet=self._get_source_line(stmt.lineno),
                    )
                )

    def _check_string_concat_in_loop(self, node: astroid.For) -> None:
        """Check for string concatenation in a loop."""
        for stmt in node.body:
            if not isinstance(stmt, astroid.AugAssign):
                continue

            if stmt.op != "+=":
                continue

            # Check if value being concatenated is a string literal
            if isinstance(stmt.value, astroid.Const) and isinstance(stmt.value.value, str):
                self._issues.append(
                    PythonicIssue(
                        tool="pythonic",
                        category=IssueCategory.INEFFICIENT_COLLECTION_BUILDING,
                        severity=Severity.WARNING,
                        message=STRING_CONCAT_IN_LOOP_MSG,
                        line=stmt.lineno,
                        column=stmt.col_offset,
                        suggestion=STRING_CONCAT_IN_LOOP_SUGGESTION,
                        code_snippet=self._get_source_line(stmt.lineno),
                    )
                )

    def _check_dict_setitem_in_loop(self, node: astroid.For) -> None:
        """Check for dict[key] = value in a loop that could be a comprehension."""
        for stmt in node.body:
            if not isinstance(stmt, astroid.Assign):
                continue

            for target in stmt.targets:
                if isinstance(target, astroid.Subscript):
                    self._issues.append(
                        PythonicIssue(
                            tool="pythonic",
                            category=IssueCategory.INEFFICIENT_COLLECTION_BUILDING,
                            severity=Severity.INFO,
                            message=DICT_SETITEM_IN_LOOP_MSG,
                            line=stmt.lineno,
                            column=stmt.col_offset,
                            suggestion=DICT_SETITEM_IN_LOOP_SUGGESTION,
                            code_snippet=self._get_source_line(stmt.lineno),
                        )
                    )

    def _check_redundant_code(self) -> None:
        """Check for redundant code patterns."""
        for node in self.tree.nodes_of_class(astroid.If):
            self._check_redundant_bool_return(node)

    def _check_redundant_bool_return(self, node: astroid.If) -> None:
        """Check for if x: return True else: return False."""
        # Must have exactly one statement in body and orelse
        if len(node.body) != 1 or len(node.orelse) != 1:
            return

        body_stmt = node.body[0]
        else_stmt = node.orelse[0]

        if not isinstance(body_stmt, astroid.Return) or not isinstance(else_stmt, astroid.Return):
            return

        body_val = body_stmt.value
        else_val = else_stmt.value

        if not isinstance(body_val, astroid.Const) or not isinstance(else_val, astroid.Const):
            return

        # Check for return True / return False pattern
        if body_val.value is True and else_val.value is False:
            self._issues.append(
                PythonicIssue(
                    tool="pythonic",
                    category=IssueCategory.REDUNDANT_CODE,
                    severity=Severity.INFO,
                    message=REDUNDANT_BOOL_RETURN_MSG,
                    line=node.lineno,
                    column=node.col_offset,
                    suggestion=REDUNDANT_BOOL_RETURN_SUGGESTION,
                    code_snippet=self._get_source_line(node.lineno),
                    end_line=else_stmt.lineno,
                )
            )
        elif body_val.value is False and else_val.value is True:
            self._issues.append(
                PythonicIssue(
                    tool="pythonic",
                    category=IssueCategory.REDUNDANT_CODE,
                    severity=Severity.INFO,
                    message=REDUNDANT_BOOL_RETURN_MSG,
                    line=node.lineno,
                    column=node.col_offset,
                    suggestion="return not condition",
                    code_snippet=self._get_source_line(node.lineno),
                    end_line=else_stmt.lineno,
                )
            )

    def _check_exception_patterns(self) -> None:
        """Check for non-idiomatic exception patterns."""
        for node in self.tree.nodes_of_class(astroid.ExceptHandler):
            self._check_bare_except(node)

    def _check_bare_except(self, node: astroid.ExceptHandler) -> None:
        """Check for bare except: clause."""
        if node.type is None:
            self._issues.append(
                PythonicIssue(
                    tool="pythonic",
                    category=IssueCategory.NON_IDIOMATIC_EXCEPTION,
                    severity=Severity.WARNING,
                    message=BARE_EXCEPT_MSG,
                    line=node.lineno,
                    column=node.col_offset,
                    suggestion=BARE_EXCEPT_SUGGESTION,
                    code_snippet=self._get_source_line(node.lineno),
                )
            )
