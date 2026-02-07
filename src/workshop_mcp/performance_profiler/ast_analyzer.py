"""AST analyzer for extracting code structure from Python files using Astroid."""

from pathlib import Path

import astroid

from workshop_mcp.core.ast_utils import (
    CallInfo,
    FunctionInfo,
    ImportInfo,
    LoopInfo,
    extract_calls,
    extract_functions,
    extract_imports,
    get_source_segment,
)
from workshop_mcp.core.inference import infer_callable

# Re-export dataclasses so existing imports from this module keep working
__all__ = ["ASTAnalyzer", "FunctionInfo", "LoopInfo", "ImportInfo", "CallInfo"]


class ASTAnalyzer:
    """Analyzes Python code using Astroid for semantic understanding."""

    def __init__(self, source_code: str | None = None, file_path: str | None = None):
        """
        Initialize the AST analyzer with Astroid.

        Args:
            source_code: Python source code as a string
            file_path: Path to a Python file to analyze

        Raises:
            ValueError: If neither source_code nor file_path is provided
            astroid.AstroidSyntaxError: If the source code has syntax errors
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
            self.file_path = file_path

        self.source_code = source_code

        try:
            self.tree = astroid.parse(source_code, path=file_path)
        except astroid.AstroidSyntaxError as e:
            # Re-raise as SyntaxError for backwards compatibility with tests
            raise SyntaxError(str(e)) from e

        self._functions: list[FunctionInfo] | None = None
        self._loops: list[LoopInfo] | None = None
        self._imports: list[ImportInfo] | None = None
        self._calls: list[CallInfo] | None = None

    def get_functions(self) -> list[FunctionInfo]:
        """
        Extract all function definitions from the code.

        Returns:
            List of FunctionInfo objects containing function metadata
        """
        if self._functions is not None:
            return self._functions

        self._functions = extract_functions(self.tree)
        return self._functions

    def get_loops(self) -> list[LoopInfo]:
        """
        Extract all loop constructs from the code.

        Returns:
            List of LoopInfo objects containing loop metadata
        """
        if self._loops is not None:
            return self._loops

        loops: list[LoopInfo] = []
        self._extract_loops_recursive(self.tree, loops, None, 0, False)
        self._loops = loops
        return loops

    def get_imports(self) -> list[ImportInfo]:
        """
        Extract all import statements from the code.

        Returns:
            List of ImportInfo objects containing import metadata
        """
        if self._imports is not None:
            return self._imports

        self._imports = extract_imports(self.tree)
        return self._imports

    def get_calls(self) -> list[CallInfo]:
        """
        Extract all function calls from the code.

        Returns:
            List of CallInfo objects containing call metadata
        """
        if self._calls is not None:
            return self._calls

        self._calls = extract_calls(self.tree)
        return self._calls

    def get_async_functions(self) -> list[FunctionInfo]:
        """
        Get only async function definitions.

        Returns:
            List of FunctionInfo objects for async functions
        """
        return [f for f in self.get_functions() if f.is_async]

    def get_functions_in_range(self, start_line: int, end_line: int) -> list[FunctionInfo]:
        """
        Get functions defined within a specific line range.

        Args:
            start_line: Starting line number (inclusive)
            end_line: Ending line number (inclusive)

        Returns:
            List of FunctionInfo objects within the range
        """
        return [f for f in self.get_functions() if start_line <= f.line_number <= end_line]

    def get_loops_in_function(self, function_name: str) -> list[LoopInfo]:
        """
        Get all loops within a specific function.

        Args:
            function_name: Name of the function

        Returns:
            List of LoopInfo objects within the function
        """
        return [loop for loop in self.get_loops() if loop.parent_function == function_name]

    def get_max_loop_nesting_depth(self) -> int:
        """
        Get the maximum nesting depth of loops in the code.

        Returns:
            Maximum nesting level (0 if no loops)
        """
        loops = self.get_loops()
        return max((loop.nesting_level for loop in loops), default=0)

    def has_blocking_calls_in_async(self) -> bool:
        """
        Check if there are potentially blocking calls in async functions.

        Returns:
            True if blocking calls are found in async functions
        """
        # This is a simple heuristic - will be enhanced in async_validator
        blocking_patterns = {"open", "read", "write", "sleep"}
        calls = self.get_calls()

        for call in calls:
            if call.is_in_async_function:
                # Check if it's a potentially blocking call
                func_name_lower = call.function_name.lower()
                if any(pattern in func_name_lower for pattern in blocking_patterns):
                    # Check if it's not an async version (aiofiles, asyncio.sleep, etc.)
                    if not (
                        call.function_name.startswith(("aio", "async"))
                        or "asyncio" in func_name_lower
                    ):
                        return True
        return False

    def _extract_loops_recursive(
        self,
        node: astroid.NodeNG,
        loops: list[LoopInfo],
        parent_function: str | None,
        nesting_level: int,
        is_in_async: bool,
    ) -> None:
        """Recursively extract loop information from Astroid nodes."""
        # Check if we're entering a function
        current_function = parent_function
        current_is_async = is_in_async

        if isinstance(node, (astroid.FunctionDef, astroid.AsyncFunctionDef)):
            current_function = node.name
            current_is_async = isinstance(node, astroid.AsyncFunctionDef)

        # Process loops
        if isinstance(node, (astroid.For, astroid.While)):
            loop_type = "for" if isinstance(node, astroid.For) else "while"
            loop_info = LoopInfo(
                type=loop_type,
                line_number=node.lineno,
                end_line_number=node.end_lineno or node.lineno,
                parent_function=current_function,
                nesting_level=nesting_level,
                is_in_async_function=current_is_async,
            )
            loops.append(loop_info)

            # Recurse into loop body with increased nesting
            for child in node.get_children():
                self._extract_loops_recursive(
                    child, loops, current_function, nesting_level + 1, current_is_async
                )
        else:
            # Continue recursion without increasing nesting
            for child in node.get_children():
                self._extract_loops_recursive(
                    child, loops, current_function, nesting_level, current_is_async
                )

    def _infer_callable_name(self, node: astroid.NodeNG) -> str | None:
        """
        Try to infer the fully qualified name of a callable.

        This is where Astroid shines - it can resolve what a function actually is.
        """
        return infer_callable(node)

    def get_source_segment(self, line_start: int, line_end: int) -> str:
        """
        Get a segment of the source code.

        Args:
            line_start: Starting line number (1-indexed)
            line_end: Ending line number (1-indexed, inclusive)

        Returns:
            Source code segment as a string
        """
        return get_source_segment(self.source_code, line_start, line_end)
