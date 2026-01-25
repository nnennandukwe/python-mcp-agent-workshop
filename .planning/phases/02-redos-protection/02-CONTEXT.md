# Phase 2: ReDoS Protection - Context

**Gathered:** 2026-01-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Prevent regex denial-of-service attacks in the keyword_search tool. Implement timeout protection, pattern validation, and safe error handling. This phase protects the server from malicious or poorly-formed regex patterns that could hang execution.

</domain>

<decisions>
## Implementation Decisions

### Timeout behavior
- Default timeout: 1 second per file (not configurable by callers)
- No override mechanism — 1 second is the hard limit
- Per-file timeout, not total operation timeout — one slow file doesn't kill the whole search
- Timeout message: "Pattern evaluation timed out"

### Pattern rejection
- Maximum pattern length: 500 characters
- Pre-validate regex syntax before searching (catch typos early)
- Block known catastrophic backtracking patterns: `(.*)+`, `(.+)*`, `(a+)+` and similar nested quantifiers
- Be permissive with blocklist — only block obvious ReDoS patterns, minimize false positives

### User feedback
- Blocked patterns: "Pattern rejected: nested quantifiers detected"
- Length exceeded: "Pattern exceeds maximum length (500 characters)"
- Invalid syntax: "Invalid regex syntax" (generic, don't expose Python internals)
- Timeout: "Pattern evaluation timed out"
- Use different JSON-RPC error codes for different failure types (syntax vs timeout)

### Fallback behavior
- If pattern times out on one file: skip that file, continue search
- Report skipped files in response metadata (`skipped_files: [...]`)
- If >50% of files are skipped due to timeout: abort entire search
- Abort message: "Pattern timed out on too many files"

### Claude's Discretion
- Specific timeout implementation mechanism (signal-based, thread-based, regex library)
- Exact catastrophic backtracking patterns to block
- JSON-RPC error code assignments
- Internal logging format for security events

</decisions>

<specifics>
## Specific Ideas

- Error codes should be distinct for programmatic handling (syntax errors vs timeout vs blocklist)
- Skipped files go in metadata, not as a warning that clutters results
- Pattern blocklist should be minimal — only proven ReDoS vectors, not heuristic guessing

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-redos-protection*
*Context gathered: 2026-01-25*
