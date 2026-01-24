"""Performance anti-pattern definitions and detection rules."""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class Severity(Enum):
    """Severity levels for performance issues."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueCategory(Enum):
    """Categories of performance issues."""

    N_PLUS_ONE_QUERY = "n_plus_one_query"
    INEFFICIENT_LOOP = "inefficient_loop"
    MEMORY_INEFFICIENCY = "memory_inefficiency"
    BLOCKING_IO_IN_ASYNC = "blocking_io_in_async"
    MISSING_ASYNC_OPPORTUNITY = "missing_async_opportunity"
    REPEATED_COMPUTATION = "repeated_computation"


@dataclass
class PerformanceIssue:
    """Represents a detected performance issue."""

    category: IssueCategory
    severity: Severity
    line_number: int
    end_line_number: int
    description: str
    suggestion: str
    code_snippet: Optional[str] = None
    function_name: Optional[str] = None


# ORM patterns that indicate database queries
ORM_QUERY_PATTERNS = {
    # Django ORM
    "django": [
        ".objects.all",
        ".objects.filter",
        ".objects.get",
        ".objects.exclude",
        ".objects.select_related",
        ".objects.prefetch_related",
    ],
    # SQLAlchemy
    "sqlalchemy": [
        ".query(",
        ".filter(",
        ".filter_by(",
        ".all()",
        ".first()",
        ".one()",
        "session.query",
    ],
    # Generic
    "generic": [
        ".execute(",
        ".fetchall(",
        ".fetchone(",
    ],
}

# Patterns for lazy-loaded relationships (trigger additional queries)
LAZY_LOAD_PATTERNS = {
    "django": [
        # Accessing related objects without select_related/prefetch_related
        # We'll detect these by checking attribute access in loops
    ],
}

# Blocking I/O functions that shouldn't be in async code
BLOCKING_IO_FUNCTIONS = {
    "builtins.open",
    "open",
    "io.open",
    "os.read",
    "os.write",
    "time.sleep",
    "requests.get",
    "requests.post",
    "requests.put",
    "requests.delete",
    "urllib.request.urlopen",
}

# Async-safe alternatives
ASYNC_ALTERNATIVES = {
    "open": "aiofiles.open",
    "builtins.open": "aiofiles.open",
    "time.sleep": "asyncio.sleep",
    "requests.get": "aiohttp.ClientSession.get",
    "requests.post": "aiohttp.ClientSession.post",
    "urllib.request.urlopen": "aiohttp.ClientSession.request",
}

# String operations that are inefficient in loops
INEFFICIENT_STRING_OPERATIONS = {
    "str.__add__",  # String concatenation with +
    "str.format",  # Repeated format calls
}

# Memory-intensive operations
MEMORY_INTENSIVE_OPERATIONS = {
    "read",  # Reading entire file
    "readlines",  # Reading all lines
    "json.load",  # Loading entire JSON
    "pickle.load",  # Loading entire pickle
}

# Indicators of unbounded list growth
LIST_GROWTH_INDICATORS = {
    "list.append",
    "list.extend",
    "list.insert",
}


def get_orm_type(inferred_callable: Optional[str]) -> Optional[str]:
    """
    Determine which ORM framework is being used based on the callable.

    Args:
        inferred_callable: Fully qualified name of the callable

    Returns:
        ORM type ('django', 'sqlalchemy', or None)
    """
    if not inferred_callable:
        return None

    inferred_lower = inferred_callable.lower()

    if "django" in inferred_lower or "models." in inferred_lower or ".objects." in inferred_lower:
        return "django"
    elif "sqlalchemy" in inferred_lower or "session.query" in inferred_lower:
        return "sqlalchemy"

    return None


def get_orm_type_from_function_name(function_name: str) -> Optional[str]:
    """
    Try to determine ORM type from function name alone (less reliable).

    Args:
        function_name: Name of the function being called

    Returns:
        ORM type ('django', 'sqlalchemy', or None)
    """
    if ".objects." in function_name or "objects.all" in function_name or "objects.filter" in function_name:
        return "django"
    elif "session.query" in function_name or ".query(" in function_name:
        return "sqlalchemy"

    return None


def is_orm_query(function_name: str, inferred_callable: Optional[str]) -> bool:
    """
    Check if a function call is likely an ORM query.

    Args:
        function_name: Name of the function being called
        inferred_callable: Fully qualified name when available

    Returns:
        True if it's likely an ORM query
    """
    # Check inferred callable first (more reliable)
    orm_type = get_orm_type(inferred_callable)
    if orm_type:
        patterns = ORM_QUERY_PATTERNS.get(orm_type, [])
        if any(pattern in inferred_callable for pattern in patterns):
            return True

    # Fallback to function name pattern matching
    for patterns in ORM_QUERY_PATTERNS.values():
        if any(pattern in function_name for pattern in patterns):
            return True

    # Additional heuristic checks for common ORM patterns
    # Django: anything with .objects. or .all() or .filter() etc
    if ".objects." in function_name or "objects.all" in function_name or "objects.filter" in function_name:
        return True

    # Check for attribute access patterns like .all(), .filter(), .get()
    if function_name.endswith((".all", ".filter", ".get", ".first", ".one")):
        return True

    return False


def is_blocking_io(function_name: str, inferred_callable: Optional[str]) -> bool:
    """
    Check if a function call is blocking I/O.

    Args:
        function_name: Name of the function being called
        inferred_callable: Fully qualified name when available

    Returns:
        True if it's blocking I/O
    """
    # Check inferred callable (most reliable)
    if inferred_callable and inferred_callable in BLOCKING_IO_FUNCTIONS:
        return True

    # Check function name
    if function_name in BLOCKING_IO_FUNCTIONS:
        return True

    # Check if it's a requests or urllib call
    if any(
        lib in function_name.lower()
        for lib in ["requests.", "urllib.request"]
    ):
        return True

    return False


def get_async_alternative(function_name: str, inferred_callable: Optional[str]) -> Optional[str]:
    """
    Get the async alternative for a blocking I/O function.

    Args:
        function_name: Name of the blocking function
        inferred_callable: Fully qualified name when available

    Returns:
        Suggested async alternative, or None
    """
    # Try inferred callable first
    if inferred_callable and inferred_callable in ASYNC_ALTERNATIVES:
        return ASYNC_ALTERNATIVES[inferred_callable]

    # Try function name
    if function_name in ASYNC_ALTERNATIVES:
        return ASYNC_ALTERNATIVES[function_name]

    # Generic suggestions based on library
    if "requests" in function_name.lower():
        return "aiohttp.ClientSession"

    if "urllib" in function_name.lower():
        return "aiohttp.ClientSession"

    return None


def is_inefficient_string_op(function_name: str, inferred_callable: Optional[str]) -> bool:
    """
    Check if a function call is an inefficient string operation.

    Args:
        function_name: Name of the function being called
        inferred_callable: Fully qualified name when available

    Returns:
        True if it's an inefficient string operation
    """
    if inferred_callable and inferred_callable in INEFFICIENT_STRING_OPERATIONS:
        return True

    # Check for string concatenation pattern
    if function_name == "__add__" or function_name.endswith(".__add__"):
        return True

    return False
