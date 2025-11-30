# MCP Setup Guide

## Overview

The Jr Dev Agent uses a two-process architecture for MCP integration:

1. **MCP Gateway Server** (HTTP) - The main backend that runs continuously
2. **MCP STDIO Bridge** (STDIO) - Connects your IDE to the gateway

## Setup Instructions

### Step 1: Start the MCP Gateway Server

The gateway must be running **before** you use `@jrdev` commands in Cursor.

```bash
# Start the gateway server (runs on http://127.0.0.1:8000)
python scripts/start_mcp_gateway.py
```

Keep this running in a terminal. You should see:

```
🚀 Starting MCP Gateway server on 0.0.0.0:8000
📚 API Docs: http://0.0.0.0:8000/docs
```

### Step 2: Verify MCP Configuration

The `.cursor/mcp.json` file should be configured to use the STDIO bridge:

```json
{
  "mcpServers": {
    "jrdev": {
      "command": "${workspaceFolder}/.venv/bin/python",
      "args": [
        "${workspaceFolder}/scripts/mcp_stdio_server.py"
      ],
      "env": {
        "PYTHONPATH": "${workspaceFolder}",
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

### Step 3: Use @jrdev Commands in Cursor

Now you can use the Jr Dev Agent directly in Cursor's chat:

```
@jrdev prepare_agent_task CEPG-67890
```

This will:
1. Connect to the running MCP gateway via STDIO bridge
2. Fetch the Jira ticket data
3. Generate an AI-optimized prompt
4. **Insert the prompt into your chat textbox** (not as a response)
5. You just press Enter to execute!

## Architecture Diagram

```
┌─────────────┐
│   Cursor    │
│   Chat UI   │
└──────┬──────┘
       │ @jrdev command
       │
       ▼
┌──────────────────┐      HTTP      ┌─────────────────┐
│  MCP STDIO       │◄───────────────►│  MCP Gateway    │
│  Bridge          │     Requests    │  Server         │
│  (per-command)   │                 │  (always-on)    │
└──────────────────┘                 │  :8000          │
                                     └────────┬────────┘
                                              │
                                     ┌────────┴────────┐
                                     │                 │
                              ┌──────▼──────┐   ┌─────▼──────┐
                              │  LangGraph  │   │ Synthetic  │
                              │  Workflow   │   │  Memory    │
                              └─────────────┘   └────────────┘
```

## Troubleshooting

### Error: "Gateway unreachable"

**Problem**: The MCP gateway server is not running.

**Solution**: Start the gateway server:
```bash
python scripts/start_mcp_gateway.py
```

### Error: "STDIO server failed"

**Problem**: The STDIO bridge can't communicate with the gateway.

**Solution**: 
1. Verify the gateway is running on port 8000
2. Check no firewall is blocking localhost connections
3. Restart Cursor to reset the MCP connection

### Prompt appears as response, not in textbox

**Problem**: The prompt is shown in chat history instead of being injected into the input box.

**Solution**: This should work automatically with the current setup! If it doesn't:

1. **Check Cursor version**: You need Cursor 1.3.5 or newer
   - Go to Cursor → About to check version
   - Update if needed

2. **Restart Cursor completely**:
   - Close all Cursor windows
   - Restart Cursor
   - MCP configuration changes require a full restart

3. **Verify the response includes chat_injection**:
   - Check that the response has a `chat_injection` field
   - Run the demo script to see the full response structure:
     ```bash
     python scripts/demo_mcp_workflow.py --ticket CEPG-67890
     ```

4. **Check Cursor logs**:
   - Look in `~/.cursor/logs/` for MCP-related errors
   - Search for "mcp" or "chat_injection" in the logs

If none of this works, your teammate who got it working in VS Code can help verify the setup!

## Development Mode

For development with auto-reload:

```bash
python scripts/start_mcp_gateway.py --dev
```

## Health Check

Verify the gateway is running:

```bash
curl http://127.0.0.1:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "langgraph": "available",
    "session_manager": "available",
    "fallback_system": "available"
  }
}
```

