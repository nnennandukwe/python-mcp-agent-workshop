# End-to-End Testing Plan for Performance Profiler Agent

## Overview

This document outlines the plan for end-to-end (E2E) testing of the performance profiler agent, validating the complete workflow from MCP server through agent execution.

## Objectives

1. Validate MCP server correctly exposes performance_check tool
2. Verify agent configuration is properly formatted and loadable
3. Test complete workflow: agent invocation → MCP tool call → analysis results
4. Ensure output schema matches agent configuration expectations
5. Validate error handling across the full stack

## Test Scenarios

### Scenario 1: Basic Performance Analysis
**Goal**: Verify agent can analyze a Python file with known performance issues

**Setup**:
- Create test file: `test_fixtures/sample_bad_performance.py` with:
  - N+1 query pattern (Django ORM in loop)
  - Blocking I/O in async function
  - String concatenation in loop

**Steps**:
1. Start MCP server in test mode
2. Send `list_tools` request, verify `performance_check` is available
3. Send `call_tool` request with `file_path` parameter
4. Verify response structure matches output schema
5. Validate all expected issues are detected

**Expected Results**:
- Response contains summary with total_issues >= 3
- Critical issues include blocking I/O in async
- High priority issues include N+1 query
- Each issue has: category, severity, line_number, description, suggestion

### Scenario 2: Clean Code Analysis
**Goal**: Verify agent correctly reports no issues for well-written code

**Setup**:
- Create test file: `test_fixtures/sample_good_performance.py` with:
  - Async code using aiofiles
  - Prefetched queries
  - Efficient string building

**Steps**:
1. Send `call_tool` request with clean code file
2. Verify response indicates 0 issues
3. Validate positive feedback in summary

**Expected Results**:
- total_issues = 0
- No entries in critical_issues or high_priority_issues arrays
- Success = true

### Scenario 3: Source Code Analysis
**Goal**: Test analysis with source_code parameter instead of file_path

**Setup**:
- Prepare Python source code string with known issues

**Steps**:
1. Send `call_tool` request with `source_code` parameter
2. Verify analysis works without file system access
3. Validate results match expected issues

**Expected Results**:
- Analysis completes successfully
- Issues detected match source code patterns
- file_analyzed field may be empty or indicate "source_code"

### Scenario 4: Error Handling - Invalid File
**Goal**: Verify proper error responses for invalid inputs

**Steps**:
1. Send `call_tool` request with non-existent file_path
2. Verify JSON-RPC error response
3. Check error code and message

**Expected Results**:
- Response contains "error" field
- Error code = -32602 (Invalid params)
- Error message clearly indicates file not found

### Scenario 5: Error Handling - Syntax Error
**Goal**: Verify handling of Python files with syntax errors

**Setup**:
- Create test file with invalid Python syntax

**Steps**:
1. Send `call_tool` request with syntax-error file
2. Verify error response includes syntax details

**Expected Results**:
- Error code = -32602
- Error message indicates syntax error
- Response maintains JSON-RPC structure

### Scenario 6: Agent Output Schema Validation
**Goal**: Verify agent responses match defined output schema

**Setup**:
- Use agent configuration's output_schema definition

**Steps**:
1. Run agent with various test cases
2. Validate each response against JSON schema
3. Check all required fields are present
4. Verify field types match schema

**Expected Fields**:
```json
{
  "success": boolean,
  "file_analyzed": string,
  "summary": {
    "total_issues": integer,
    "critical_count": integer,
    "high_count": integer,
    "medium_count": integer,
    "low_count": integer,
    "overall_assessment": string
  },
  "critical_issues": array,
  "high_priority_issues": array,
  "other_issues_summary": string,
  "optimization_roadmap": object,
  "risk_assessment": object
}
```

## Test Fixtures

### Required Test Files

1. **test_fixtures/sample_bad_performance.py**
   - Contains all major anti-pattern categories
   - Well-documented with inline comments explaining issues
   - Line numbers predictable for assertion

2. **test_fixtures/sample_good_performance.py**
   - Demonstrates best practices
   - No performance issues
   - Shows async/await done correctly

3. **test_fixtures/sample_mixed.py**
   - Mix of good and bad patterns
   - Tests prioritization and partial issues

4. **test_fixtures/sample_syntax_error.py**
   - Invalid Python syntax for error testing

## Testing Approach

### Unit Level
- Already covered by existing `test_mcp_server_integration.py` (10 tests)
- Validates individual tool execution

### Integration Level (NEW)
- Test MCP server message framing with agent-like requests
- Validate JSON-RPC protocol compliance
- Test concurrent tool calls

### E2E Level (NEW)
- Simulate complete agent workflow
- Test with actual agent configuration loaded
- Validate output matches agent expectations

## Implementation Tasks

### Task 1: Create Test Fixtures
- [ ] Create `test_fixtures/` directory
- [ ] Write sample_bad_performance.py with documented issues
- [ ] Write sample_good_performance.py with best practices
- [ ] Write sample_mixed.py with varied issues
- [ ] Write sample_syntax_error.py for error testing

### Task 2: Write E2E Test Suite
- [ ] Create `tests/test_e2e_workflow.py`
- [ ] Implement Scenario 1: Basic analysis test
- [ ] Implement Scenario 2: Clean code test
- [ ] Implement Scenario 3: Source code parameter test
- [ ] Implement Scenario 4: Invalid file error test
- [ ] Implement Scenario 5: Syntax error test
- [ ] Implement Scenario 6: Schema validation test

### Task 3: Agent Configuration Testing
- [ ] Create `tests/test_agent_config.py`
- [ ] Validate TOML file is well-formed
- [ ] Verify all required fields present
- [ ] Test output schema is valid JSON schema
- [ ] Validate instructions are comprehensive

### Task 4: Load Testing (Optional)
- [ ] Test with large files (>1000 lines)
- [ ] Test with files having many issues (>50)
- [ ] Measure response times
- [ ] Validate memory usage is reasonable

## Success Criteria

- [ ] All E2E tests pass consistently
- [ ] Agent configuration loads without errors
- [ ] Output schema validation passes for all scenarios
- [ ] Error handling covers all edge cases
- [ ] Test coverage for E2E flows >= 80%
- [ ] Documentation clearly explains testing approach

## Manual Testing Checklist

For human validation before merging:

- [ ] Start MCP server manually: `poetry run python -m workshop_mcp.server`
- [ ] Send test JSON-RPC requests via stdin
- [ ] Verify responses on stdout
- [ ] Test with real-world Python files from the project
- [ ] Confirm agent works with actual LLM (Gemini 2.5 Pro)
- [ ] Validate analysis quality and suggestions are accurate

## Future Enhancements

- Performance benchmarking suite
- Regression testing with known issues database
- Integration with CI/CD pipeline
- Automated agent conversation testing
- Mock LLM responses for deterministic testing
