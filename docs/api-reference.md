# API Reference

This document provides detailed API documentation for the Performance Profiler module.

## Table of Contents

- [PerformanceChecker](#performancechecker)
- [ASTAnalyzer](#astanalyzer)
- [Data Classes](#data-classes)
- [Enums](#enums)
- [Pattern Functions](#pattern-functions)

---

## PerformanceChecker

**Module**: `workshop_mcp.performance_profiler.performance_checker`

The main class for analyzing Python code for performance anti-patterns.

### Constructor

```python
PerformanceChecker(source_code: Optional[str] = None, file_path: Optional[str] = None)
```

**Parameters**:
- `source_code` - Python source code as a string
- `file_path` - Path to a Python file to analyze

**Raises**:
- `ValueError` - If neither source_code nor file_path is provided
- `SyntaxError` - If the source code has syntax errors
- `FileNotFoundError` - If file_path doesn't exist

**Example**:
```python
# From file
checker = PerformanceChecker(file_path="mycode.py")

# From source
checker = PerformanceChecker(source_code="def foo(): pass")
```

### Methods

#### check_all

```python
check_all() -> List[PerformanceIssue]
```

Run all performance checks on the code.

**Returns**: List of detected performance issues, sorted by severity (critical first) then line number.

**Example**:
```python
issues = checker.check_all()
for issue in issues:
    print(f"{issue.severity}: {issue.description}")
```

---

#### check_n_plus_one_queries

```python
check_n_plus_one_queries() -> List[PerformanceIssue]
```

Detect N+1 query anti-patterns where database queries are executed inside loops.

**Returns**: List of N+1 query issues (severity: HIGH)

---

#### check_blocking_io_in_async

```python
check_blocking_io_in_async() -> List[PerformanceIssue]
```

Detect blocking I/O operations in async functions that would block the event loop.

**Returns**: List of blocking I/O issues (severity: CRITICAL)

---

#### check_inefficient_loops

```python
check_inefficient_loops() -> List[PerformanceIssue]
```

Detect inefficient patterns in loops:
- String concatenation with `+=`
- Deeply nested loops (3+ levels)

**Returns**: List of inefficient loop issues (severity: MEDIUM)

---

#### check_memory_inefficiencies

```python
check_memory_inefficiencies() -> List[PerformanceIssue]
```

Detect memory inefficiency patterns:
- `read()` / `readlines()` - Loading entire files
- `json.load()` / `pickle.load()` - Loading entire data structures

**Returns**: List of memory inefficiency issues (severity: MEDIUM)

---

#### get_issues_by_severity

```python
get_issues_by_severity(severity: Severity) -> List[PerformanceIssue]
```

Filter issues by severity level.

**Parameters**:
- `severity` - Severity level to filter by

**Example**:
```python
critical = checker.get_issues_by_severity(Severity.CRITICAL)
```

---

#### get_issues_by_category

```python
get_issues_by_category(category: IssueCategory) -> List[PerformanceIssue]
```

Filter issues by category.

**Parameters**:
- `category` - Issue category to filter by

**Example**:
```python
n_plus_one = checker.get_issues_by_category(IssueCategory.N_PLUS_ONE_QUERY)
```

---

#### get_critical_issues

```python
get_critical_issues() -> List[PerformanceIssue]
```

Convenience method to get all CRITICAL severity issues.

**Returns**: List of critical issues

---

#### has_issues

```python
has_issues() -> bool
```

Check if any performance issues were found.

**Returns**: `True` if issues were found, `False` otherwise

---

#### get_summary

```python
get_summary() -> dict
```

Get a summary of all detected issues.

**Returns**: Dictionary with structure:
```python
{
    "total_issues": int,
    "by_severity": {
        "critical": int,
        "high": int,
        "medium": int,
        "low": int
    },
    "by_category": {
        "n_plus_one_query": int,
        "blocking_io_in_async": int,
        "inefficient_loop": int,
        "memory_inefficiency": int,
        "missing_async_opportunity": int,
        "repeated_computation": int
    }
}
```

---

## ASTAnalyzer

**Module**: `workshop_mcp.performance_profiler.ast_analyzer`

Low-level AST analysis using Astroid for semantic understanding of Python code.

### Constructor

```python
ASTAnalyzer(source_code: Optional[str] = None, file_path: Optional[str] = None)
```

**Parameters**:
- `source_code` - Python source code as a string
- `file_path` - Path to a Python file to analyze

**Raises**:
- `ValueError` - If neither source_code nor file_path is provided
- `SyntaxError` - If the source code has syntax errors
- `FileNotFoundError` - If file_path doesn't exist

### Methods

#### get_functions

```python
get_functions() -> List[FunctionInfo]
```

Extract all function definitions from the code.

**Returns**: List of `FunctionInfo` objects

---

#### get_async_functions

```python
get_async_functions() -> List[FunctionInfo]
```

Get only async function definitions.

**Returns**: List of `FunctionInfo` objects where `is_async=True`

---

#### get_functions_in_range

```python
get_functions_in_range(start_line: int, end_line: int) -> List[FunctionInfo]
```

Get functions defined within a specific line range.

**Parameters**:
- `start_line` - Starting line number (inclusive)
- `end_line` - Ending line number (inclusive)

---

#### get_loops

```python
get_loops() -> List[LoopInfo]
```

Extract all loop constructs (for/while) from the code.

**Returns**: List of `LoopInfo` objects

---

#### get_loops_in_function

```python
get_loops_in_function(function_name: str) -> List[LoopInfo]
```

Get all loops within a specific function.

**Parameters**:
- `function_name` - Name of the function

---

#### get_max_loop_nesting_depth

```python
get_max_loop_nesting_depth() -> int
```

Get the maximum nesting depth of loops in the code.

**Returns**: Maximum nesting level (0 if no loops)

---

#### get_imports

```python
get_imports() -> List[ImportInfo]
```

Extract all import statements from the code.

**Returns**: List of `ImportInfo` objects

---

#### get_calls

```python
get_calls() -> List[CallInfo]
```

Extract all function calls from the code.

**Returns**: List of `CallInfo` objects with context about where calls occur

---

#### has_blocking_calls_in_async

```python
has_blocking_calls_in_async() -> bool
```

Quick check if there are potentially blocking calls in async functions.

**Returns**: `True` if blocking calls are found

---

#### get_source_segment

```python
get_source_segment(line_start: int, line_end: int) -> str
```

Get a segment of the source code.

**Parameters**:
- `line_start` - Starting line number (1-indexed)
- `line_end` - Ending line number (1-indexed, inclusive)

**Returns**: Source code segment as a string

---

## Data Classes

### PerformanceIssue

**Module**: `workshop_mcp.performance_profiler.patterns`

Represents a detected performance issue.

```python
@dataclass
class PerformanceIssue:
    category: IssueCategory
    severity: Severity
    line_number: int
    end_line_number: int
    description: str
    suggestion: str
    code_snippet: Optional[str] = None
    function_name: Optional[str] = None
```

**Fields**:
- `category` - Type of performance issue
- `severity` - How critical the issue is
- `line_number` - Start line of the issue
- `end_line_number` - End line of the issue
- `description` - Human-readable description
- `suggestion` - How to fix the issue
- `code_snippet` - The problematic code (optional)
- `function_name` - Containing function name (optional)

---

### FunctionInfo

**Module**: `workshop_mcp.performance_profiler.ast_analyzer`

Information about a function definition.

```python
@dataclass
class FunctionInfo:
    name: str
    line_number: int
    end_line_number: int
    is_async: bool
    parameters: List[str]
    decorators: List[str]
    return_annotation: Optional[str]
    docstring: Optional[str]
    inferred_types: Dict[str, str]
```

---

### LoopInfo

**Module**: `workshop_mcp.performance_profiler.ast_analyzer`

Information about a loop construct.

```python
@dataclass
class LoopInfo:
    type: str  # 'for' or 'while'
    line_number: int
    end_line_number: int
    parent_function: Optional[str]
    nesting_level: int
    is_in_async_function: bool
```

---

### ImportInfo

**Module**: `workshop_mcp.performance_profiler.ast_analyzer`

Information about an import statement.

```python
@dataclass
class ImportInfo:
    module: str
    names: List[str]
    line_number: int
    is_from_import: bool
    aliases: Dict[str, str]
    resolved_module: Optional[str]
```

---

### CallInfo

**Module**: `workshop_mcp.performance_profiler.ast_analyzer`

Information about a function call.

```python
@dataclass
class CallInfo:
    function_name: str
    line_number: int
    parent_function: Optional[str]
    is_in_loop: bool
    is_in_async_function: bool
    inferred_callable: Optional[str]
```

**Fields**:
- `function_name` - Name as it appears in code
- `inferred_callable` - Fully qualified name when Astroid can resolve it

---

## Enums

### Severity

**Module**: `workshop_mcp.performance_profiler.patterns`

```python
class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
```

---

### IssueCategory

**Module**: `workshop_mcp.performance_profiler.patterns`

```python
class IssueCategory(Enum):
    N_PLUS_ONE_QUERY = "n_plus_one_query"
    INEFFICIENT_LOOP = "inefficient_loop"
    MEMORY_INEFFICIENCY = "memory_inefficiency"
    BLOCKING_IO_IN_ASYNC = "blocking_io_in_async"
    MISSING_ASYNC_OPPORTUNITY = "missing_async_opportunity"
    REPEATED_COMPUTATION = "repeated_computation"
```

---

## Pattern Functions

**Module**: `workshop_mcp.performance_profiler.patterns`

Helper functions for pattern detection.

### is_orm_query

```python
is_orm_query(function_name: str, inferred_callable: Optional[str]) -> bool
```

Check if a function call is likely an ORM query (Django or SQLAlchemy).

---

### get_orm_type

```python
get_orm_type(inferred_callable: Optional[str]) -> Optional[str]
```

Determine which ORM framework is being used.

**Returns**: `'django'`, `'sqlalchemy'`, or `None`

---

### is_blocking_io

```python
is_blocking_io(function_name: str, inferred_callable: Optional[str]) -> bool
```

Check if a function call is blocking I/O.

---

### get_async_alternative

```python
get_async_alternative(function_name: str, inferred_callable: Optional[str]) -> Optional[str]
```

Get the async alternative for a blocking I/O function.

---

### is_memory_intensive

```python
is_memory_intensive(function_name: str, inferred_callable: Optional[str]) -> bool
```

Check if a function call is memory-intensive.

---

### get_memory_optimization_suggestion

```python
get_memory_optimization_suggestion(function_name: str, inferred_callable: Optional[str]) -> str
```

Get optimization suggestion for a memory-intensive operation.
