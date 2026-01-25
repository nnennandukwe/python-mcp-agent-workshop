# Testing Patterns

**Analysis Date:** 2026-01-25

## Test Framework

**Runner:**
- pytest 7.4.0+
- Config: `pyproject.toml` with `[tool.pytest.ini_options]`
- asyncio_mode = "auto" - auto-detects async tests
- testpaths = ["tests"]

**Assertion Library:**
- pytest's built-in assertions (assert statements)
- pytest.raises() for exception testing

**Run Commands:**
```bash
poetry run pytest                           # Run all tests
poetry run pytest -v                        # Verbose mode
poetry run pytest tests/test_keyword_search.py -v  # Specific test file
poetry run pytest --cov=workshop_mcp        # Run with coverage
poetry run pytest -x                        # Stop on first failure
```

## Test File Organization

**Location:**
- Co-located in separate `tests/` directory (not alongside source files)
- Root directory: `/tests/`

**Naming:**
- Pattern: `test_<module_name>.py`
- Examples: `test_keyword_search.py`, `test_performance_checker.py`, `test_ast_analyzer.py`

**Structure:**
```
tests/
├── test_ast_analyzer.py              # 41 tests - AST analysis
├── test_performance_checker.py        # 31 tests - Pattern detection
├── test_keyword_search.py             # 15 tests - File search
├── test_mcp_server_integration.py     # 10 tests - Tool registration
├── test_mcp_server_protocol.py        # 5 tests - Message framing
├── test_agent_config.py               # Tests for agent configuration
└── test_e2e_workflow.py               # End-to-end workflow tests
```

## Test Structure

**Suite Organization:**
```python
class TestBlockingIOInAsync:
    """Test blocking I/O detection in async functions."""

    def test_detect_blocking_open_in_async(self):
        """Test detection of blocking file open in async function."""
        source = """
async def read_file():
    with open('file.txt') as f:
        data = f.read()
    return data
"""
        checker = PerformanceChecker(source_code=source)
        issues = checker.check_blocking_io_in_async()

        assert len(issues) > 0
        issue = issues[0]
        assert issue.category == IssueCategory.BLOCKING_IO_IN_ASYNC
        assert issue.severity == Severity.CRITICAL
        assert "aiofiles" in issue.suggestion
```

**Patterns:**
- Test classes group related tests by functionality
- Each test method focuses on a single scenario
- Docstrings explain what's being tested
- Source code passed as string parameter (no file I/O in tests)
- Clear assertions with meaningful comparisons

## Mocking

**Framework:** No external mocking library; uses built-in pytest and asyncio

**Patterns:**
- File system operations tested with `tmp_path` pytest fixture
- Temporary directories created per test with `tempfile.TemporaryDirectory()`
- Test data created inline as strings in source code parameter

**Fixture Pattern from `test_keyword_search.py`:**
```python
@pytest_asyncio.fixture
async def temp_test_directory(self) -> Path:
    """Create a temporary directory with test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        test_files = {
            "test.py": "def hello_world(): pass",
            "test.java": "public class HelloWorld { }",
        }
        for filename, content in test_files.items():
            file_path = temp_path / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
        yield temp_path
```

**What to Mock:**
- File I/O - use `tmp_path` fixture for temporary test files
- Network calls - not present in current codebase

**What NOT to Mock:**
- Core business logic - always run real checks
- AST analysis - uses real Astroid analyzer
- Pattern detection - tests verify actual detection logic

## Fixtures and Factories

**Test Data:**
- Source code passed as strings to avoid file I/O:
  ```python
  source = """
  for user in User.objects.all():
      print(user.profile.name)
  """
  checker = PerformanceChecker(source_code=source)
  issues = checker.check_n_plus_one_queries()
  ```

- Temporary files created with pytest fixtures:
  ```python
  def test_init_with_file_path(self, tmp_path):
      """Test initialization with file path."""
      file_path = tmp_path / "test.py"
      source = "def hello(): pass"
      file_path.write_text(source)
      checker = PerformanceChecker(file_path=str(file_path))
  ```

**Location:**
- Fixtures in test files using `@pytest.fixture` and `@pytest_asyncio.fixture`
- Test data as inline strings (preferred approach)
- No separate factory or fixture module

**Fixture Examples from `test_mcp_server_protocol.py`:**
```python
@pytest.fixture
def server() -> WorkshopMCPServer:
    instance = WorkshopMCPServer()
    yield instance
    instance.loop.close()  # Cleanup

@pytest_asyncio.fixture
async def search_tool(self) -> KeywordSearchTool:
    """Create a KeywordSearchTool instance for testing."""
    return KeywordSearchTool()
```

## Coverage

**Requirements:**
- No explicit target enforced in config
- Coverage measured via pytest-cov (^5.0.0)
- Test suite has 102 tests total

**View Coverage:**
```bash
poetry run pytest --cov=workshop_mcp --cov-report=html
```

## Test Types

**Unit Tests:**
- Scope: Individual functions and methods in isolation
- Approach: Pass source code as strings, verify outputs
- Examples: `test_detect_django_n_plus_one_in_loop()`, `test_init_with_source_code()`
- Location: Majority of tests in `test_performance_checker.py` (31 tests), `test_ast_analyzer.py` (41 tests)

**Integration Tests:**
- Scope: Component interactions (MCP server with tools)
- Approach: Full request/response cycle through server
- Examples: `test_performance_check_with_source_code()`, `test_call_tool_response()`
- Location: `test_mcp_server_integration.py` (10 tests), `test_mcp_server_protocol.py` (5 tests)

**E2E Tests:**
- Framework: Custom test suite in `test_e2e_workflow.py`
- Scope: Full workflows from initialization through tool invocation
- Not traditional Selenium/browser-based; tests actual server behavior

## Common Patterns

**Async Testing:**
- Decorator: `@pytest.mark.asyncio` (via asyncio_mode = "auto" in config)
- Async fixtures: `@pytest_asyncio.fixture`
- Example from `test_keyword_search.py`:
  ```python
  @pytest_asyncio.fixture
  async def search_tool(self) -> KeywordSearchTool:
      return KeywordSearchTool()

  async def test_search_with_case_insensitive(self, search_tool):
      result = await search_tool.execute(
          keyword="WORLD",
          root_paths=[str(self.temp_path)],
          case_insensitive=True,
      )
      assert result["summary"]["total_occurrences"] > 0
  ```

**Error Testing:**
- Using `pytest.raises()` for exception validation:
  ```python
  def test_init_without_source_or_file(self):
      """Test that initialization fails without source or file."""
      with pytest.raises(ValueError):
          PerformanceChecker()

  def test_init_with_nonexistent_file(self):
      """Test that initialization fails with nonexistent file."""
      with pytest.raises(FileNotFoundError):
          ASTAnalyzer(file_path="/nonexistent/file.py")

  def test_init_with_syntax_error(self):
      """Test that initialization fails with invalid syntax."""
      with pytest.raises(SyntaxError):
          ASTAnalyzer(source_code="def invalid syntax")
  ```

**Parametrized Tests:**
- Not observed in current test suite
- Could be applied to test multiple inputs with `@pytest.mark.parametrize`

**Test Data Setup:**
- Inline strings for source code
- tmp_path fixture for file-based tests
- No setUp/tearDown methods; fixtures handle setup/cleanup

## Protocol Testing Pattern

**Test harness functions from `test_mcp_server_protocol.py`:**
```python
def _encode_message(payload: Dict[str, Any]) -> bytes:
    """Encode payload as Content-Length framed message."""
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    header = f"Content-Length: {len(data)}\r\n\r\n".encode("utf-8")
    return header + data

def _decode_message(raw: bytes) -> Dict[str, Any]:
    """Decode Content-Length framed message."""
    header_blob, body = raw.split(b"\r\n\r\n", 1)
    # Parse Content-Length header...
    return json.loads(body[:content_length].decode("utf-8"))

def _run_server_harness(
    server: WorkshopMCPServer, raw_message: bytes
) -> Optional[Dict[str, Any]]:
    """Execute one server request/response cycle."""
    stdin = io.BytesIO(raw_message)
    stdout = io.BytesIO()
    processed = server.serve_once(stdin, stdout)
    if not processed:
        return None
    stdout.seek(0)
    output = stdout.read()
    return _decode_message(output) if output else None
```

## Type Hints in Tests

- Function signatures include return types: `def test_init_with_source_code(self) -> None:`
- Fixtures typed: `async def search_tool(self) -> KeywordSearchTool:`
- Parameters typed where needed: `def test_extract_simple_function(self) -> None:`

---

*Testing analysis: 2026-01-25*
