# Session Context

## User Prompts

### Prompt 1

Which PR should I review next? Highest priority order please.

### Prompt 2

Base directory for this skill: /Users/nnennandukwe/.claude/skills/pr-resolver

# Qodo PR Resolver

Fetch Qodo review issues for your current branch's PR/MR, fix them interactively or in batch, and reply to each inline comment with the decision. Supports GitHub, GitLab, Bitbucket, and Azure DevOps.

## Prerequisites

### Required Tools:
- **Git** - For branch operations
- **Git Provider CLI** (one of):
  - **GitHub**: `gh` CLI
    - Install: `brew install gh` or [cli.github.com](https://cli.githu...

### Prompt 3

The issue below was found during a code review. Follow the provided context and guidance below and implement a solution

## Issue description
Returning a line number entry for every occurrence can explode the response size for common keywords. The MCP server sends the complete JSON response without pagination/limits, risking large stdout messages and heavy JSON serialization overhead.
### Issue Context
This is a usability/scalability concern rather than a correctness issue, but it can cause real...

### Prompt 4

commit this and push.

