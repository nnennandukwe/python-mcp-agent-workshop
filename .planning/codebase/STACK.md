# Technology Stack

**Analysis Date:** 2026-01-25

## Languages

**Primary:**
- Python 3.10+ (configured in `pyproject.toml` as `python = ">=3.10,<4.0"`)
  - Used for all application logic, MCP server implementation, tools, and tests
  - Target version for type checking: Python 3.11 (see `pyproject.toml` [tool.mypy] section)

## Runtime

**Environment:**
- CPython 3.9.6+ (system default, but project requires 3.10+)
- asyncio - Standard library async runtime used in MCP server and keyword search tool

**Package Manager:**
- Poetry 2.3.1+
  - Lockfile: `poetry.lock` present and generated
  - Dependency management configuration in `pyproject.toml`

## Frameworks

**Core:**
- Model Context Protocol (MCP) - Custom implementation without official SDK
  - Implements JSON-RPC 2.0 protocol over stdio with Content-Length framing
  - Location: `src/workshop_mcp/server.py`
  - Provides standard MCP methods: initialize, list_tools, call_tool

**Analysis & AST:**
- Astroid 3.3.11 - Advanced abstract syntax tree parser for semantic Python code analysis
  - Provides type inference, call resolution, cross-module understanding
  - Used by Performance Profiler tool to detect code anti-patterns
  - Location: `src/workshop_mcp/performance_profiler/ast_analyzer.py`

**Async I/O:**
- aiofiles 23.2.1 - Async file I/O operations
  - Used by KeywordSearchTool for non-blocking file reading
  - Location: `src/workshop_mcp/keyword_search.py`

**Testing:**
- pytest 7.4.0+ - Test runner and framework
  - Configuration: `pyproject.toml` [tool.pytest.ini_options]
  - asyncio_mode: "auto" for async test support
  - 102 tests organized in `tests/` directory

- pytest-asyncio 0.21.0 - Async test support
  - Required for async/await tests with `@pytest.mark.asyncio` decorator

- pytest-cov 5.0.0 - Code coverage reporting
  - Command: `poetry run pytest --cov=workshop_mcp`

**Build/Dev:**
- Black 23.0.0+ - Code formatter
  - Configuration: Line length 88, target version py311
  - Applied to `src/` and `tests/`

- isort 5.12.0+ - Import statement sorter
  - Configuration: Uses Black profile, line length 88
  - Integrates with Black formatting

- mypy 1.5.0+ - Static type checker
  - Configuration: Python 3.11 target, disallow_untyped_defs enabled
  - Strict mode: warn_return_any and warn_unused_configs enabled

## Key Dependencies

**Critical:**
- Astroid 3.3.11 - Semantic Python code analysis for performance profiling
  - Why it matters: Enables detection of performance anti-patterns requiring cross-module understanding
  - Alternative: Standard library ast module lacks type inference and semantic resolution

- aiofiles 23.2.1 - Non-blocking file I/O
  - Why it matters: Enables concurrent file search without blocking the event loop
  - Alternative: Would require threading or multiprocessing for concurrent file operations

**Infrastructure:**
- None - Project has no external service dependencies (no databases, APIs, caching, monitoring)

## Configuration

**Environment:**
- .env file present at repository root
  - Currently contains: GITHUB_PAT_TOKEN (optional, for GitHub access)
  - Not required for core functionality

**Build:**
- `pyproject.toml` - Single source of truth for dependencies, build config, and tool settings
  - Entry point: `workshop-mcp-server` → `workshop_mcp.server:sync_main`
  - No separate setup.py, requirements.txt, or Pipfile

## Platform Requirements

**Development:**
- Python 3.10 or higher
- Poetry 1.2 or higher for dependency management
- Unix-like shell (bash/zsh) for development scripts
- macOS/Linux/Windows (project supports all via poetry)

**Production:**
- Python 3.10 or higher (same as development)
- stdin/stdout available for MCP protocol (runs as stdio server)
- File system read access for keyword search and performance profiler
- No external services required
- No specific OS requirements - pure Python implementation

## Code Style & Tooling

**Code Formatting:**
- Black 23.12.1 - Enforced via pre-commit hook
- Configuration: 88 character line length, Python 3.11 target
- Applied automatically: `poetry run black src/ tests/`

**Linting:**
- Ruff 0.6.9 - Fast Python linter via pre-commit
  - Rules: E, F, W, I, B, UP, S (error, future, warning, import, bugbear, upgrade, security)
  - Fails on violations, no auto-fix

**Import Sorting:**
- isort 5.12.0 - Import organization
  - Profile: Black-compatible
  - Applied automatically: `poetry run isort src/ tests/`

**Type Checking:**
- mypy 1.5.0 - Static type analysis
  - Config: Python 3.11, disallow untyped defs, warn on unused configs
  - Run: `poetry run mypy src/`

**Pre-commit Hooks:**
- File: `.pre-commit-config.yaml` (v1.35.1 compatible)
- Hooks include:
  - Black (Python formatter)
  - Prettier (JS/TS/JSON/YAML/Markdown formatter)
  - shfmt (Shell script formatter)
  - Ruff (Python linter)
  - ESLint (JavaScript linter)
  - yamllint (YAML linter)
  - shellcheck (Shell script linter)
  - detect-secrets (Credential scanning)
  - commitizen (Conventional Commits validation)

---

*Stack analysis: 2026-01-25*
