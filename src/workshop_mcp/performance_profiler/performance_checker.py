"""Performance checker for detecting anti-patterns in Python code."""

from collections import Counter

from .ast_analyzer import ASTAnalyzer
from .patterns import (
    IssueCategory,
    PerformanceIssue,
    Severity,
    get_async_alternative,
    get_memory_optimization_suggestion,
    get_orm_type,
    get_orm_type_from_function_name,
    is_blocking_io,
    is_inefficient_string_op,
    is_memory_intensive,
    is_orm_query,
    is_type_conversion,
)


class PerformanceChecker:
    """Analyzes Python code for performance anti-patterns."""

    def __init__(self, source_code: str | None = None, file_path: str | None = None):
        """
        Initialize the performance checker.

        Args:
            source_code: Python source code as a string
            file_path: Path to a Python file to analyze

        Raises:
            ValueError: If neither source_code nor file_path is provided
            SyntaxError: If the source code has syntax errors
            FileNotFoundError: If file_path doesn't exist
        """
        self.analyzer = ASTAnalyzer(source_code=source_code, file_path=file_path)
        self._issues: list[PerformanceIssue] | None = None

    def check_all(self) -> list[PerformanceIssue]:
        """
        Run all performance checks on the code.

        Returns:
            List of detected performance issues
        """
        if self._issues is not None:
            return self._issues

        issues = []

        # Run all checks
        issues.extend(self.check_n_plus_one_queries())
        issues.extend(self.check_blocking_io_in_async())
        issues.extend(self.check_inefficient_loops())
        issues.extend(self.check_memory_inefficiencies())
        issues.extend(self.check_exception_in_loops())
        issues.extend(self.check_type_conversions_in_loops())
        issues.extend(self.check_global_mutations())

        # Sort by severity (critical first) and then by line number
        severity_order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
        }
        issues.sort(key=lambda x: (severity_order[x.severity], x.line_number))

        self._issues = issues
        return issues

    def check_n_plus_one_queries(self) -> list[PerformanceIssue]:
        """
        Detect N+1 query anti-patterns.

        This occurs when code iterates over a collection and makes a database
        query for each item instead of fetching all data at once.

        Returns:
            List of N+1 query issues
        """
        issues = []
        calls = self.analyzer.get_calls()

        # Find database queries inside loops
        for call in calls:
            if call.is_in_loop and is_orm_query(call.function_name, call.inferred_callable):
                orm_type = get_orm_type(call.inferred_callable) or get_orm_type_from_function_name(
                    call.function_name
                )

                # Determine suggestion based on ORM type
                if orm_type == "django":
                    suggestion = (
                        "Use select_related() for foreign keys or "
                        "prefetch_related() for many-to-many relationships "
                        "to fetch related objects in a single query"
                    )
                elif orm_type == "sqlalchemy":
                    suggestion = (
                        "Use joinedload() or subqueryload() to eager load "
                        "related objects and reduce query count"
                    )
                else:
                    suggestion = (
                        "Consider fetching all required data before the loop "
                        "or using a JOIN query to reduce database round-trips"
                    )

                code_snippet = self.analyzer.get_source_segment(call.line_number, call.line_number)

                issue = PerformanceIssue(
                    category=IssueCategory.N_PLUS_ONE_QUERY,
                    severity=Severity.HIGH,
                    line_number=call.line_number,
                    end_line_number=call.line_number,
                    description=f"Potential N+1 query: {call.function_name} called inside a loop",
                    suggestion=suggestion,
                    code_snippet=code_snippet,
                    function_name=call.parent_function,
                )
                issues.append(issue)

        return issues

    def check_blocking_io_in_async(self) -> list[PerformanceIssue]:
        """
        Detect blocking I/O operations in async functions.

        Blocking I/O in async functions defeats the purpose of async/await
        and can cause the entire event loop to stall.

        Returns:
            List of blocking I/O issues
        """
        issues = []
        calls = self.analyzer.get_calls()

        for call in calls:
            if call.is_in_async_function and is_blocking_io(
                call.function_name, call.inferred_callable
            ):
                alternative = get_async_alternative(call.function_name, call.inferred_callable)

                suggestion = "Replace with async alternative"
                if alternative:
                    suggestion = f"Replace with {alternative} and use await"

                code_snippet = self.analyzer.get_source_segment(call.line_number, call.line_number)

                issue = PerformanceIssue(
                    category=IssueCategory.BLOCKING_IO_IN_ASYNC,
                    severity=Severity.CRITICAL,
                    line_number=call.line_number,
                    end_line_number=call.line_number,
                    description=f"Blocking I/O call '{call.function_name}' in async function blocks event loop",
                    suggestion=suggestion,
                    code_snippet=code_snippet,
                    function_name=call.parent_function,
                )
                issues.append(issue)

        return issues

    def check_inefficient_loops(self) -> list[PerformanceIssue]:
        """
        Detect inefficient patterns in loops.

        Common issues:
        - String concatenation in loops (creates new string each iteration)
        - Repeated calculations that could be done once
        - Deep nesting

        Returns:
            List of inefficient loop issues
        """
        issues = []

        # Check for string concatenation in loops
        calls = self.analyzer.get_calls()
        for call in calls:
            if call.is_in_loop and is_inefficient_string_op(
                call.function_name, call.inferred_callable
            ):
                code_snippet = self.analyzer.get_source_segment(call.line_number, call.line_number)

                issue = PerformanceIssue(
                    category=IssueCategory.INEFFICIENT_LOOP,
                    severity=Severity.MEDIUM,
                    line_number=call.line_number,
                    end_line_number=call.line_number,
                    description="String concatenation in loop creates new string object each iteration",
                    suggestion="Use list.append() and ''.join(list) or io.StringIO for better performance",
                    code_snippet=code_snippet,
                    function_name=call.parent_function,
                )
                issues.append(issue)

        # Check for deeply nested loops
        max_depth = self.analyzer.get_max_loop_nesting_depth()
        if max_depth >= 2:
            # Find the deeply nested loops
            loops = self.analyzer.get_loops()
            for loop in loops:
                if loop.nesting_level >= 2:  # 0-indexed, so level 2 = 3 deep
                    code_snippet = self.analyzer.get_source_segment(
                        loop.line_number,
                        min(loop.line_number + 2, loop.end_line_number),
                    )

                    issue = PerformanceIssue(
                        category=IssueCategory.INEFFICIENT_LOOP,
                        severity=Severity.MEDIUM,
                        line_number=loop.line_number,
                        end_line_number=loop.end_line_number,
                        description=f"Deeply nested loop (depth {loop.nesting_level + 1}) has O(n^{loop.nesting_level + 1}) complexity",
                        suggestion="Consider if the algorithm can be optimized with better data structures or caching",
                        code_snippet=code_snippet,
                        function_name=loop.parent_function,
                    )
                    issues.append(issue)

        return issues

    def check_memory_inefficiencies(self) -> list[PerformanceIssue]:
        """
        Detect memory inefficiency patterns.

        Common issues:
        - Reading entire large files into memory (read, readlines)
        - Loading entire data structures (json.load, pickle.load)
        - Unbounded list growth
        - Missing generator usage

        Returns:
            List of memory inefficiency issues
        """
        issues = []
        calls = self.analyzer.get_calls()

        # Check for memory-intensive operations
        for call in calls:
            if is_memory_intensive(call.function_name, call.inferred_callable):
                suggestion = get_memory_optimization_suggestion(
                    call.function_name, call.inferred_callable
                )

                code_snippet = self.analyzer.get_source_segment(call.line_number, call.line_number)

                # Determine specific description based on operation type
                operation = call.function_name
                if "json.load" in operation:
                    description = (
                        f"Loading entire JSON file with {operation}() loads all data into memory"
                    )
                elif "pickle.load" in operation:
                    description = (
                        f"Loading entire pickle file with {operation}() loads all data into memory"
                    )
                elif "readlines" in operation:
                    description = (
                        f"Reading all lines with {operation}() loads entire file into memory"
                    )
                elif "read" in operation:
                    description = (
                        f"Reading entire file with {operation}() loads all data into memory"
                    )
                else:
                    description = f"Memory-intensive operation {operation}() loads large amount of data into memory"

                issue = PerformanceIssue(
                    category=IssueCategory.MEMORY_INEFFICIENCY,
                    severity=Severity.MEDIUM,
                    line_number=call.line_number,
                    end_line_number=call.line_number,
                    description=description,
                    suggestion=suggestion,
                    code_snippet=code_snippet,
                    function_name=call.parent_function,
                )
                issues.append(issue)

        return issues

    def check_exception_in_loops(self) -> list[PerformanceIssue]:
        """
        Detect try/except blocks inside loops.

        Exception handling has significant overhead in Python. When try/except
        is used inside a loop, this overhead is incurred on every iteration.

        Returns:
            List of exception-in-loop issues
        """
        issues = []
        try_excepts = self.analyzer.get_try_except_statements()

        for try_except in try_excepts:
            if try_except.is_in_loop:
                code_snippet = self.analyzer.get_source_segment(
                    try_except.line_number,
                    min(try_except.line_number + 3, try_except.end_line_number),
                )

                issue = PerformanceIssue(
                    category=IssueCategory.EXCEPTION_IN_LOOP,
                    severity=Severity.MEDIUM,
                    line_number=try_except.line_number,
                    end_line_number=try_except.end_line_number,
                    description="Try/except block inside loop incurs exception handling overhead on each iteration",
                    suggestion="Move try/except outside the loop, or use conditional checks (if/else) for expected cases",
                    code_snippet=code_snippet,
                    function_name=try_except.parent_function,
                )
                issues.append(issue)

        return issues

    def check_type_conversions_in_loops(self) -> list[PerformanceIssue]:
        """
        Detect type conversion calls inside loops.

        Type conversions like int(), str(), float() create new objects.
        When called repeatedly in a loop, this can be inefficient if the
        conversion could be done once outside the loop.

        Returns:
            List of type-conversion-in-loop issues
        """
        issues = []
        calls = self.analyzer.get_calls()

        for call in calls:
            if call.is_in_loop and is_type_conversion(call.function_name, call.inferred_callable):
                code_snippet = self.analyzer.get_source_segment(call.line_number, call.line_number)

                issue = PerformanceIssue(
                    category=IssueCategory.TYPE_CONVERSION_IN_LOOP,
                    severity=Severity.MEDIUM,
                    line_number=call.line_number,
                    end_line_number=call.line_number,
                    description=f"Type conversion '{call.function_name}()' called inside loop creates new objects each iteration",
                    suggestion="If converting the same value repeatedly, move the conversion outside the loop",
                    code_snippet=code_snippet,
                    function_name=call.parent_function,
                )
                issues.append(issue)

        return issues

    def check_global_mutations(self) -> list[PerformanceIssue]:
        """
        Detect functions that mutate global state.

        Functions using 'global' keyword to modify global variables make code
        harder to reason about and can cause issues in concurrent code.

        Returns:
            List of global mutation issues
        """
        issues = []
        globals_list = self.analyzer.get_global_statements()

        for global_stmt in globals_list:
            if global_stmt.parent_function:  # Only flag when inside a function
                code_snippet = self.analyzer.get_source_segment(
                    global_stmt.line_number, global_stmt.line_number
                )

                names_str = ", ".join(global_stmt.names)
                issue = PerformanceIssue(
                    category=IssueCategory.GLOBAL_MUTATION,
                    severity=Severity.MEDIUM,
                    line_number=global_stmt.line_number,
                    end_line_number=global_stmt.line_number,
                    description=f"Function modifies global variable(s): {names_str}",
                    suggestion="Pass values as parameters and return results instead of using global state",
                    code_snippet=code_snippet,
                    function_name=global_stmt.parent_function,
                )
                issues.append(issue)

        return issues

    def get_issues_by_severity(self, severity: Severity) -> list[PerformanceIssue]:
        """
        Get issues filtered by severity level.

        Args:
            severity: Severity level to filter by

        Returns:
            List of issues with the specified severity
        """
        all_issues = self.check_all()
        return [issue for issue in all_issues if issue.severity == severity]

    def get_issues_by_category(self, category: IssueCategory) -> list[PerformanceIssue]:
        """
        Get issues filtered by category.

        Args:
            category: Issue category to filter by

        Returns:
            List of issues in the specified category
        """
        all_issues = self.check_all()
        return [issue for issue in all_issues if issue.category == category]

    def get_critical_issues(self) -> list[PerformanceIssue]:
        """
        Get all critical severity issues.

        Returns:
            List of critical issues
        """
        return self.get_issues_by_severity(Severity.CRITICAL)

    def has_issues(self) -> bool:
        """
        Check if any performance issues were found.

        Returns:
            True if issues were found, False otherwise
        """
        return len(self.check_all()) > 0

    def get_summary(self) -> dict:
        """
        Get a summary of all detected issues.

        Returns:
            Dictionary with issue counts by severity and category
        """
        all_issues = self.check_all()

        severity_counts = Counter(issue.severity for issue in all_issues)
        category_counts = Counter(issue.category for issue in all_issues)

        summary = {
            "total_issues": len(all_issues),
            "by_severity": {s.value: severity_counts.get(s, 0) for s in Severity},
            "by_category": {c.value: category_counts.get(c, 0) for c in IssueCategory},
        }

        return summary
