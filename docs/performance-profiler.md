# Performance Profiler Guide

The Performance Profiler is a semantic Python code analyzer that detects performance anti-patterns using Astroid-based AST analysis.

## Table of Contents

- [Introduction](#introduction)
- [Why Astroid?](#why-astroid)
- [Issue Categories](#issue-categories)
- [Usage](#usage)
- [Output Reference](#output-reference)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

## Introduction

The performance profiler goes beyond simple pattern matching by using **semantic analysis** to understand your code's structure and behavior. Unlike general linters (Pylint, Flake8), it focuses specifically on runtime performance issues that can cause:

- Database query explosions (N+1 queries)
- Event loop blocking in async code
- Memory exhaustion from inefficient data handling
- O(n²) or worse algorithmic complexity

## Why Astroid?

The profiler uses [Astroid](https://github.com/pylint-dev/astroid) rather than Python's built-in `ast` module because Astroid provides:

| Feature | ast module | Astroid |
|---------|------------|---------|
| Type inference | No | Yes |
| Call resolution | No | Yes |
| Cross-module analysis | No | Yes |
| Understand ORM calls | No | Yes |

This means the profiler can detect patterns like "Django ORM query inside a loop" by actually understanding what `User.objects.filter()` is, not just matching string patterns.

## Issue Categories

### N+1 Queries (Severity: HIGH)

**What**: Database queries executed inside loops, causing N+1 round-trips to the database.

**Detection**: The profiler identifies ORM method calls (Django, SQLAlchemy) that occur within loop bodies.

**Problematic Pattern**:
```python
def get_user_posts():
    users = User.objects.all()  # 1 query
    for user in users:
        posts = user.posts.all()  # N queries!
        process(posts)
```

**Solution**:
```python
# Django
users = User.objects.prefetch_related('posts').all()

# SQLAlchemy
users = session.query(User).options(joinedload(User.posts)).all()
```

### Blocking I/O in Async (Severity: CRITICAL)

**What**: Synchronous I/O operations in async functions that block the entire event loop.

**Detection**: Identifies calls to `open()`, `time.sleep()`, `requests.*`, etc. within async function definitions.

**Problematic Pattern**:
```python
async def fetch_data():
    with open('data.json') as f:  # Blocks event loop!
        return json.load(f)
```

**Solution**:
```python
import aiofiles
import asyncio

async def fetch_data():
    async with aiofiles.open('data.json') as f:
        content = await f.read()
        return json.loads(content)
```

**Async Alternatives**:

| Blocking Call | Async Alternative |
|---------------|-------------------|
| `open()` | `aiofiles.open()` |
| `time.sleep()` | `asyncio.sleep()` |
| `requests.get()` | `aiohttp.ClientSession.get()` |
| `urllib.request.urlopen()` | `aiohttp.ClientSession.request()` |

### Inefficient Loops (Severity: MEDIUM)

**What**: Loop patterns that degrade performance as data grows.

**Detection**: String concatenation with `+=` in loops, deeply nested loops (3+ levels).

**Problematic Pattern**:
```python
def build_report(items):
    result = ""
    for item in items:
        result += f"{item.name}: {item.value}\n"  # O(n²) string allocation
    return result
```

**Solution**:
```python
def build_report(items):
    parts = []
    for item in items:
        parts.append(f"{item.name}: {item.value}")
    return "\n".join(parts)  # O(n) total
```

**Deep Nesting**:
```python
# O(n³) - Flagged at nesting level 3+
for i in range(n):
    for j in range(n):
        for k in range(n):  # Consider algorithm optimization
            process(i, j, k)
```

### Memory Inefficiencies (Severity: MEDIUM)

**What**: Operations that load excessive data into memory at once.

**Detection**: Calls to `read()`, `readlines()`, `json.load()`, `pickle.load()` that load entire files.

**Problematic Pattern**:
```python
def process_log(path):
    with open(path) as f:
        lines = f.readlines()  # Loads entire file into memory
    for line in lines:
        process(line)
```

**Solution**:
```python
def process_log(path):
    with open(path) as f:
        for line in f:  # Iterates line-by-line
            process(line)
```

**For Large JSON**:
```python
import ijson

def process_large_json(path):
    with open(path, 'rb') as f:
        for item in ijson.items(f, 'items.item'):
            process(item)
```

## Usage

### Programmatic Usage

```python
from workshop_mcp.performance_profiler import PerformanceChecker

# Analyze a file
checker = PerformanceChecker(file_path="mycode.py")
issues = checker.check_all()

for issue in issues:
    print(f"[{issue.severity.value.upper()}] Line {issue.line_number}")
    print(f"  Category: {issue.category.value}")
    print(f"  {issue.description}")
    print(f"  Suggestion: {issue.suggestion}")
    print()

# Get summary
summary = checker.get_summary()
print(f"Total: {summary['total_issues']} issues")
print(f"Critical: {summary['by_severity']['critical']}")
print(f"High: {summary['by_severity']['high']}")
```

### Analyze Source Code Directly

```python
source = '''
async def bad_example():
    with open('file.txt') as f:
        return f.read()
'''

checker = PerformanceChecker(source_code=source)
issues = checker.check_all()
# Returns: 1 CRITICAL blocking_io_in_async issue
```

### Via MCP Server

```bash
# Start the server
poetry run python -m workshop_mcp.server

# Send JSON-RPC request
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"performance_check","arguments":{"file_path":"src/mycode.py"}}}' | poetry run python -m workshop_mcp.server
```

### Via Qodo Agent

```bash
qodo performance_analysis --set file_path="path/to/code.py"
```

## Output Reference

### PerformanceIssue Structure

```python
@dataclass
class PerformanceIssue:
    category: IssueCategory      # Type of issue
    severity: Severity           # CRITICAL, HIGH, MEDIUM, LOW
    line_number: int             # Start line
    end_line_number: int         # End line
    description: str             # Human-readable description
    suggestion: str              # How to fix
    code_snippet: Optional[str]  # The problematic code
    function_name: Optional[str] # Containing function
```

### Severity Levels

| Level | Priority | Description |
|-------|----------|-------------|
| CRITICAL | Immediate fix | Blocks event loop, causes hangs |
| HIGH | Fix soon | N+1 queries, significant slowdown |
| MEDIUM | Plan to fix | Inefficient patterns, technical debt |
| LOW | Nice to fix | Minor optimizations |

### Issue Categories

| Category | Typical Severity | Description |
|----------|------------------|-------------|
| `blocking_io_in_async` | CRITICAL | Sync I/O in async function |
| `n_plus_one_query` | HIGH | ORM query in loop |
| `inefficient_loop` | MEDIUM | String concat, deep nesting |
| `memory_inefficiency` | MEDIUM | Loading entire files |

### Summary Structure

```json
{
  "total_issues": 5,
  "by_severity": {
    "critical": 1,
    "high": 2,
    "medium": 2,
    "low": 0
  },
  "by_category": {
    "n_plus_one_query": 1,
    "blocking_io_in_async": 1,
    "inefficient_loop": 2,
    "memory_inefficiency": 1,
    "missing_async_opportunity": 0,
    "repeated_computation": 0
  }
}
```

## Examples

### Example 1: Django View with N+1 Query

**Before** (problematic):
```python
def user_dashboard(request):
    users = User.objects.all()
    data = []
    for user in users:
        # N+1: Each iteration queries the database
        orders = user.orders.filter(status='pending')
        data.append({
            'user': user.name,
            'pending_orders': orders.count()
        })
    return JsonResponse({'users': data})
```

**Analysis Output**:
```
[HIGH] Line 6: Potential N+1 query: user.orders.filter called inside a loop
Suggestion: Use select_related() for foreign keys or prefetch_related() for
many-to-many relationships to fetch related objects in a single query
```

**After** (fixed):
```python
from django.db.models import Count, Q

def user_dashboard(request):
    users = User.objects.annotate(
        pending_count=Count('orders', filter=Q(orders__status='pending'))
    )
    data = [
        {'user': user.name, 'pending_orders': user.pending_count}
        for user in users
    ]
    return JsonResponse({'users': data})
```

### Example 2: Async Function with Blocking I/O

**Before** (problematic):
```python
import json

async def load_config():
    with open('config.json') as f:      # Line 4: Blocking!
        config = json.load(f)            # Line 5: Blocking!
    return config
```

**Analysis Output**:
```
[CRITICAL] Line 4: Blocking I/O call 'open' in async function blocks event loop
Suggestion: Replace with aiofiles.open and use await

[MEDIUM] Line 5: Loading entire JSON file with json.load() loads all data into memory
Suggestion: Use ijson for streaming JSON parsing to avoid loading entire file into memory
```

**After** (fixed):
```python
import aiofiles
import json

async def load_config():
    async with aiofiles.open('config.json') as f:
        content = await f.read()
        config = json.loads(content)
    return config
```

### Example 3: Memory-Intensive File Processing

**Before** (problematic):
```python
def analyze_log(log_path):
    with open(log_path) as f:
        lines = f.readlines()  # Loads entire file

    errors = []
    for line in lines:
        if 'ERROR' in line:
            errors.append(line)
    return errors
```

**Analysis Output**:
```
[MEDIUM] Line 3: Reading all lines with readlines() loads entire file into memory
Suggestion: Iterate over the file object directly instead of readlines() to process line-by-line
```

**After** (fixed):
```python
def analyze_log(log_path):
    errors = []
    with open(log_path) as f:
        for line in f:  # Streams line-by-line
            if 'ERROR' in line:
                errors.append(line)
    return errors
```

## Troubleshooting

### "File not found" Error

```
FileNotFoundError: File not found: path/to/code.py
```

**Solution**: Verify the file path is correct and accessible. Use absolute paths when possible.

### "Syntax error" in Analyzed Code

```
SyntaxError: invalid syntax (<unknown>, line 15)
```

**Solution**: The Python file has syntax errors. Fix the syntax before analyzing.

### Astroid Inference Failures

Some ORM patterns may not be detected if Astroid cannot infer the type. This typically happens with:

- Dynamically generated models
- Complex metaclass patterns
- Heavily decorated functions

**Workaround**: The profiler falls back to pattern-matching for common ORM method names (.objects.filter, .query(), etc.)

### False Positives

**Scenario**: `json.load()` flagged but file is small and known to fit in memory.

**Context**: The profiler cannot know file sizes at static analysis time. It flags all potentially memory-intensive operations.

**Approach**: Use the severity as a guide. MEDIUM severity issues like memory inefficiencies are worth reviewing but may be acceptable in your specific context.

### Performance on Large Files

For files with 1000+ lines, analysis may take a few seconds due to AST traversal and type inference.

**Tip**: Analyze specific modules rather than entire codebases at once.
