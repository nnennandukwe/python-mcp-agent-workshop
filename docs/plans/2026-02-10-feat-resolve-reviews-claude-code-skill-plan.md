---
title: "feat: Add /resolve-reviews Claude Code skill for Qodo comment resolution"
type: feat
date: 2026-02-10
---

# feat: Add /resolve-reviews Claude Code Skill

## Overview

Create a Claude Code slash command (`/resolve-reviews`) that autonomously resolves actionable Qodo (PR-Agent) code review comments on GitHub PRs. The skill fetches review comments, parses Qodo's structured format, prioritizes issues, implements fixes — including multi-file changes — with per-issue commits, and prompts the user to push.

This will be the first non-GSD custom command in the project, establishing the pattern for project-specific Claude Code skills.

## Problem Statement / Motivation

After Qodo reviews a PR, it leaves inline comments with structured suggestions (security fixes, bug reports, style violations). Currently, resolving these requires manually reading each comment, understanding the suggestion, implementing the fix, and committing. This is tedious and error-prone, especially for PRs with many comments.

The skill automates this entire loop — turning a 20-minute manual review-and-fix cycle into a single command. It leverages Claude Code's agent teammate capability to parallelize independent fixes for speed.

## Proposed Solution

A single Claude Code command file at `.claude/commands/resolve-reviews.md` that instructs Claude to:

1. Run pre-flight checks (branch, working tree, `gh` auth)
2. Fetch and parse Qodo review comments via GitHub API
3. Display a prioritized plan of actionable items
4. **Spawn agent teammates** to resolve independent fixes in parallel
5. Retry fixes that fail validation — the goal is resolution, not just attempt
6. Present a summary and offer to push

### Design Document

The detailed design specification already exists at `.claude/docs/resolve-reviews-design.md`, covering:
- Qodo comment HTML format and parsing regex
- `ActionableItem` data model
- Priority normalization (P0-P2)
- Commit message format
- UX mockups for success and failure scenarios

This plan focuses on **what the design doc missed** and the implementation structure.

## Execution Architecture

### Agent Teammate Strategy

The skill should use Claude Code's `Task` tool to spawn agent teammates for parallel fix resolution. The lead agent orchestrates while teammates implement fixes concurrently.

```
/resolve-reviews 49
        │
        ▼
┌────────────────────────────────┐
│  LEAD AGENT                    │
│  1. Pre-flight checks          │
│  2. Fetch & parse comments     │
│  3. Build dependency graph     │
│  4. Display plan               │
└────────────────────────────────┘
        │
        ▼
┌────────────────────────────────────────────────────────┐
│  PARALLEL EXECUTION (independent items)                │
│                                                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │ Agent A  │  │ Agent B  │  │ Agent C  │  ...       │
│  │ P0 fix   │  │ P1 fix   │  │ P2 fix   │            │
│  │ server.py│  │ checker  │  │ utils.py │            │
│  └──────────┘  └──────────┘  └──────────┘            │
│                                                        │
│  Items sharing files → run SEQUENTIALLY                │
│  Items on different files → run in PARALLEL            │
└────────────────────────────────────────────────────────┘
        │
        ▼
┌────────────────────────────────┐
│  LEAD AGENT                    │
│  5. Collect results            │
│  6. Create commits (ordered)   │
│  7. Display summary            │
│  8. Push prompt                │
└────────────────────────────────┘
```

**Dependency graph:** Items are grouped by their target files. Items touching different files can be resolved in parallel by separate agent teammates. Items touching the same file must be resolved sequentially (in priority order) to avoid conflicts.

**Why teammates matter:** A PR with 6 Qodo comments across 4 files can resolve all 4 file groups concurrently instead of fixing 6 items one-by-one. For a typical review, this cuts resolution time significantly.

### Fix Resolution Strategy (Not Just Attempt — Actually Resolve)

Each fix attempt follows a **resolve-or-escalate** loop, not a single-shot attempt:

```
For each actionable item:
    attempt = 1
    max_attempts = 3

    while attempt <= max_attempts:
        1. Read the target file(s)
        2. Apply fix using Qodo's agent prompt as guidance
        3. Validate: python -m py_compile <file>
        4. If valid → stage and break (success)
        5. If invalid:
           a. Read the error message
           b. git checkout -- <file>  (restore clean state)
           c. Retry with error context: "Previous attempt failed
              because: <error>. Fix the issue differently."
           d. attempt += 1

    If all attempts fail:
        Log "✗ Could not resolve after 3 attempts: <last error>"
        Restore file to clean state
        Continue to next item
```

The key difference from the original design: **failures trigger retries with error context**, not immediate skip. The agent learns from each failed attempt and adjusts its approach. Only after exhausting retries does it move on.

## Technical Considerations

### Pre-flight Checks (Critical — Not in Design Doc)

Before any work, the skill must verify:

| Check | Command | Failure Behavior |
|-------|---------|------------------|
| Clean working tree | `git status --porcelain` | Abort: "Stash or commit changes first" |
| Correct branch | `gh pr view <pr> --json headRefName` vs `git branch --show-current` | Abort: "Switch to `<branch>` first" |
| Not on protected branch | Check against `main`/`master` | Abort: "Cannot commit to protected branch" |
| `gh` authenticated | `gh auth status` | Abort: "Run `gh auth login` first" |

### Multi-File Fix Support

Qodo comments can reference multiple files in their Fix Focus Areas:

```
## Fix Focus Areas
- src/workshop_mcp/server.py[632-646]
- src/workshop_mcp/security/path_validator.py[102-132]
- src/workshop_mcp/pythonic_check/pythonic_checker.py[67-72]
```

The skill must:

1. **Parse Fix Focus Areas** from the agent prompt body using regex:
   ```
   r'[-•]\s*([\w/]+\.py)\[(\d+)-?(\d+)?\]'
   ```

2. **Extend the data model** to support multiple files:
   ```python
   @dataclass
   class ActionableItem:
       id: str
       priority: int
       primary_file: str              # From API path field
       affected_files: list[tuple[str, tuple[int, int]]]  # All files from Fix Focus Areas
       agent_prompt: str
       title: str
       category: str
   ```

3. **Dependency graph uses all affected files**, not just the primary file. Two items that share *any* affected file must be resolved sequentially.

4. **Validation runs on all modified files**, not just the primary file. All must pass `py_compile` for the fix to be accepted.

5. **Rollback restores all modified files** on failure: `git checkout -- <file1> <file2> ...`

### Parsing Fixes (Gaps Found in Design Doc)

**`line` can be `null`:** Real data from PR #49 shows `line: null, start_line: null`. Fix: fall back to `original_line` / `original_start_line` fields.

```python
# Updated extraction logic
end_line = comment.get("line") or comment.get("original_line")
start_line = comment.get("start_line") or comment.get("original_start_line") or end_line
```

**`title` and `category` not extracted:** The data model includes both but the parsing pseudocode never sets them. Extract from:
- Title: the numbered description line (e.g., `1. <b><i>method_name</i></b> description text`)
- Category: the emoji-tagged code block (e.g., `⛨ Security`, `⛯ Reliability`)

**`agent_prompt` can be `None`:** If the `<details>` regex doesn't match, skip the item with "Could not extract fix instructions."

### Dynamic Repository Detection

Derive owner/repo dynamically instead of hardcoding:

```bash
gh repo view --json nameWithOwner -q .nameWithOwner
```

### Pagination

GitHub API defaults to 30 items/page. Use `--paginate` flag:

```bash
gh api --paginate repos/{owner}/{repo}/pulls/{pr}/comments
```

### Line Number Drift for Same-File Fixes

When multiple items target the same file, fixing item N may shift line numbers for item N+1. Mitigation: re-read the file fresh for each item and rely on the agent prompt's semantic description rather than exact line numbers as the primary targeting mechanism. The line range becomes advisory context, not prescriptive.

### Security: Agent Prompt Trust Model

The agent prompt is extracted from Qodo bot comments and executed as instructions. Mitigations:
- Filter strictly on `user.login === "qodo-code-review[bot]"`
- The bot account is verified by GitHub (bot badge)
- Acceptable risk for v1 since only the repo owner invokes the skill

## Acceptance Criteria

### Functional Requirements

- [x] Skill file exists at `.claude/commands/resolve-reviews.md`
- [x] Invocation: `/resolve-reviews <pr-number>` works
- [x] Pre-flight checks: clean tree, correct branch, not on protected branch, `gh` auth
- [x] Fetches inline review comments via `gh api --paginate`
- [x] Filters for `qodo-code-review[bot]` comments only
- [x] Correctly identifies actionable items (`alt="Action required"`)
- [x] Extracts priority, agent prompt, file path, line range (with `null` fallbacks)
- [x] Extracts title and category from comment body
- [x] Parses Fix Focus Areas for multi-file affected file list
- [x] Builds dependency graph: same-file items sequential, different-file items parallel
- [x] Displays prioritized plan before execution
- [x] Spawns agent teammates for parallel resolution of independent items
- [x] Implements each fix using Qodo's agent prompt as guidance
- [x] Supports multi-file fixes (reads, modifies, and validates all affected files)
- [x] Retries failed fixes up to 3 times with error context from previous attempt
- [x] Validates all modified files with `python -m py_compile` before committing
- [x] Restores all modified files (`git checkout --`) on final failure
- [x] Creates one commit per resolved item with conventional commit format
- [x] Handles same-file multi-item fixes sequentially (re-reads between items)
- [x] Skips items with missing agent prompt
- [x] Shows summary with success/failure counts and attempt details
- [x] Prompts "Push N commits to origin?" with Yes/No
- [x] Derives repo owner/name dynamically from git remote
- [x] Handles 0 Qodo comments gracefully (early exit with message)
- [x] Handles 0 actionable items gracefully (early exit with message)

### Quality Gates

- [x] Tested against a real PR with Qodo comments (e.g., PR #49)
- [x] Handles the `line: null` edge case from PR #49 comment #1
- [x] Multi-file fix correctly modifies and validates all referenced files
- [x] Retry logic recovers from at least one type of validation failure
- [x] Co-Authored-By uses `Claude Opus 4.6` (updated from design doc's 4.5)

## User Experience

### What the User Sees

```
> /resolve-reviews 49

Pre-flight checks...
  ✓ Working tree clean
  ✓ On branch feat/pythonic-checker-42 (matches PR)
  ✓ GitHub CLI authenticated

Fetching PR #49 review comments...

Found 4 actionable items from Qodo:

  P0  ▸ source_code type not validated       server.py:610-631
  P0  ▸ Discarded validated path (TOCTOU)    server.py:633-646
        + path_validator.py:102-132
        + pythonic_checker.py:67-72
  P1  ▸ Empty file_path can crash            pythonic_checker.py:64-82
  P2  ▸ __init__ missing return hint         pythonic_checker.py:51

Execution plan:
  Sequential group 1 (server.py): items #1, #2
  Sequential group 2 (pythonic_checker.py): items #3, #4
  → Groups 1 and 2 resolve in parallel via agent teammates

Resolving issues...

  ✓ Fixed source_code type validation (a1b2c3d)
  ✓ Fixed TOCTOU path handling across 3 files (e4f5g6h)
  ✓ Fixed empty file_path edge case (i7j8k9l)  [retry 2/3 — first attempt had syntax error]
  ✓ Fixed __init__ return type hint (m0n1o2p)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

4/4 issues resolved.

Push 4 commits to origin/feat/pythonic-checker-42?
▸ Yes
  No
```

### With Failures After Retries

```
  ✓ Fixed source_code type validation (a1b2c3d)
  ✗ Could not resolve TOCTOU path handling after 3 attempts
    Last error: path_validator.py import cycle
  ✓ Fixed empty file_path edge case (i7j8k9l)
  ✓ Fixed __init__ return type hint (m0n1o2p)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

3/4 issues resolved. 1 failed after 3 attempts (see above).

Push 3 commits to origin?
```

## File Structure

```
.claude/
├── commands/
│   ├── gsd/                          # Existing GSD commands
│   └── resolve-reviews.md            # NEW - skill definition
└── docs/
    └── resolve-reviews-design.md     # Existing design document (update needed)
```

### Skill File Structure

The command file should follow the project's established command format (adapted from GSD patterns):

```markdown
---
name: resolve-reviews
description: Autonomously resolve Qodo code review comments on a PR
argument-hint: "<pr-number>"
---

# Resolve Reviews

<objective>
Resolve all actionable Qodo review comments on the specified PR
by fetching comments, implementing fixes (with retries), and
committing each resolution.
</objective>

<context>
$ARGUMENTS
@.claude/docs/resolve-reviews-design.md
</context>

<process>
1. PRE-FLIGHT CHECKS
   ...

2. FETCH & PARSE
   ...

3. BUILD DEPENDENCY GRAPH & DISPLAY PLAN
   ...

4. RESOLVE WITH AGENT TEAMMATES
   ...

5. SUMMARY & PUSH PROMPT
   ...
</process>

<success_criteria>
- [ ] All actionable items attempted with up to 3 retries each
- [ ] Multi-file fixes modify and validate all affected files
- [ ] Each resolved item has its own commit
- [ ] Summary displayed with success/failure/retry counts
</success_criteria>
```

## Deferred to v2

These items were identified by the SpecFlow analysis but are not needed for v1:

- **Item selection from plan** — Let users deselect items before execution
- **Dry-run mode** — Preview fixes without committing
- **Re-run deduplication** — Track previously resolved items across runs
- **PR URL parsing** — Accept full GitHub URLs (v1 accepts PR numbers only)
- **Stale line number detection** — Compare `comment.commit_id` with current HEAD
- **Multi-reviewer support** — CodeRabbit, Sourcery, SonarCloud parsers

## Dependencies & Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Qodo changes comment HTML format | Low | High | Document expected format; warn user if all parsing fails |
| Complex fixes exceed Claude's ability | Medium | Medium | 3 retries with error context; log failure, continue |
| Line number drift corrupts fixes | Medium | Medium | Re-read file between items; semantic prompts over line numbers |
| Pre-commit hooks reject commits | Low | Medium | Handle hook failures; retry with adjusted code |
| Multi-file fix creates import cycles | Low | Medium | Validate all files before committing; rollback all on failure |
| Agent teammates create merge conflicts | Low | High | Dependency graph ensures same-file items are sequential |

## Success Metrics

- Resolves 80%+ of Qodo actionable items on first run
- Retry mechanism recovers from at least 50% of initial failures
- Parallel execution reduces total resolution time vs sequential for PRs with 3+ independent file groups

## References & Research

### Internal References

- Design document: `.claude/docs/resolve-reviews-design.md`
- Qodo config: `.pr_agent.toml`
- GSD command examples: `.claude/commands/gsd/*.md`
- Existing Qodo work branch: `origin/claude/fetch-qodo-comments-1S59w`

### External References

- [GitHub Pull Request Review Comments API](https://docs.github.com/en/rest/pulls/comments)
- [Claude Code Custom Slash Commands](https://docs.anthropic.com/en/docs/claude-code/tutorials#create-custom-slash-commands)
- [Qodo Merge Documentation](https://docs.qodo.ai/qodo-documentation/qodo-merge)

### Test PR

- PR #49 — 4 Qodo comments (2x P0, 1x P1, 1x P2), includes multi-file TOCTOU fix and `line: null` edge case
