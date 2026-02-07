"""Core Astroid AST parsing utilities shared across analysis tools."""

from dataclasses import dataclass

import astroid


@dataclass
class FunctionInfo:
    """Information about a function in the code."""

    name: str
    line_number: int
    end_line_number: int
    is_async: bool
    parameters: list[str]
    decorators: list[str]
    return_annotation: str | None
    docstring: str | None
    inferred_types: dict[str, str]  # Parameter name -> inferred type (when available)


@dataclass
class LoopInfo:
    """Information about a loop in the code."""

    type: str  # 'for' or 'while'
    line_number: int
    end_line_number: int
    parent_function: str | None
    nesting_level: int
    is_in_async_function: bool


@dataclass
class ImportInfo:
    """Information about an import statement."""

    module: str
    names: list[str]
    line_number: int
    is_from_import: bool
    aliases: dict[str, str]  # Maps imported name to alias
    resolved_module: str | None  # Fully resolved module path when available


@dataclass
class CallInfo:
    """Information about a function call."""

    function_name: str
    line_number: int
    parent_function: str | None
    is_in_loop: bool
    is_in_async_function: bool
    inferred_callable: str | None  # Fully qualified name when inferred


@dataclass
class ClassInfo:
    """Information about a class definition."""

    name: str
    line_number: int
    end_line_number: int
    bases: list[str]
    methods: list[str]
    decorators: list[str]
    docstring: str | None


def parse_source(source_code: str, file_path: str | None = None) -> astroid.Module:
    """Parse Python source code into an Astroid AST module.

    Args:
        source_code: Python source code as a string.
        file_path: Optional file path for error reporting.

    Returns:
        Parsed Astroid Module node.

    Raises:
        SyntaxError: If the source code contains syntax errors.
    """
    try:
        return astroid.parse(source_code, path=file_path)
    except astroid.AstroidSyntaxError as e:
        raise SyntaxError(str(e)) from e


def extract_functions(tree: astroid.Module) -> list[FunctionInfo]:
    """Extract all function definitions from an Astroid AST.

    Args:
        tree: Parsed Astroid Module node.

    Returns:
        List of FunctionInfo objects containing function metadata.
    """
    functions = []
    for node in tree.nodes_of_class((astroid.FunctionDef, astroid.AsyncFunctionDef)):
        func_info = _extract_function_info(node)
        functions.append(func_info)
    return functions


def extract_classes(tree: astroid.Module) -> list[ClassInfo]:
    """Extract all class definitions from an Astroid AST.

    Args:
        tree: Parsed Astroid Module node.

    Returns:
        List of ClassInfo objects containing class metadata.
    """
    classes = []
    for node in tree.nodes_of_class(astroid.ClassDef):
        class_info = _extract_class_info(node)
        classes.append(class_info)
    return classes


def extract_imports(tree: astroid.Module) -> list[ImportInfo]:
    """Extract all import statements from an Astroid AST.

    Args:
        tree: Parsed Astroid Module node.

    Returns:
        List of ImportInfo objects containing import metadata.
    """
    imports = []

    # Handle regular imports
    for node in tree.nodes_of_class(astroid.Import):
        for name, alias in node.names:
            import_info = ImportInfo(
                module=name,
                names=[name],
                line_number=node.lineno,
                is_from_import=False,
                aliases={name: alias} if alias else {},
                resolved_module=None,
            )
            imports.append(import_info)

    # Handle from imports
    for node in tree.nodes_of_class(astroid.ImportFrom):
        if node.modname:
            aliases = {}
            names = []
            for name, alias in node.names:
                names.append(name)
                if alias:
                    aliases[name] = alias

            import_info = ImportInfo(
                module=node.modname,
                names=names,
                line_number=node.lineno,
                is_from_import=True,
                aliases=aliases,
                resolved_module=None,
            )
            imports.append(import_info)

    return imports


def extract_calls(tree: astroid.Module) -> list[CallInfo]:
    """Extract all function calls from an Astroid AST.

    Args:
        tree: Parsed Astroid Module node.

    Returns:
        List of CallInfo objects containing call metadata.
    """
    calls: list[CallInfo] = []
    _extract_calls_recursive(tree, calls, None, False, False)
    return calls


def get_source_segment(source_code: str, line_start: int, line_end: int) -> str:
    """Get a segment of source code by line numbers.

    Args:
        source_code: Full source code string.
        line_start: Starting line number (1-indexed).
        line_end: Ending line number (1-indexed, inclusive).

    Returns:
        Source code segment as a string.
    """
    lines = source_code.splitlines()
    return "\n".join(lines[line_start - 1 : line_end])


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_function_info(
    node: astroid.FunctionDef | astroid.AsyncFunctionDef,
) -> FunctionInfo:
    """Extract metadata from a function definition node."""
    parameters = [arg.name for arg in node.args.args]
    decorators = (
        [_get_decorator_name(dec) for dec in node.decorators.nodes] if node.decorators else []
    )

    return_annotation = None
    if node.returns:
        return_annotation = node.returns.as_string()

    docstring = node.doc_node.value if node.doc_node else None

    inferred_types = {}
    for arg in node.args.args:
        if hasattr(arg, "annotation") and arg.annotation:
            inferred_types[arg.name] = arg.annotation.as_string()

    return FunctionInfo(
        name=node.name,
        line_number=node.lineno,
        end_line_number=node.end_lineno or node.lineno,
        is_async=isinstance(node, astroid.AsyncFunctionDef),
        parameters=parameters,
        decorators=decorators,
        return_annotation=return_annotation,
        docstring=docstring,
        inferred_types=inferred_types,
    )


def _extract_class_info(node: astroid.ClassDef) -> ClassInfo:
    """Extract metadata from a class definition node."""
    bases = [base.as_string() for base in node.bases]
    methods = [m.name for m in node.mymethods()]
    decorators = (
        [_get_decorator_name(dec) for dec in node.decorators.nodes] if node.decorators else []
    )
    docstring = node.doc_node.value if node.doc_node else None

    return ClassInfo(
        name=node.name,
        line_number=node.lineno,
        end_line_number=node.end_lineno or node.lineno,
        bases=bases,
        methods=methods,
        decorators=decorators,
        docstring=docstring,
    )


def _get_decorator_name(decorator: astroid.NodeNG) -> str:
    """Extract the name of a decorator."""
    if isinstance(decorator, astroid.Name):
        return decorator.name
    elif isinstance(decorator, astroid.Call):
        if isinstance(decorator.func, astroid.Name):
            return decorator.func.name
        elif isinstance(decorator.func, astroid.Attribute):
            return decorator.func.as_string()
    elif isinstance(decorator, astroid.Attribute):
        return decorator.as_string()
    return decorator.as_string()


def _extract_calls_recursive(
    node: astroid.NodeNG,
    calls: list[CallInfo],
    parent_function: str | None,
    is_in_loop: bool,
    is_in_async: bool,
) -> None:
    """Recursively extract function call information from Astroid nodes."""
    current_function = parent_function
    current_is_async = is_in_async

    if isinstance(node, (astroid.FunctionDef, astroid.AsyncFunctionDef)):
        current_function = node.name
        current_is_async = isinstance(node, astroid.AsyncFunctionDef)

    current_in_loop = is_in_loop
    if isinstance(node, (astroid.For, astroid.While)):
        current_in_loop = True

    if isinstance(node, astroid.Call):
        function_name = _get_call_name(node.func)
        if function_name:
            from .inference import infer_callable

            inferred_callable = infer_callable(node.func)

            call_info = CallInfo(
                function_name=function_name,
                line_number=node.lineno,
                parent_function=current_function,
                is_in_loop=current_in_loop,
                is_in_async_function=current_is_async,
                inferred_callable=inferred_callable,
            )
            calls.append(call_info)

    for child in node.get_children():
        _extract_calls_recursive(child, calls, current_function, current_in_loop, current_is_async)


def _get_call_name(node: astroid.NodeNG) -> str | None:
    """Extract the name of a function being called."""
    if isinstance(node, astroid.Name):
        return node.name
    elif isinstance(node, astroid.Attribute):
        return node.as_string()
    return None
