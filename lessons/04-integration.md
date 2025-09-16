# Chapter 4: Integration & Testing

## Objective
Verify that our complete system works end-to-end:
- MCP server is connected to Qodo Command
- Agent calls MCP when executed
- MCP server handles tool calls correctly
- Agent produces high-quality analysis

We're at the last chapter in this workshop! Congrats!

Let's review what we've accomplished so far:

1. Set up keyword search functionality for an MCP server
2. Built the MCP server
3. Built an AI agent

Now, we can connect the local MCP server to Qodo Command, our CLI tool.

In Qodo Command, we'll confirm that the MCP server shows up in the list of available tools.

When we run the AI agent, we'll provide a keyword to begin a codebase search.

This codebase search will trigger the MCP tool call and will execute the instructions from the agent with the enhanced functionality from the MCP to provide high quality results in a JSON file.

To integrate the MCP with Qodo Command so that the agent knows it exists as an available tool to use, we need to first add the local MCP to `mcp.json`.

Use this code snippet to copy/paste into `mcp.json`:

```json
{
  "mcpServers": {
    "workshop-mcp": {
      "command": "poetry",
      "args": ["run", "workshop-mcp-server"],
      "cwd": "/Users/{LAPTOP_USERNAME_HERE}/python-mcp-agent-workshop"
    }
  }
}
```

> **WARNING!**
Depending on your machine, the `cwd` (current working directory) will need to match the current working directory on your own local machine that will point to this repository!

For example, my code exists in `/Users/nnennandukwe/Code/python-mcp-agent-workshop`. Therefore, that is what I'd use as the string for `cwd` in the JSON code snippet.

To verify that the keyword search MCP is integrated successfully, let's run the MCP server.

```bash
poetry run workshop-mcp-server
```

Next, let's start up Qodo Command in a separate terminal tab:

```bash
qodo
```

In Qodo Command's chat interface, use the `/` (forward slash) to find the `list-mcp` command for listing all available MCPs.

At the bottom of the list under "Remote MCPs", you should find `workshop_mcp` listed with the description of the tools available.

In another separate terminal tab, let's test the agent and the MCP using an example keyword to search the codebase:

```bash
qodo keyword_analysis --set keyword="python"
```

As the agent runs, you should see an approval message display, requesting your permission to approve the MCP tool call.

Approve the tool and allow the analysis to execute and produce a JSON file with the results/output.

Feel free to test the agent with other keywords such as:

```bash
# Test with a simple keyword
qodo keyword_analysis --set keyword="class"

# Test with async keyword
qodo keyword_analysis --set keyword="async"
```

The agent should provide:

- ✅ Structured analysis of keyword distribution
- ✅ Identification of the most relevant file
- ✅ Insights about code organization
- ✅ Actionable recommendations

Agent example output:

```json
{
    "success": true,
    "file_path": "/path/to/src/workshop_mcp/keyword_search.py",
    "keyword_count": 12,
    "file_summary": "This file contains the KeywordSearchTool class implementation with extensive async operations...",
    "explanation": "This file contains the most 'async' keywords because it implements the core asynchronous file processing logic. The high concentration suggests this is the right architectural choice for I/O-intensive operations..."
}
```

## Key Agent Concepts Learned

- ✅ Natural Language Programming: Instructions define agent behavior
- ✅ Tool Integration: Agent knows how to use your MCP server
- ✅ Structured Thinking: Process guides lead to better analysis
- ✅ Schema-Driven Output: Consistent, parseable results

## Summary The Magic Moment 🎉

Your agent is now using YOUR tool to provide intelligent analysis!

1. You built the keyword search functionality
2. You wrapped it in MCP protocol
3. You programmed an AI to use it intelligently

Congratulations! You've built a complete AI agent system from scratch! 🎉