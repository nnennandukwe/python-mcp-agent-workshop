# Python MCP Agent Workshop - Introduction

## What You'll Build
By the end of this workshop, you'll have created:
- ⚡ **MCP Server**: Keyword search tool using async Python
- 🤖 **AI Agent**: Intelligent code analyst using Qodo
- 🔧 **Complete Integration**: Working agent-tool ecosystem

## Workshop Architecture

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   AI Agent      │───▶│   MCP Server    │───▶│  Keyword Tool   │
│(keyword_analysis│    │   (server.py)   │    │(keyword_search) │
│     .toml)      │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘

## Prerequisites Verified ✅
- Python 3.11+
- Poetry for dependency management
- Qodo Command for agent execution
- Git for version control

## Learning Path
1. **Protocol Foundations** - Build MCP from first principles:
   - [01 - Transport: Framing MCP Messages Over stdio](01-transport.md)
   - [02 - JSON-RPC 2.0: Validating and Routing Requests](02-jsonrpc.md)
   - [03 - Initialize: Capability Handshake](03-initialize.md)
   - [04 - Tools: Advertising and Invoking Capabilities](04-tools.md)
2. **Tool Development** - Building the keyword search functionality
3. **Server Integration** - Wrapping tools in MCP protocol
4. **Agent Configuration** - Creating intelligent analysis behavior
5. **Testing & Integration** - Ensuring everything works together

## Key Concepts
- **MCP (Model Context Protocol)**: Standardized way for AI to interact with tools
- **Async Programming**: Non-blocking file operations for performance
- **Agent Instructions**: Natural language programming for AI behavior
- **Tool Schema**: Structured definitions for AI understanding

Ready to build something amazing? Let's go! 🚀
