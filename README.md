# 🚀 Jr Dev Agent v2 (MCP-Only)

**AI-Powered Development Agent via Model Context Protocol (MCP)**

Transform Jira tickets into working pull requests through AI automation. Simply type `/jrdev CEPG-12345` in any MCP-compatible IDE and receive a complete, agent-ready prompt for immediate execution.

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

### 3. Start Server
```bash
python scripts/start_mcp_gateway.py --dev
```

### 4. IDE Setup
Configure your MCP-compatible IDE to connect to: `http://localhost:8000`

### 5. Usage
In your IDE chat, type:
```
/jrdev CEPG-12345
```

The system will:
1. 🎫 Fetch Jira ticket metadata
2. 🧱 Build structured prompt using templates  
3. 🧠 Enrich with Synthetic Memory context
4. 📝 Return ready-to-run prompt for Agent Mode
5. ⚡ You press Enter → AI Agent executes changes

## 📋 Commands

| Command | Description |
|---------|-------------|
| `/jrdev TICKET-ID` | Generate agent-ready prompt for ticket |
| Health endpoint: `GET /health` | Check server status |
| Finalize: `POST /v2/jrdev/finalize` | Complete session & trigger PESS scoring |

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

### Run Tests
```bash
# Test v2 MCP Orchestrator
python scripts/test_v2_mcp_orchestrator.py

# Test v1 compatibility  
python scripts/test_mcp_gateway.py

# Test with fallback data
python scripts/test_mvp_fallback.py
```

### Development Mode
```bash
export DEV_MODE=true
python scripts/start_mcp_gateway.py --dev
```

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

## 🔧 Configuration

Key configuration options in `config.json`:

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