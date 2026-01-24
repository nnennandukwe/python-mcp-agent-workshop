"""AST analyzer for extracting code structure from Python files."""

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union


@dataclass
class FunctionInfo:
    """Information about a function in the code."""

    name: str
    line_number: int
    end_line_number: int
    is_async: bool
    parameters: List[str]
    decorators: List[str]
    return_annotation: Optional[str]
    docstring: Optional[str]


@dataclass
class LoopInfo:
    """Information about a loop in the code."""

    type: str  # 'for' or 'while'
    line_number: int
    end_line_number: int
    parent_function: Optional[str]
    nesting_level: int
    is_in_async_function: bool


@dataclass
class ImportInfo:
    """Information about an import statement."""

    module: str
    names: List[str]
    line_number: int
    is_from_import: bool
    aliases: Dict[str, str]  # Maps imported name to alias


@dataclass
class CallInfo:
    """Information about a function call."""

    function_name: str
    line_number: int
    parent_function: Optional[str]
    is_in_loop: bool
    is_in_async_function: bool


class ASTAnalyzer:
    """Analyzes Python code using Abstract Syntax Trees."""

    def __init__(self, source_code: Optional[str] = None, file_path: Optional[str] = None):
        """
        Initialize the AST analyzer.

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

        self.source_code = source_code
        self.file_path = file_path
        self.tree = ast.parse(source_code)
        self._functions: Optional[List[FunctionInfo]] = None
        self._loops: Optional[List[LoopInfo]] = None
        self._imports: Optional[List[ImportInfo]] = None
        self._calls: Optional[List[CallInfo]] = None

    def get_functions(self) -> List[FunctionInfo]:
        """
        Extract all function definitions from the code.

        Returns:
            List of FunctionInfo objects containing function metadata
        """
        if self._functions is not None:
            return self._functions

        functions = []
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_info = self._extract_function_info(node)
                functions.append(func_info)

        self._functions = functions
        return functions

    def get_loops(self) -> List[LoopInfo]:
        """
        Extract all loop constructs from the code.

        Returns:
            List of LoopInfo objects containing loop metadata
        """
        if self._loops is not None:
            return self._loops

        loops = []
        self._extract_loops_recursive(self.tree, loops, None, 0, False)
        self._loops = loops
        return loops

    def get_imports(self) -> List[ImportInfo]:
        """
        Extract all import statements from the code.

        Returns:
            List of ImportInfo objects containing import metadata
        """
        if self._imports is not None:
            return self._imports

        imports = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    import_info = ImportInfo(
                        module=alias.name,
                        names=[alias.name],
                        line_number=node.lineno,
                        is_from_import=False,
                        aliases={alias.name: alias.asname} if alias.asname else {},
                    )
                    imports.append(import_info)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    aliases = {}
                    names = []
                    for alias in node.names:
                        names.append(alias.name)
                        if alias.asname:
                            aliases[alias.name] = alias.asname
                    import_info = ImportInfo(
                        module=node.module,
                        names=names,
                        line_number=node.lineno,
                        is_from_import=True,
                        aliases=aliases,
                    )
                    imports.append(import_info)

        self._imports = imports
        return imports

    def get_calls(self) -> List[CallInfo]:
        """
        Extract all function calls from the code.

        Returns:
            List of CallInfo objects containing call metadata
        """
        if self._calls is not None:
            return self._calls

        calls = []
        self._extract_calls_recursive(self.tree, calls, None, False, False)
        self._calls = calls
        return calls

    def get_async_functions(self) -> List[FunctionInfo]:
        """
        Get only async function definitions.

        Returns:
            List of FunctionInfo objects for async functions
        """
        return [f for f in self.get_functions() if f.is_async]

    def get_functions_in_range(self, start_line: int, end_line: int) -> List[FunctionInfo]:
        """
        Get functions defined within a specific line range.

        Args:
            start_line: Starting line number (inclusive)
            end_line: Ending line number (inclusive)

        Returns:
            List of FunctionInfo objects within the range
        """
        return [
            f
            for f in self.get_functions()
            if start_line <= f.line_number <= end_line
        ]

    def get_loops_in_function(self, function_name: str) -> List[LoopInfo]:
        """
        Get all loops within a specific function.

        Args:
            function_name: Name of the function

        Returns:
            List of LoopInfo objects within the function
        """
        return [
            loop
            for loop in self.get_loops()
            if loop.parent_function == function_name
        ]

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
                if any(pattern in call.function_name.lower() for pattern in blocking_patterns):
                    # Check if it's not an async version (aiofiles, asyncio.sleep, etc.)
                    if not call.function_name.startswith(("aio", "async")):
                        return True
        return False

    def _extract_function_info(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> FunctionInfo:
        """Extract metadata from a function definition node."""
        parameters = [arg.arg for arg in node.args.args]
        decorators = [self._get_decorator_name(dec) for dec in node.decorator_list]

        return_annotation = None
        if node.returns:
            return_annotation = ast.unparse(node.returns)

        docstring = ast.get_docstring(node)

        return FunctionInfo(
            name=node.name,
            line_number=node.lineno,
            end_line_number=node.end_lineno or node.lineno,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            parameters=parameters,
            decorators=decorators,
            return_annotation=return_annotation,
            docstring=docstring,
        )

    def _get_decorator_name(self, decorator: ast.expr) -> str:
        """Extract the name of a decorator."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Name):
                return decorator.func.id
            elif isinstance(decorator.func, ast.Attribute):
                return ast.unparse(decorator.func)
        elif isinstance(decorator, ast.Attribute):
            return ast.unparse(decorator)
        return ast.unparse(decorator)

    def _extract_loops_recursive(
        self,
        node: ast.AST,
        loops: List[LoopInfo],
        parent_function: Optional[str],
        nesting_level: int,
        is_in_async: bool,
    ) -> None:
        """Recursively extract loop information from AST nodes."""
        # Check if we're entering a function
        current_function = parent_function
        current_is_async = is_in_async

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            current_function = node.name
            current_is_async = isinstance(node, ast.AsyncFunctionDef)

        # Process loops
        if isinstance(node, (ast.For, ast.While, ast.AsyncFor)):
            loop_type = "for" if isinstance(node, (ast.For, ast.AsyncFor)) else "while"
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
            for child in ast.iter_child_nodes(node):
                self._extract_loops_recursive(
                    child, loops, current_function, nesting_level + 1, current_is_async
                )
        else:
            # Continue recursion without increasing nesting
            for child in ast.iter_child_nodes(node):
                self._extract_loops_recursive(
                    child, loops, current_function, nesting_level, current_is_async
                )

    def _extract_calls_recursive(
        self,
        node: ast.AST,
        calls: List[CallInfo],
        parent_function: Optional[str],
        is_in_loop: bool,
        is_in_async: bool,
    ) -> None:
        """Recursively extract function call information from AST nodes."""
        # Track function context
        current_function = parent_function
        current_is_async = is_in_async

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            current_function = node.name
            current_is_async = isinstance(node, ast.AsyncFunctionDef)

        # Track loop context
        current_in_loop = is_in_loop
        if isinstance(node, (ast.For, ast.While, ast.AsyncFor)):
            current_in_loop = True

        # Extract call information
        if isinstance(node, ast.Call):
            function_name = self._get_call_name(node.func)
            if function_name:
                call_info = CallInfo(
                    function_name=function_name,
                    line_number=node.lineno,
                    parent_function=current_function,
                    is_in_loop=current_in_loop,
                    is_in_async_function=current_is_async,
                )
                calls.append(call_info)

        # Continue recursion
        for child in ast.iter_child_nodes(node):
            self._extract_calls_recursive(
                child, calls, current_function, current_in_loop, current_is_async
            )

    def _get_call_name(self, node: ast.expr) -> Optional[str]:
        """Extract the name of a function being called."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return ast.unparse(node)
        return None

    def get_source_segment(self, line_start: int, line_end: int) -> str:
        """
        Get a segment of the source code.

        Args:
            line_start: Starting line number (1-indexed)
            line_end: Ending line number (1-indexed, inclusive)

        Returns:
            Source code segment as a string
        """
        lines = self.source_code.splitlines()
        return "\n".join(lines[line_start - 1:line_end])
