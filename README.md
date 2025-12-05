# 🚀 Jr Dev Agent v2 (MCP-Only)

**AI-Powered Development Agent via Model Context Protocol (MCP)**

**Accelerate AI Adoption with Spec-Driven Development**

Jr Dev Agent bridges the gap between traditional project management and modern AI-assisted coding. By transforming standardized Jira tickets into context-rich, agent-ready prompts, it enables a **spec-driven workflow** where Engineering Managers, Product Owners, and Developers can define requirements that AI agents can flawlessly implement.

Simply type `@jrdev prepare_agent_task CEPG-12345` to trigger a sophisticated pipeline that:
*   **Extracts** structured requirements from dynamic templates.
*   **Enriches** context with historical knowledge from our Synthetic Memory.
*   **Optimizes** instructions using the Prompt Effectiveness Scoring System (PESS).

The result is a precise, actionable prompt injected directly into your IDE, empowering every developer—regardless of their AI experience—to ship high-quality code faster.

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
│                 │              │
└─────────────────┘              │
                    ┌────────────┼────────────┐
                    │            │            │
            ┌───────▼────┐ ┌─────▼─────┐ ┌───▼────────────┐
            │    PESS    │ │ Synthetic │ │   PromptBuilder│
            │  Scoring   │ │  Memory   │ │   + Templates  │
            │   System   │ │  (MVP FS) │ │                │
            └────────────┘ └───────────┘ └────────────────┘
```

## 🧠 Core Components

### 1. 🎯 **Universal MCP Orchestrator** 
The central nervous system of the agent, serving as a high-throughput request router and workflow coordinator. It abstracts IDE-specific implementations into a unified protocol, enabling seamless, consistent agent capabilities across VS Code, Cursor, Windsurf, and any future MCP-compliant environments.

### 2. 🧠 **Synthetic Memory Engine**
An advanced knowledge persistence layer that enables the agent to "learn" from past iterations. It automatically enriches new tasks with relevant context, historical file patterns, and architectural relationships, featuring robust type safety and self-healing capabilities to maintain data integrity across evolving schema versions.

### 3. 📊 **PESS Intelligence Layer** 
An integrated Prompt Effectiveness Scoring System that quantitatively evaluates the quality of every generated prompt. By analyzing execution outcomes, it identifies gaps in template clarity and context, creating a feedback loop that signals when and how templates should be evolved to maintain high agent success rates.

### 4. 🧱 **Adaptive PromptBuilder**
A hybrid deterministic/generative engine that constructs high-fidelity prompts. It dynamically parses ephemeral template schemas embedded directly within Jira descriptions, allowing teams to define and evolve their specification standards on the fly without code changes.

### 5. 🔗 **Resilient Integration Layer**
A fault-tolerant gateway that seamlessly bridges your IDE with enterprise tools like Jira. It features an intelligent multi-tiered fallback system, ensuring uninterrupted development workflows even during API outages or completely offline scenarios via local template overrides.

### 6. 🌐 **Cross-IDE Compatibility**
Works with VS Code, Cursor, Windsurf, and any MCP-aware IDE.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- MCP-compatible IDE (VS Code, Cursor, Windsurf)
- Jira access (or use **manual fallback mode**)
- `pip install -r requirements.txt` must be run inside your virtualenv

### 1. Installation
Clone the repository and set up the server locally to connect it to your IDE.

```bash
git clone https://github.com/your-org/jr-dev-agent.git
cd jr-dev-agent
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

*Note: If you encounter errors with the `python` command, try using `python3` instead, as your system may default to an older version or require the explicit alias.*

### 2. Configuration
```bash
cp config.json.example config.json
# Edit config.json with your settings if needed
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

### 4. IDE Setup (Cursor/VS Code)

Configure `.cursor/mcp.json` (or `.vscode/mcp.json`) to connect to your local Jr Dev Agent server. You can use either STDIO (recommended for local) or SSE (HTTP).

#### Option A: STDIO (Recommended for Local)
This launches the server automatically when you open the IDE.

```json
{
  "mcpServers": {
    "jrdev": {
      "command": "/absolute/path/to/jr-dev-agent/.venv/bin/python",
      "args": ["/absolute/path/to/jr-dev-agent/scripts/mcp_stdio_server.py"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/jr-dev-agent",
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```
*Ensure you update `/absolute/path/to/jr-dev-agent` to your actual path.*

#### Option B: SSE (HTTP)
If you are running the server manually (via `scripts/start_mcp_gateway.py`) or remotely.

```json
{
  "mcpServers": {
    "jrdev-sse": {
      "url": "http://127.0.0.1:8000/mcp",
      "transport": "sse"
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
3. You can then Copy-Paste it into the input box.

#### Manual Fallback (Offline Mode) 🛠️
If the Jira MCP server is unavailable or you want to test locally without Jira:
1. Create a `jira_ticket_template.txt` file in your **project root directory**.
2. Paste your ticket details using the provided format.
3. Run the command: `@jrdev prepare_agent_task CEPG-12345`.
4. The agent will automatically read this file and send its content to the MCP server, enabling offline/remote fallback support.

#### Workflow
The system will:
1. 🎫 Fetch Jira ticket metadata (or read from fallback)
2. 🧱 Build structured prompt using templates  
3. 🧠 Enrich with Synthetic Memory context
4. 📝 Return ready-to-run prompt
5. ⚡ **Execute the prompt with the AI Agent**

## 📋 Commands

| Command | Description |
|---------|-------------|
| `@jrdev prepare_agent_task ID` | Generate agent-ready prompt for ticket |
| Health endpoint: `GET /health` | Check server status |
| MCP finalize tool | `/mcp/tools/call` with `finalize_session` |

For scripted demos use `python scripts/demo_mcp_workflow.py`.

## 🧠 Synthetic Memory System

The system automatically creates a learning knowledge base in `syntheticMemory/`.

**Memory Enrichment** automatically adds context like:
- 🔗 Related files and features you've worked on before
- 📊 Complexity scores and relationships
- 🎯 Connected features and dependencies

## 🧪 Development & Testing

- **Run the full E2E lifecycle test:**
  ```bash
  # Verifies fallback flow, memory enrichment, and prompt generation
  python tests/e2e/test_full_lifecycle_with_memory.py
  ```
- **Run integration smoke test:**
  ```bash
  pytest tests/integration/test_mcp_gateway_endpoints.py
  ```
- Enable fallback-only mode by exporting `DEV_MODE=true`.

## 📁 Project Structure

```
jr-dev-agent/
├── config.json              # Configuration
├── jr_dev_agent/           # Main application
│   ├── server/              # Server components
│   │   ├── main.py          # FastAPI app
│   │   └── mcp_gateway.py   # MCP Protocol Handler
│   ├── tools/               # MCP Tools (prepare, finalize, health)
│   ├── services/            # Core services
│   │   ├── prompt_builder.py # Hybrid prompt builder
│   │   ├── synthetic_memory.py # Memory System
│   │   └── template_engine.py  # Template Logic
│   ├── graph/               # LangGraph workflow
│   └── fallback/            # Development fallbacks
│       ├── jira_prompt.json         # JSON Fallback
│       └── jira_ticket_template.txt # Manual Text Fallback
├── syntheticMemory/         # Learning knowledge base
├── scripts/                 # Development tools
└── tests/                   # Test suites
    ├── e2e/                 # End-to-end scenarios
    └── integration/         # Integration tests
```

## 🔄 Migration from v1

v2 maintains full backwards compatibility with v1 while adding:
- ✅ Cross-IDE MCP compatibility
- ✅ Simplified single-server architecture  
- ✅ Filesystem-based Synthetic Memory MVP
- ✅ **Robust Manual Fallback for Offline Dev**
- ✅ **Dynamic Template Parsing from Jira Descriptions**

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Run tests: `python tests/e2e/test_full_lifecycle_with_memory.py`
4. Commit changes
5. Push branch and Open Pull Request

## 📄 License

This project is licensed under the MIT License.
