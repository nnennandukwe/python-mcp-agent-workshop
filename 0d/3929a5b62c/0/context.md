# Session Context

## User Prompts

### Prompt 1

Let's look at my GH PRs. Which one should be resolved first?

### Prompt 2

Let's analyze PR 49. Are there outstanding Qodo comments to address?

### Prompt 3

Base directory for this skill: /Users/nnennandukwe/.claude/skills/pr-resolver

# Qodo PR Resolver

Fetch Qodo review issues for your current branch's PR/MR, fix them interactively or in batch, and reply to each inline comment with the decision. Supports GitHub, GitLab, Bitbucket, and Azure DevOps.

## Prerequisites

### Required Tools:
- **Git** - For branch operations
- **Git Provider CLI** (one of):
  - **GitHub**: `gh` CLI
    - Install: `brew install gh` or [cli.github.com](https://cli.githu...

### Prompt 4

### Issue description
`pythonic_check` reads file contents but only catches `UnicodeDecodeError`. Other I/O errors can escape the handler.

### Issue Context
Even after `validate_exists`, the file can be deleted/changed or become unreadable before `read_text` runs. This should return a structured JSON-RPC error instead of throwing.

### Fix Focus Areas
- src/workshop_mcp/server.py[655-669]

