# Chapter 0: Foundation Setup

## Verification Checklist
Run the verification script:

```bash
python3.12 verification.py
```
Expected output:

```
✅ Python 3.11+ 
✅ Poetry installed
✅ Project structure
✅ Dependencies installed
✅ Qodo Command
```

## Project Structure Overview

```bash
agent-mcp-workshop-python/
    ├── pyproject.toml              # Poetry configuration
    ├── README.md                   # Workshop documentation
    ├── verification.py             # Setup verification
    ├── src/workshop_mcp/           # Main package (we'll build this)
    ├── agents/                     # Agent configurations (we'll create this)
    ├── tests/                      # Test suite (we'll write this)
    └── lessons/                    # Chapter guides (navigation)
```

## Git Workflow

Each chapter has its own branch with progressive content:

```bash
# Start with setup
git checkout 00-setup

# Progress through chapters  
git checkout 01-mcp-basics
git checkout 02-keyword-search
# ... etc
```

## Development Environment

We'll use Poetry for dependency management:

```bash
# Install dependencies
poetry install

# Run commands in virtual environment
poetry run python [script]
poetry run pytest
poetry run workshop-mcp-server
```

## Workshop Flow

1. Instructor Demo: See the final working system
2. Chapter Work: Build components step-by-step
3. Testing: Verify each piece works
4. Integration: Connect everything together

Ready for Chapter 1? Let's learn MCP! ⚡