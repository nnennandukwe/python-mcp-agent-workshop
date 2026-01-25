# External Integrations

**Analysis Date:** 2026-01-25

## APIs & External Services

**Model Context Protocol (MCP):**
- MCP Protocol - Communication standard for AI agents
  - Protocol: JSON-RPC 2.0 over stdio with Content-Length framing
  - Transport: stdin/stdout only (no network connections)
  - Implementation: Custom from scratch (no external SDK dependency)
  - Location: `src/workshop_mcp/server.py`

**AI Agents:**
- Gemini 2.5 Pro (documented in CLAUDE.md as typical integration)
  - Expected to connect via MCP protocol
  - No SDK or client library required - communicates via stdin/stdout
  - Optional: Qodo agent framework mentioned for performance analysis

**No External HTTP APIs:**
- No REST API integrations (requests, urllib, httpx, etc.)
- No webhook outbound calls
- No third-party SaaS integrations

## Data Storage

**Databases:**
- None - Project has no database integrations
- No SQL, NoSQL, or document store dependencies
- No ORM libraries (SQLAlchemy, Django ORM, etc.)

**File Storage:**
- Local filesystem only
  - Read-only access via standard Python pathlib and os modules
  - Keyword Search tool recursively searches local directories
  - Performance Profiler analyzes local Python files
  - No cloud storage (S3, GCS, Azure Blob, etc.)

**Caching:**
- None - No caching layer (Redis, Memcached, etc.)
- No in-memory cache library

## Authentication & Identity

**Auth Provider:**
- Custom implementation - No external auth provider
  - MCP protocol itself handles agent capability negotiation
  - initialize() method exchanges protocol version and capabilities
  - No OAuth, JWT, or third-party identity provider needed

**Secrets Management:**
- .env file (local configuration only)
  - Contains: GITHUB_PAT_TOKEN (optional, not used by core application logic)
  - No external secrets vault (HashiCorp Vault, AWS Secrets Manager, etc.)
  - Not required for application functionality

## Monitoring & Observability

**Error Tracking:**
- None - No error tracking service (Sentry, Rollbar, etc.)
- Errors logged to stderr via Python logging module

**Logs:**
- Python logging module (standard library)
  - Configured in `src/workshop_mcp/server.py`:
    ```python
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )
    ```
  - Output: stderr
  - No log aggregation service (ELK, Datadog, CloudWatch, etc.)

**Metrics & Observability:**
- None - No metrics collection, APM, or observability platform

## CI/CD & Deployment

**Hosting:**
- stdio-based server (runs locally or in agent environment)
- No cloud platform deployment (AWS Lambda, Google Cloud Run, etc.)
- Entry point: `poetry run workshop-mcp-server` or direct Python invocation

**CI Pipeline:**
- Not detected in codebase
- Pre-commit hooks configured (.pre-commit-config.yaml) for local development
- No GitHub Actions, GitLab CI, CircleCI, or other CI/CD detected

**Build:**
- Poetry build system via `poetry build`
- No Docker configuration (no Dockerfile detected)
- No deployment configuration files (Kubernetes, Terraform, etc.)

## Environment Configuration

**Required env vars:**
- GITHUB_PAT_TOKEN - Optional, present in .env but not used by core application

**Optional configuration:**
- No environment variables required for standard operation
- Application operates with no external service dependencies

**Secrets location:**
- `.env` file in repository root (local development only)
- Not production-ready for secrets management
- Should use proper secrets vault in production environments

## Communication Patterns

**Incoming (Client → Server):**
- MCP Protocol via stdin
  - initialize - Capability handshake
  - list_tools - Discover available tools
  - call_tool - Execute specific tool (keyword_search or performance_check)

**Tool Invocations:**

1. **keyword_search Tool:**
   - Receives: keyword, root_paths, optional case_insensitive, use_regex, include_patterns, exclude_patterns
   - Executes: Local file system traversal and pattern matching
   - Returns: JSON with search results and statistics
   - Location: `src/workshop_mcp/keyword_search.py`

2. **performance_check Tool:**
   - Receives: Either file_path or source_code string
   - Executes: AST analysis via Astroid semantic parser
   - Returns: JSON with detected performance issues and suggestions
   - Location: `src/workshop_mcp/performance_profiler/performance_checker.py`

**Outgoing (Server → Client):**
- MCP Protocol responses via stdout
  - JSON-RPC result messages
  - JSON-RPC error messages
  - No outbound HTTP calls or webhook callbacks

## Data Flow

```
AI Agent (Gemini 2.5 Pro, etc.)
    ↓
    MCP Client (stdin/stdout)
    ↓
WorkshopMCPServer (server.py)
    ├─→ initialize() → Capability handshake
    ├─→ list_tools() → Tool definitions
    └─→ call_tool() → Route to:
        ├─→ KeywordSearchTool (keyword_search.py)
        │   ├─→ os.walk() → Local file traversal
        │   ├─→ aiofiles → Async file reading
        │   ├─→ re.compile() → Pattern matching
        │   └─→ Return results JSON
        └─→ PerformanceChecker (performance_checker.py)
            ├─→ astroid.parse() → AST analysis
            ├─→ ASTAnalyzer (ast_analyzer.py) → Code inspection
            ├─→ Pattern matching (patterns.py)
            └─→ Return issues JSON
```

## Third-Party Integrations

**None** - This project has zero external service dependencies.

The application is completely self-contained:
- No API calls to external services
- No database connections
- No authentication providers
- No monitoring/logging backends
- No package repositories beyond PyPI (via Poetry)
- No cloud platform dependencies

This design makes the project ideal for:
- Educational/learning purposes
- Offline operation
- Deployment in restricted environments
- Minimal security surface area
- Zero operational dependencies

---

*Integration audit: 2026-01-25*
