# 🚀 Jr Dev Agent v2 (MCP-Only)

**AI-Powered Development Agent via Model Context Protocol (MCP)**

Transform Jira tickets into working pull requests through AI automation. Simply type `@jrdev prepare_agent_task CEPG-12345` in any MCP-compatible IDE and receive a complete, agent-ready prompt injected directly into your chat input box.

> **⚠️ IMPORTANT**: The MCP gateway must be **running separately** before using `@jrdev` commands.  
> Start it once with: `python scripts/start_mcp_gateway.py` and keep it running.  
> The IDE then connects via the STDIO bridge (configured in `.cursor/mcp.json`).

## 🏗️ v2 Architecture (MCP-Only)

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   VS Code       │    │   Jr Dev Agent  │    │   Jira API      │
│   Cursor        │◄──►│   MCP Server    │◄──►│   Integration   │
│   Windsurf      │    │                 │    │                 │
│   Any MCP IDE   │    └─────────┬───────┘    └─────────────────┘
└─────────────────┘              │
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
            ┌───────▼────┐ ┌─────▼─────┐ ┌───▼────────────┐
            │    PESS    │ │ Synthetic │ │   PromptBuilder│
            │  Scoring   │ │  Memory   │ │   + Templates  │
            │   System   │ │  (MVP FS) │ │                │
            └────────────┘ └───────────┘ └────────────────┘
```

## 🧠 Core Components

### 1. 🎯 **MCP Orchestrator** 
Central request router and workflow coordinator for `/jrdev` commands across all IDEs

### 2. 🧠 **Synthetic Memory MVP**
Filesystem-based knowledge store (`syntheticMemory/`) with automatic context enrichment and vector DB upgrade path

### 3. 📊 **PESS Integration** 
Prompt Effectiveness Scoring System for continuous improvement and telemetry

### 4. 🧱 **PromptBuilder (Hybrid)**
Deterministic template filling with optional LLM assist for tone/scoping/edge cases

### 5. 🔗 **Jira Integration**
Fetches ticket metadata including YAML prompt templates embedded in descriptions

### 6. 🌐 **Cross-IDE Compatibility**
Works with VS Code, Cursor, Windsurf, and any MCP-aware IDE

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- MCP-compatible IDE (VS Code, Cursor, Windsurf)
- Jira access (or use fallback mode)
- `pip install -r requirements.txt` must be run inside your virtualenv (the repo includes a lightweight `langgraph/` stub so no extra install is required for that dependency when running offline)

### 1. Installation
```bash
git clone https://github.com/your-org/jr-dev-agent.git
cd jr-dev-agent
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configuration
```bash
cp config.json.example config.json
# Edit config.json with your Jira settings
```

### 3. Start MCP Gateway Server

⚠️ **IMPORTANT**: The MCP gateway must be running BEFORE you use `@jrdev` commands.

```bash
# Start the gateway (keep this running in a separate terminal)
python scripts/start_mcp_gateway.py
```

You should see:
```
🚀 Starting MCP Gateway server on 0.0.0.0:8000
📚 API Docs: http://0.0.0.0:8000/docs
```

The server will run continuously. Keep this terminal open.

### 4. IDE Setup (Cursor)

The `.cursor/mcp.json` file is pre-configured to connect to the gateway via STDIO bridge:

```json
{
  "mcpServers": {
    "jrdev": {
      "command": "${workspaceFolder}/.venv/bin/python",
      "args": ["${workspaceFolder}/scripts/mcp_stdio_server.py"],
      "env": {
        "PYTHONPATH": "${workspaceFolder}",
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

**No additional setup needed!** Cursor will automatically use this configuration.

### 5. Usage

#### Option A: Tool (Recommended for Cursor)
In Cursor chat, type:
```
@jrdev prepare_agent_task CEPG-12345
```
1. The system executes and displays the generated prompt as a **Result Block**.
2. **Click Copy** on the result block.
3. Paste into the chat input box and press Enter.

#### Option B: Prompt (Slash Command)
In Cursor chat, type `/` and select `jrdev/prepare_agent_task`.
1. Enter the `ticket_id` when prompted.
2. Cursor will execute the prompt and insert the result into the **Chat History**.
3. You can then Copy-Paste it into the input box (Cursor does not yet support auto-filling the input box from prompts).

#### Workflow
The system will:
1. 🎫 Fetch Jira ticket metadata
2. 🧱 Build structured prompt using templates  
3. 🧠 Enrich with Synthetic Memory context
4. 📝 Return ready-to-run prompt
5. ⚡ **Execute the prompt with the AI Agent**

**Note**: Due to current Cursor MCP limitations, the prompt appears as a response (not injected into the input box). Simply copy-paste it into a new message to execute.

### 6. Local Demo (optional)
With the server running you can exercise the entire workflow without curl:
```bash
python scripts/demo_mcp_workflow.py --ticket CEPG-67890 --session demo-session
```
This prints the tool list, generated prompt, mock PESS score, and the Confluence template update (stored under `syntheticMemory/_confluence_updates/`).

## 📋 Commands

| Command | Description |
|---------|-------------|
| `/jrdev TICKET-ID` | Generate agent-ready prompt for ticket |
| Health endpoint: `GET /health` | Check server status |
| MCP finalize tool | `/mcp/tools/call` with `finalize_session` to record feedback and scores |

For scripted demos use `python scripts/demo_mcp_workflow.py`.

## 🧠 Synthetic Memory System

The system automatically creates a learning knowledge base:

```
syntheticMemory/
├── features/
│   ├── new_feature/
│   │   └── CEPG-12345/
│   │       ├── summary.json      # Ticket metadata
│   │       ├── files.json        # File relationships  
│   │       ├── graph.json        # Connected features
│   │       ├── agent_run.json    # PESS results
│   │       └── README.md         # Human context
│   └── ...
```

**Memory Enrichment** automatically adds context like:
- 🔗 Related files and features you've worked on before
- 📊 Complexity scores and relationships
- 🎯 Connected features and dependencies

## 📊 PESS Scoring

After each PR, get automated feedback:
- **Prompt Score**: How effective was the generated prompt?
- **Clarity Rating**: Was the instruction clear and actionable?
- **Risk Score**: Potential issues or improvements
- **Recommendations**: How to improve future prompts

## 🧪 Development & Testing

- Run the integration smoke test:
  ```bash
  pytest tests/integration/test_mcp_gateway_endpoints.py
  ```
- For manual demos start the gateway (`python scripts/start_mcp_gateway.py`) and run `python scripts/demo_mcp_workflow.py`.
- Enable fallback-only mode by exporting `DEV_MODE=true` before launching the server.

## 📁 Project Structure

```
jr-dev-agent/
├── config.json              # Configuration
├── langgraph_mcp/           # Main application
│   ├── server/main.py       # FastAPI server
│   ├── mcp/                 # v2 MCP Orchestrator
│   │   ├── handlers/        # Command handlers
│   │   ├── jira_client.py   # Jira integration
│   │   ├── prompt_builder.py # Hybrid prompt builder
│   │   ├── memory.py        # Synthetic Memory
│   │   └── pess_client.py   # PESS integration
│   ├── graph/               # LangGraph workflow (v1)
│   ├── services/            # Core services
│   └── fallback/            # Development fallbacks
├── syntheticMemory/         # Learning knowledge base
├── scripts/                 # Development tools
└── tests/                   # Test suites
```

## 🔧 Configuration & MCP Secrets

Key configuration options live in `config.json` (used mainly for the filesystem synthetic memory backend). When connecting to the enterprise MCP servers supply the following environment variables before starting the gateway:

```bash
export JIRA_MCP_URL="https://mcp-jira.stage.walmart.com/mcp/"
export JIRA_MCP_TOKEN="Bearer <PINGFED_TOKEN>"
export CONFLUENCE_MCP_URL="https://mcp-confluence.stage.walmart.com/mcp/"
export CONFLUENCE_MCP_TOKEN="Bearer <PINGFED_TOKEN>"
```

If these are not set the gateway automatically falls back to the local `langgraph_mcp/fallback/jira_prompt.json` ticket data and writes Confluence updates to `syntheticMemory/_confluence_updates/`.

The default `config.json` controls the synthetic memory backend:

```json
{
  "memory": {
    "backend": "fs",              // "fs" or "vector"
    "fs": {
      "root_dir": "syntheticMemory"
    }
  },
  "jira": {
    "base_url": "https://your.atlassian.net",
    "token": "your-token"
  },
  "pess": {
    "url": "https://your-pess-server.com",
    "enabled": true
  }
}
```

## 🚀 Deployment

### Docker
```bash
docker build -t jr-dev-agent -f langgraph_mcp/Dockerfile .
docker run -p 8000:8000 jr-dev-agent
```

### Production
- Set `DEV_MODE=false`
- Configure proper Jira credentials
- Set up PESS scoring endpoint
- Enable vector DB for Synthetic Memory scaling

## 🔄 Migration from v1

v2 maintains full backwards compatibility with v1 while adding:
- ✅ Cross-IDE MCP compatibility (vs. VS Code-only)
- ✅ Simplified single-server architecture  
- ✅ Filesystem-based Synthetic Memory MVP
- ✅ Improved PESS integration
- ✅ No extension installation required

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Run tests: `python scripts/test_v2_mcp_orchestrator.py`
4. Commit changes: `git commit -m 'Add amazing feature'`
5. Push branch: `git push origin feature/amazing-feature`
6. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- 📧 Email: support@jr-dev-agent.com
- 💬 Slack: #jr-dev-agent
- 🐛 Issues: [GitHub Issues](https://github.com/your-org/jr-dev-agent/issues)
- 📖 Docs: [Documentation](https://docs.jr-dev-agent.com)

---

**🎉 Jr Dev Agent v2 - From Jira Ticket to Working PR in seconds!**
