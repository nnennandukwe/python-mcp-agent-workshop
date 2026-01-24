# Documentation Plan for Performance Profiler Agent

## Overview

This document outlines the plan for comprehensive documentation of the performance profiler agent, including README updates, usage examples, and developer guides.

## Objectives

1. Update main README with performance profiler information
2. Create detailed usage examples and tutorials
3. Document the architecture and design decisions
4. Provide troubleshooting guide
5. Create API reference documentation
6. Document testing procedures

## Documentation Structure

### 1. Main README Updates

**File**: `README.md`

**Sections to Add/Update**:

#### A. Project Description
- Update to mention dual-agent system (keyword search + performance profiler)
- Highlight performance profiler as the primary showcase agent
- Brief mention of Astroid-powered semantic analysis

#### B. Features Section
Add performance profiler capabilities:
- N+1 Query Detection (Django, SQLAlchemy)
- Blocking I/O in Async Functions
- Inefficient Loop Patterns
- Memory Inefficiency Detection

#### C. Installation Section
- Verify Poetry installation instructions are current
- Confirm dependency list includes Astroid
- Add any new dependencies

#### D. Quick Start Guide
Add performance profiler example:
```bash
# Start the MCP server
poetry run python -m workshop_mcp.server

# Test with sample request
echo '{"jsonrpc":"2.0","id":1,"method":"call_tool","params":{"name":"performance_check","arguments":{"file_path":"path/to/code.py"}}}' | poetry run python -m workshop_mcp.server
```

#### E. Agent Configuration
Document both agents:
- `agents/keyword_analysis.toml` - Keyword search agent
- `agents/performance_profiler.toml` - Performance analysis agent

#### F. Usage Examples
Add comprehensive examples for:
- Analyzing a single file
- Using source_code parameter
- Interpreting results
- Understanding severity levels
- Acting on suggestions

#### G. Architecture Section (NEW)
High-level overview:
- MCP Server (JSON-RPC 2.0 over stdio)
- Performance Profiler Module
- Astroid AST Analysis
- Pattern Detection Engine
- Agent Integration Layer

#### H. Testing Section
- How to run tests: `poetry run pytest`
- Test coverage: 102 tests
- How to add new tests

#### I. Contributing Section
- Code style guidelines
- Test requirements (test-driven development)
- PR process
- Code review expectations

#### J. License Section
- Ensure license is specified

### 2. Performance Profiler Documentation

**File**: `docs/performance-profiler.md` (NEW)

**Contents**:

#### Introduction
- What is the performance profiler?
- Why use semantic analysis (Astroid)?
- Comparison with general linters (Pylint, Flake8)

#### Architecture
- Component diagram
- Data flow from source code to issues
- AST Analyzer role
- Performance Checker role
- Pattern definitions

#### Issue Categories

**N+1 Queries**
- What are N+1 queries?
- How we detect them (ORM patterns in loops)
- Django examples
- SQLAlchemy examples
- How to fix them (select_related, prefetch_related, joinedload)

**Blocking I/O in Async**
- Why blocking I/O is problematic in async functions
- Detected patterns (open, time.sleep, requests)
- Async alternatives (aiofiles, asyncio.sleep, aiohttp)
- Real-world impact examples

**Inefficient Loops**
- String concatenation anti-pattern
- Deep nesting concerns
- Solutions (list comprehensions, join, generators)

**Memory Inefficiencies**
- Loading entire files into memory
- json.load and pickle.load issues
- Streaming alternatives (ijson, line-by-line reading)
- When these patterns are actually okay

#### Usage Guide

**Basic Usage**
```python
from workshop_mcp.performance_profiler import PerformanceChecker

checker = PerformanceChecker(file_path="code.py")
issues = checker.check_all()

for issue in issues:
    print(f"{issue.severity}: {issue.description} at line {issue.line_number}")
```

**Via MCP Server**
JSON-RPC request/response examples

**Via Agent**
How to invoke the agent with Gemini 2.5 Pro

#### Configuration

**Agent Configuration Explained**
- TOML structure
- Instructions customization
- Output schema format
- Execution strategy options

#### Output Reference

**Issue Object Structure**
```json
{
  "category": "n_plus_one_query",
  "severity": "high",
  "line_number": 42,
  "end_line_number": 45,
  "description": "...",
  "suggestion": "...",
  "code_snippet": "...",
  "function_name": "get_users"
}
```

**Summary Object Structure**
```json
{
  "total_issues": 5,
  "by_severity": {
    "critical": 2,
    "high": 2,
    "medium": 1,
    "low": 0
  },
  "by_category": {
    "n_plus_one_query": 1,
    "blocking_io_in_async": 2,
    "inefficient_loop": 1,
    "memory_inefficiency": 1
  }
}
```

#### Examples

**Example 1: Django View with N+1 Query**
- Show problematic code
- Show analysis output
- Show fixed code
- Explain the improvement

**Example 2: Async Function with Blocking I/O**
- Show problematic code
- Show analysis output
- Show fixed code with async alternatives
- Performance comparison

**Example 3: Memory-Intensive File Processing**
- Show problematic code
- Show analysis output
- Show streaming solution
- Memory usage comparison

#### Troubleshooting

Common issues and solutions:
- "File not found" errors
- "Syntax error" in analyzed code
- Astroid inference failures
- False positives and how to handle them
- Performance of analysis on large files

### 3. API Reference Documentation

**File**: `docs/api-reference.md` (NEW)

**Contents**:

#### ASTAnalyzer

**Class**: `workshop_mcp.performance_profiler.ast_analyzer.ASTAnalyzer`

Methods:
- `__init__(source_code=None, file_path=None)`
- `get_functions() -> List[FunctionInfo]`
- `get_loops() -> List[LoopInfo]`
- `get_imports() -> List[ImportInfo]`
- `get_calls() -> List[CallInfo]`
- `get_source_segment(start_line, end_line) -> str`

Data classes:
- `FunctionInfo`
- `LoopInfo`
- `ImportInfo`
- `CallInfo`

#### PerformanceChecker

**Class**: `workshop_mcp.performance_profiler.performance_checker.PerformanceChecker`

Methods:
- `__init__(source_code=None, file_path=None)`
- `check_all() -> List[PerformanceIssue]`
- `check_n_plus_one_queries() -> List[PerformanceIssue]`
- `check_blocking_io_in_async() -> List[PerformanceIssue]`
- `check_inefficient_loops() -> List[PerformanceIssue]`
- `check_memory_inefficiencies() -> List[PerformanceIssue]`
- `get_issues_by_severity(severity: Severity) -> List[PerformanceIssue]`
- `get_issues_by_category(category: IssueCategory) -> List[PerformanceIssue]`
- `get_critical_issues() -> List[PerformanceIssue]`
- `has_issues() -> bool`
- `get_summary() -> Dict[str, Any]`

#### Patterns Module

**Module**: `workshop_mcp.performance_profiler.patterns`

Enums:
- `IssueCategory`
- `Severity`

Data class:
- `PerformanceIssue`

Functions:
- `is_orm_query(function_name, inferred_callable) -> bool`
- `get_orm_type(function_name, inferred_callable) -> Optional[str]`
- `is_blocking_io(function_name, inferred_callable) -> bool`
- `get_async_alternative(function_name) -> Optional[str]`
- `is_memory_intensive(function_name, inferred_callable) -> bool`
- `get_memory_optimization_suggestion(function_name, inferred_callable) -> str`

### 4. Developer Guide

**File**: `docs/developer-guide.md` (NEW)

**Contents**:

#### Setting Up Development Environment
- Clone repository
- Install dependencies with Poetry
- Run tests to verify setup
- IDE configuration (VS Code, PyCharm)

#### Architecture Deep Dive
- Why Astroid over stdlib ast?
- Design patterns used
- Module organization
- Extension points

#### Adding New Performance Checks

Step-by-step guide:
1. Define pattern in `patterns.py`
2. Add detection logic in `performance_checker.py`
3. Write tests in `tests/test_performance_checker.py`
4. Update documentation

Example: Adding "Redundant Database Call" check

#### Testing Guidelines
- Test-driven development approach
- Test structure and organization
- Using fixtures
- Mocking external dependencies
- Coverage expectations

#### Code Review Process
- Qodo code review integration
- Addressing review feedback
- PR checklist

#### Versioning and Releases
- Semantic versioning
- Changelog maintenance
- Release process

### 5. MCP Integration Guide

**File**: `docs/mcp-integration.md` (NEW)

**Contents**:

#### MCP Protocol Overview
- JSON-RPC 2.0 specification
- Content-Length framing
- Request/Response structure

#### Server Architecture
- WorkshopMCPServer class
- Message handling flow
- Tool registration
- Error handling

#### Adding New Tools
- Tool definition structure
- Input schema specification
- Tool execution handler
- Testing new tools

#### Agent Configuration
- TOML format specification
- Instruction writing best practices
- Output schema design
- Execution strategies (plan vs. act)

## Implementation Tasks

### Phase 5.1: README Updates
- [ ] Update project description
- [ ] Add performance profiler to features
- [ ] Update quick start with both agents
- [ ] Add architecture overview
- [ ] Update testing section
- [ ] Add contributing guidelines

### Phase 5.2: Create New Documentation Files
- [ ] Create `docs/` directory
- [ ] Write `docs/performance-profiler.md`
- [ ] Write `docs/api-reference.md`
- [ ] Write `docs/developer-guide.md`
- [ ] Write `docs/mcp-integration.md`

### Phase 5.3: Add Usage Examples
- [ ] Create `examples/` directory
- [ ] Create `examples/bad_performance.py` (annotated)
- [ ] Create `examples/good_performance.py` (annotated)
- [ ] Create `examples/mcp_client_example.py`
- [ ] Create `examples/programmatic_usage.py`

### Phase 5.4: API Documentation
- [ ] Add docstrings to all public methods
- [ ] Generate API docs with Sphinx or pdoc
- [ ] Include type hints in documentation
- [ ] Add usage examples in docstrings

### Phase 5.5: Diagrams and Visuals
- [ ] Create architecture diagram (ASCII or Mermaid)
- [ ] Create data flow diagram
- [ ] Create example output screenshots
- [ ] Add issue severity hierarchy diagram

## Documentation Standards

### Writing Style
- Clear and concise
- Technical but accessible
- Use active voice
- Include code examples
- Explain the "why" not just the "how"

### Code Examples
- Must be runnable (or clearly marked as pseudo-code)
- Include expected output
- Show both good and bad patterns
- Comment liberally

### Formatting
- Use Markdown with GitHub flavor
- Code blocks with language specification
- Consistent heading levels
- Table of contents for long documents
- Links to related sections

## Success Criteria

- [ ] README is comprehensive and welcoming
- [ ] All features documented with examples
- [ ] API reference is complete and accurate
- [ ] Developer guide enables new contributors
- [ ] MCP integration is clearly explained
- [ ] Examples are runnable and pedagogical
- [ ] Documentation is discoverable (good navigation)
- [ ] No broken links or outdated information

## Review Checklist

Before marking documentation complete:

- [ ] Spelling and grammar check
- [ ] Technical accuracy verified
- [ ] Code examples tested
- [ ] Links verified
- [ ] Screenshots are current
- [ ] Version numbers are correct
- [ ] License information is accurate
- [ ] Contributing guidelines are clear
- [ ] Contact/support information provided

## Maintenance Plan

Documentation should be updated:
- When adding new features
- When fixing bugs that affect usage
- When performance characteristics change
- After each major release
- When receiving user feedback about clarity
