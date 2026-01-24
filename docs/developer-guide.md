# Developer Guide

This guide covers setting up a development environment, understanding the architecture, and contributing to the project.

## Table of Contents

- [Development Environment Setup](#development-environment-setup)
- [Architecture Overview](#architecture-overview)
- [Adding New Performance Checks](#adding-new-performance-checks)
- [Testing Guidelines](#testing-guidelines)
- [Code Style](#code-style)
- [Pull Request Process](#pull-request-process)

## Development Environment Setup

### Prerequisites

- Python 3.11+
- Poetry (dependency management)
- Git

### Initial Setup

```bash
# Clone the repository
git clone <repository-url>
cd python-mcp-agent-workshop

# Install dependencies
poetry install

# Verify installation
python verification.py

# Run tests to confirm setup
poetry run pytest
```

### IDE Configuration

#### VS Code

Recommended extensions:
- Python (Microsoft)
- Pylance (type checking)
- Black Formatter

Settings (`.vscode/settings.json`):
```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests"],
    "editor.formatOnSave": true,
    "[python]": {
        "editor.defaultFormatter": "ms-python.black-formatter"
    }
}
```

#### PyCharm

1. Open project, select Poetry interpreter
2. Mark `src/` as Sources Root
3. Mark `tests/` as Tests Root
4. Enable pytest as test runner

## Architecture Overview

### Module Structure

```
src/workshop_mcp/
├── __init__.py
├── server.py                    # MCP server (JSON-RPC over stdio)
├── keyword_search.py            # Keyword search tool
└── performance_profiler/        # Performance analysis module
    ├── __init__.py              # Public exports
    ├── ast_analyzer.py          # Astroid-based AST analysis
    ├── patterns.py              # Anti-pattern definitions
    └── performance_checker.py   # Issue detection engine
```

### Why Astroid?

The performance profiler uses [Astroid](https://pylint-dev.github.io/astroid/) instead of Python's built-in `ast` module because:

1. **Type Inference**: Astroid can infer what type a variable holds
2. **Call Resolution**: It resolves what function is actually being called
3. **Semantic Understanding**: It understands imports, method resolution, etc.

Example of Astroid's power:
```python
# With ast: We see a call to "filter"
# With Astroid: We know it's "django.db.models.QuerySet.filter"
users = User.objects.filter(active=True)
```

### Data Flow

```
Source Code (file or string)
        │
        ▼
┌─────────────────────┐
│    ASTAnalyzer      │ ← Parses code with Astroid
│  - get_functions()  │ ← Extracts function metadata
│  - get_loops()      │ ← Finds loop structures
│  - get_calls()      │ ← Identifies all function calls
└─────────────────────┘
        │
        ▼
┌─────────────────────┐
│ PerformanceChecker  │ ← Uses ASTAnalyzer data
│  - check_all()      │ ← Runs all pattern checks
│  - check_n_plus_one │ ← ORM calls in loops
│  - check_blocking   │ ← Sync I/O in async
│  - check_loops      │ ← Inefficient patterns
│  - check_memory     │ ← Memory hogs
└─────────────────────┘
        │
        ▼
┌─────────────────────┐
│ List[Performance-   │
│      Issue]         │ ← Sorted by severity
└─────────────────────┘
```

### Pattern Detection

Patterns are defined in `patterns.py`:

```python
# ORM query patterns
ORM_QUERY_PATTERNS = {
    "django": [".objects.all", ".objects.filter", ...],
    "sqlalchemy": [".query(", ".filter(", ...],
}

# Blocking I/O functions
BLOCKING_IO_FUNCTIONS = {
    "builtins.open", "time.sleep", "requests.get", ...
}
```

The checker uses these patterns combined with Astroid's type inference to detect issues.

## Adding New Performance Checks

### Step 1: Define the Pattern

Add pattern definitions to `patterns.py`:

```python
# Example: Detecting expensive regex compilation in loops
EXPENSIVE_REGEX_FUNCTIONS = {
    "re.compile",
    "re.match",
    "re.search",
}

def is_expensive_regex(function_name: str, inferred_callable: Optional[str]) -> bool:
    """Check if a function call compiles regex."""
    if inferred_callable in EXPENSIVE_REGEX_FUNCTIONS:
        return True
    return function_name in EXPENSIVE_REGEX_FUNCTIONS
```

### Step 2: Add Detection Logic

Add a new check method to `PerformanceChecker`:

```python
def check_regex_in_loops(self) -> List[PerformanceIssue]:
    """
    Detect regex compilation inside loops.

    Compiling regex in a loop is wasteful; compile once outside.
    """
    issues = []
    calls = self.analyzer.get_calls()

    for call in calls:
        if call.is_in_loop and is_expensive_regex(
            call.function_name, call.inferred_callable
        ):
            code_snippet = self.analyzer.get_source_segment(
                call.line_number, call.line_number
            )

            issue = PerformanceIssue(
                category=IssueCategory.REPEATED_COMPUTATION,
                severity=Severity.MEDIUM,
                line_number=call.line_number,
                end_line_number=call.line_number,
                description=f"Regex compilation '{call.function_name}' inside loop",
                suggestion="Compile regex once outside the loop and reuse the pattern object",
                code_snippet=code_snippet,
                function_name=call.parent_function,
            )
            issues.append(issue)

    return issues
```

### Step 3: Wire Up in check_all()

Add your new check to the `check_all()` method:

```python
def check_all(self) -> List[PerformanceIssue]:
    issues = []
    issues.extend(self.check_n_plus_one_queries())
    issues.extend(self.check_blocking_io_in_async())
    issues.extend(self.check_inefficient_loops())
    issues.extend(self.check_memory_inefficiencies())
    issues.extend(self.check_regex_in_loops())  # Add new check
    # ... sorting logic
    return issues
```

### Step 4: Write Tests

Add tests to `tests/test_performance_checker.py`:

```python
def test_detects_regex_compile_in_loop():
    """Test detection of regex compilation in loops."""
    source = '''
def process_items(items):
    for item in items:
        pattern = re.compile(r"\\d+")
        if pattern.match(item):
            yield item
'''
    checker = PerformanceChecker(source_code=source)
    issues = checker.check_all()

    assert len(issues) == 1
    assert issues[0].category == IssueCategory.REPEATED_COMPUTATION
    assert "regex" in issues[0].description.lower()


def test_no_issue_for_regex_outside_loop():
    """Test that regex compilation outside loops is not flagged."""
    source = '''
def process_items(items):
    pattern = re.compile(r"\\d+")
    for item in items:
        if pattern.match(item):
            yield item
'''
    checker = PerformanceChecker(source_code=source)
    issues = checker.check_regex_in_loops()

    assert len(issues) == 0
```

### Step 5: Update Documentation

- Add the new check to `docs/performance-profiler.md`
- Update `docs/api-reference.md` with new method
- Add example in README if it's a common pattern

## Testing Guidelines

### Test-Driven Development

We follow TDD:
1. Write a failing test first
2. Implement the minimum code to pass
3. Refactor while keeping tests green

### Test Structure

```python
def test_<what>_<condition>():
    """Clear description of what is being tested."""
    # Arrange
    source = '''
    # Code to analyze
    '''

    # Act
    checker = PerformanceChecker(source_code=source)
    issues = checker.check_specific_thing()

    # Assert
    assert len(issues) == expected_count
    assert issues[0].severity == expected_severity
```

### Running Tests

```bash
# All tests
poetry run pytest

# Specific file
poetry run pytest tests/test_performance_checker.py

# Specific test
poetry run pytest tests/test_performance_checker.py::test_detects_n_plus_one

# With coverage
poetry run pytest --cov=workshop_mcp --cov-report=html

# Verbose output
poetry run pytest -v -s
```

### Test Categories

| File | Coverage |
|------|----------|
| `test_ast_analyzer.py` | AST extraction, function/loop/call info |
| `test_performance_checker.py` | Pattern detection, issue generation |
| `test_mcp_server_integration.py` | Tool registration, JSON-RPC handling |
| `test_mcp_server_protocol.py` | Message framing, protocol compliance |
| `test_e2e_workflow.py` | Complete workflow validation |
| `test_agent_config.py` | TOML validation, schema verification |

### Writing Good Tests

- **One assertion concept per test** (multiple asserts OK if related)
- **Descriptive names**: `test_detects_blocking_open_in_async_function`
- **Isolated**: Tests should not depend on each other
- **Fast**: Avoid file I/O; use source_code parameter
- **Edge cases**: Empty code, syntax errors, no issues found

## Code Style

### Formatting

We use Black for formatting:

```bash
poetry run black src/ tests/
```

### Import Sorting

We use isort:

```bash
poetry run isort src/ tests/
```

### Type Hints

All public functions must have type hints:

```python
def get_issues_by_severity(self, severity: Severity) -> List[PerformanceIssue]:
    """Get issues filtered by severity level."""
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def check_n_plus_one_queries(self) -> List[PerformanceIssue]:
    """
    Detect N+1 query anti-patterns.

    This occurs when code iterates over a collection and makes a database
    query for each item instead of fetching all data at once.

    Returns:
        List of N+1 query issues with HIGH severity.
    """
```

## Pull Request Process

### Before Submitting

1. **Run all tests**: `poetry run pytest`
2. **Format code**: `poetry run black src/ tests/`
3. **Check types**: `poetry run mypy src/` (if configured)
4. **Update docs** if adding features

### PR Checklist

- [ ] Tests pass locally
- [ ] New code has tests
- [ ] Type hints added
- [ ] Docstrings added
- [ ] Documentation updated
- [ ] Commit messages are clear

### Commit Message Format

```
type: short description

Longer description if needed.

Co-Authored-By: Your Name <email>
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

Examples:
```
feat: add regex-in-loop detection to performance checker

fix: handle empty source code gracefully in ASTAnalyzer

refactor: extract ORM detection logic to patterns module

test: add edge case tests for blocking I/O detection
```

### Review Process

1. Create PR with clear description
2. Automated tests run (if CI configured)
3. Code review by maintainer
4. Address feedback
5. Squash and merge when approved
