# Codebase Concerns

**Analysis Date:** 2026-01-25

## Race Condition in Keyword Search Results

**Issue:** Concurrent file read operations mutate shared result dictionary without synchronization.

**Files:** `src/workshop_mcp/keyword_search.py` (lines 282-304)

**Impact:** In high-concurrency scenarios with many simultaneous file reads, concurrent mutations to `result["summary"]` counters can cause race conditions. Multiple coroutines increment `total_files_searched`, `total_occurrences`, `total_files_with_matches`, and `files_with_errors` without atomic operations or locks. This produces incorrect summary statistics.

**Current Code:**
```python
result["summary"]["total_files_searched"] += 1
if occurrences > 0:
    result["summary"]["total_files_with_matches"] += 1
    result["summary"]["total_occurrences"] += occurrences
```

**Fix approach:** Use thread-safe counter library (e.g., `threading.Lock`, `asyncio.Lock`, or `collections.Counter`) to protect counter mutations, or refactor to collect results per-coroutine and aggregate in single-threaded final step.

---

## Memory Leak in Keyword Search with Large Files

**Issue:** Entire file contents loaded into memory at once, no support for streaming.

**Files:** `src/workshop_mcp/keyword_search.py` (line 268)

**Impact:** Large files (>500MB) are read entirely with `await file.read()`, causing memory spikes and potential OOM errors. No streaming or chunked reading implemented. This is especially problematic when searching directories with large log files or data files.

**Current Code:**
```python
async with aiofiles.open(file_path, "r", encoding="utf-8", errors="ignore") as file:
    content = await file.read()  # Loads entire file into memory
```

**Fix approach:** Implement streaming with line-by-line iteration or fixed chunk size (e.g., 64KB chunks) to keep memory footprint constant regardless of file size. Provide optional max-file-size parameter to skip oversized files.

---

## Event Loop Lifecycle Management Issue

**Issue:** Single event loop instance reused across multiple requests, no error isolation.

**Files:** `src/workshop_mcp/server.py` (lines 53-54, 386)

**Impact:** If an async operation fails or raises an exception in `run_until_complete()`, the event loop remains in a potentially degraded state. Subsequent requests may fail with spurious errors. Mixing sync and async contexts in a long-running server makes debugging difficult. The loop is never cleaned between calls.

**Current Code:**
```python
def __init__(self) -> None:
    self.loop = asyncio.new_event_loop()
    asyncio.set_event_loop(self.loop)

# Later...
result = self.loop.run_until_complete(
    self.keyword_search_tool.execute(...)
)
```

**Fix approach:** Either (1) use `asyncio.run()` to create a fresh loop per request, or (2) wrap `run_until_complete()` with proper exception handling and loop state validation between requests. Test recovery behavior after exceptions.

---

## Uncaught Exception in Async Gather

**Issue:** CancelledError is re-raised but other exceptions may be silently dropped.

**Files:** `src/workshop_mcp/keyword_search.py` (lines 151-161)

**Impact:** When `asyncio.gather(return_exceptions=True)` completes, search_results contains exceptions mixed with None results. The code explicitly handles `CancelledError` but logs other exceptions without failing fast. This means searches can complete "successfully" while silently losing significant data.

**Current Code:**
```python
search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
for search_result in search_results:
    if isinstance(search_result, asyncio.CancelledError):
        raise search_result
    if isinstance(search_result, Exception):
        result["summary"]["files_with_errors"] += 1
        self.logger.error("Search task for a root path failed: %s", search_result, exc_info=True)
        result.setdefault("search_errors", []).append(...)
```

**Fix approach:** Log whether *any* search task failed and optionally fail the entire search operation for critical errors. Distinguish between recoverable per-file errors and fatal directory-traversal errors. Return error status in result structure.

---

## Fragile Pattern Detection Heuristics

**Issue:** ORM and blocking I/O detection relies on simple string matching with high false positive/negative rates.

**Files:** `src/workshop_mcp/performance_profiler/patterns.py` (lines 125-257)

**Impact:** The patterns rely on substring matching (e.g., `".objects." in function_name`) which produces false positives (detecting ORM queries in user variable names) and false negatives (missing aliased imports like `from django.db import models as m`). Users may dismiss tool as unreliable.

**Example problem:**
```python
# False positive: detects this as ORM query
user_objects.all()  # user_objects is not Django ORM

# False negative: misses this
from django.db.models import QuerySet
# QuerySet operations won't be detected if not explicitly importing models
```

**Fix approach:** Enhance semantic analysis by tracking imports and type inference more carefully. Use Astroid's inference capabilities to resolve imported names. Add confidence scores to findings.

---

## Binary File Handling Mismatch

**Issue:** Binary file detection happens after file read attempt, wasting I/O on unsuitable files.

**Files:** `src/workshop_mcp/keyword_search.py` (lines 306-316, 299-301)

**Impact:** The `_is_text_file()` check based on extension happens at directory traversal time, but binary files are only actually skipped during read via `UnicodeDecodeError`. This means binary files (images, archives, compiled code) are opened and read, then discarded on encoding error. Wastes disk I/O especially with large binaries.

**Current Code:**
```python
if not self._is_text_file(file_path):  # Extension check
    continue
# Later...
except UnicodeDecodeError:  # Only caught during read
    self.logger.debug(f"Skipping binary file: {file_path}")
```

**Fix approach:** The extension check at line 216 should prevent binary opens, but aiofiles with `errors="ignore"` silently discards undecodable bytes. Consider reading first N bytes to verify text format, or skip files with encoding errors at open time.

---

## Insufficient Regex ReDoS Protection

**Issue:** ReDoS (Regular Expression Denial of Service) protection is incomplete.

**Files:** `src/workshop_mcp/performance_profiler/patterns.py` (lines 324-340)

**Impact:** Current checks only catch nested quantifiers like `(a+)+` but miss other ReDoS patterns like excessive alternation `(a|b|c|...)*` or backreferences. An attacker providing a crafted regex could hang the keyword search tool.

**Current Code:**
```python
dangerous_patterns = [
    r'\([^)]*[+*][^)]*\)[+*]',  # Nested quantifiers like (a+)+
    r'\([^)]*\|[^)]*\)[+*]',     # Alternation with quantifier like (a|b)+
]
```

**Fix approach:** Use a regex complexity analyzer library (e.g., `regex` crate or dedicated ReDoS detector) or impose a timeout on regex matching operations with signal handlers.

---

## Mutable Default Arguments in Patterns

**Issue:** Static pattern dictionaries are mutable and shared globally.

**Files:** `src/workshop_mcp/performance_profiler/patterns.py` (lines 43-122)

**Impact:** If any code mutates `ORM_QUERY_PATTERNS`, `BLOCKING_IO_FUNCTIONS`, or other module-level dicts, all subsequent checks are affected. This is a latent bug waiting to happen if code ever dynamically adds patterns.

**Current Code:**
```python
ORM_QUERY_PATTERNS = {  # Mutable dict at module level
    "django": [...],
    "sqlalchemy": [...]
}
```

**Fix approach:** Convert to `frozendict` or freeze with `types.MappingProxyType()` to prevent accidental mutations.

---

## Missing Python Version Compatibility Check

**Issue:** Code targets Python 3.10+ but no version validation at import time.

**Files:** `pyproject.toml` (line 14)

**Impact:** If the package is installed on Python 3.9 or earlier, imports succeed but runtime failures occur (e.g., `match`/`case` statements would cause SyntaxError). No explicit `sys.version_info` check in `__init__.py`.

**Current requirement:**
```toml
python = ">=3.10,<4.0"
```

**Fix approach:** Add version check in `src/workshop_mcp/__init__.py`:
```python
import sys
if sys.version_info < (3, 10):
    raise RuntimeError("workshop_mcp requires Python 3.10 or later")
```

---

## Logging Configuration Only at Server Level

**Issue:** Logging is configured only in `server.py` but not when modules are imported directly.

**Files:** `src/workshop_mcp/server.py` (lines 20-26)

**Impact:** If `PerformanceChecker` or `KeywordSearchTool` are used programmatically (not via MCP server), logging is unconfigured. Users see no debug output. Different log levels between server and direct usage create confusion.

**Fix approach:** Move logging configuration to `__init__.py` so it applies regardless of import path. Allow configuration via environment variables.

---

## Test Coverage Gaps

**Untested areas:**

1. **Concurrent search of same directory:** No test for multiple simultaneous searches of overlapping directory trees (lines 138-148 in keyword_search.py).

2. **Event loop error recovery:** No test for MCP server behavior after `run_until_complete()` raises exception (lines 386-395 in server.py).

3. **Very large files (>1GB):** Memory test suite doesn't validate streaming vs. load-all behavior at scale.

4. **Symlink handling:** No tests for symlinks, junction points, or circular directory references in traversal.

5. **Permission errors at scale:** Tests exist for single permission denied but not for directories with many inaccessible files.

**Files:** `tests/test_keyword_search.py`, `tests/test_mcp_server_integration.py`

**Risk:** These untested paths may fail in production. User reports of "search hangs on large files" or "permission error crashes server" are unverified before merge.

**Priority:** HIGH - Concurrency and memory tests should be added before 1.0 release.

---

## Blocking Call in Sync MCP Handler

**Issue:** `self.loop.run_until_complete()` blocks the entire server while async work completes.

**Files:** `src/workshop_mcp/server.py` (lines 386-395)

**Impact:** While a long-running search executes (e.g., 30-second grep of large codebase), the server's event loop is blocked and cannot process other requests. For a single-threaded server, this is expected, but if multiple clients connect, they stall. No timeout mechanism exists.

**Current Code:**
```python
result = self.loop.run_until_complete(
    self.keyword_search_tool.execute(...)
)
```

**Fix approach:** Implement request timeouts (e.g., 60-second default) and document this blocking behavior in MCP tool schema. Consider process-based parallelism for future scalability.

---

## Astroid Inference Limitations

**Issue:** Astroid's type inference is limited for complex code, leading to missed pattern detections.

**Files:** `src/workshop_mcp/performance_profiler/ast_analyzer.py` (lines 408-420)

**Impact:** Patterns like N+1 queries only detected if function names match known patterns. If user writes custom query wrapper, tool doesn't detect it. Semantic inference doesn't work across module boundaries.

**Example miss:**
```python
# This N+1 query won't be detected if execute() is a custom wrapper
def custom_query(obj_id):
    return User.objects.filter(id=obj_id)

for user_id in user_ids:
    custom_query(user_id)  # N+1 but goes undetected
```

**Fix approach:** Document inference limitations. Consider adding custom pattern registry for project-specific ORMs. Add note to findings about conservative filtering.

---

## Incomplete Error Messages

**Issue:** JSON-RPC error responses lack actionable context for some failures.

**Files:** `src/workshop_mcp/server.py` (lines 326-329)

**Impact:** When `KeyError` is caught for missing arguments, error message just says `"missing": "str(exc)"` which produces unhelpful output like `"missing": "'keyword'"` instead of `"missing": "keyword"` or `"missing_param": "keyword"`.

**Current Code:**
```python
except KeyError as exc:
    return self._error_response(
        request_id,
        JsonRpcError(-32602, "Missing required argument", {"missing": str(exc)}),
    )
```

**Fix approach:** Extract argument name more carefully: `str(exc).strip("'\"")` or use `exc.args[0]` directly.

---

## Statistics Calculation Happens After Aggregation

**Issue:** Summary statistics calculated after all results collected, but concurrent mutations may still occur.

**Files:** `src/workshop_mcp/keyword_search.py` (lines 167-174, 397-428)

**Impact:** Between gathering all search results and calling `_calculate_summary()`, there's a window where counters may be inconsistent. If `_calculate_summary()` is called while background tasks are still updating the dict, calculations like `average_occurrences_per_matching_file` will be incorrect.

**Fix approach:** Ensure all concurrent operations are truly complete before summary calculation, or calculate summary within each async task and aggregate deterministically.

---

## Dependencies with Known Vulnerabilities Not Monitored

**Issue:** No automated dependency vulnerability scanning in CI pipeline.

**Files:** `pyproject.toml`

**Impact:** Direct dependencies (astroid, aiofiles) could have CVEs. Current setup has no pipeline to alert maintainers. Manual `pip audit` required.

**Fix approach:** Add `pip audit` or `safety` check to CI. Pin dependency versions more tightly or use dependabot for automated PRs.

---

## No Input Validation on Paths

**Issue:** File paths accepted directly from user input without path traversal checks.

**Files:** `src/workshop_mcp/keyword_search.py` (lines 130-136)

**Impact:** Symbolic links could point outside intended root directory. On systems without proper symlink restrictions, a malicious client could request search of `/etc/passwd` via symlink. Path resolution with `.resolve()` mitigates this somewhat but not tested thoroughly.

**Fix approach:** Validate that resolved path is within root directory using `resolved_path.relative_to(root_path)` after resolution, and document this behavior.

---

*Concerns audit: 2026-01-25*
