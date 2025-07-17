# 🚀 Jr Dev Agent

**AI-Powered Junior Developer Agent with Copilot Agent Mode & LangGraph MCP Controller**

Transform Jira tickets into working pull requests through AI-powered automation. Simply type `/jr_dev CEPG-12345` in VS Code and receive a complete PR with minimal manual intervention.

## 🏗️ System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   VS Code       │    │   LangGraph     │    │   PromptBuilder │
│   Extension     │◄──►│   MCP Server    │◄──►│   Service       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                    ┌───────────┼───────────┐
                    │           │           │
            ┌───────▼────┐ ┌───▼────┐ ┌───▼────────────┐
            │    PESS    │ │Synthetic│ │    Copilot     │
            │  Scoring   │ │ Memory  │ │  Agent Mode    │
            │   System   │ │ System  │ │   Integration  │
            └────────────┘ └────────┘ └────────────────┘
```

## 🧠 Core Components

### 1. 🧠 LangGraph MCP Server
Central orchestration engine with Router + Workers pattern using LangGraph DAG

### 2. 📊 PESS (Prompt Effectiveness Scoring System)
Intelligence layer with 8-dimensional scoring system for continuous improvement

### 3. 🧱 PromptBuilder
Template-based prompt generation with 9 template families for different task types

### 4. 🧠 Synthetic Memory System
Long-term contextual understanding using Qdrant vector database for RAG capabilities

### 5. 💻 VS Code Extension
Developer interface with seamless Copilot Chat integration

### 6. 🌀 Session Management
Stateful lifecycle tracking with follow-up prompt support

### 7. 🔁 Template Intelligence
Self-improving template evolution with automated optimization

### 8. 🔧 Infrastructure & DevOps
Supporting cloud infrastructure with monitoring and security

## 🚀 Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd Jr-dev-agent

# Setup development environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
# Edit .env with your configuration

# Start the development environment
docker-compose up -d

# Run the LangGraph MCP Server
python -m langgraph_mcp.server
```

## 📁 Project Structure

```
Jr-dev-agent/
├── 🧠 langgraph_mcp/          # LangGraph MCP Server
│   ├── nodes/                 # LangGraph DAG nodes
│   ├── api/                   # FastAPI endpoints
│   ├── fallback/              # Jira fallback files
│   └── server.py              # Main server entry point
├── 📊 pess/                   # PESS Scoring System
│   ├── pipeline/              # 5-stage scoring pipeline
│   ├── dimensions/            # 8-dimensional scoring
│   └── database/              # Score storage
├── 🧱 promptbuilder/          # PromptBuilder Service
│   ├── templates/             # 9 template families
│   ├── engine/                # Template processing
│   └── api/                   # Template generation API
├── 🧠 synthetic_memory/       # Synthetic Memory System
│   ├── embeddings/            # Vector embeddings
│   ├── qdrant/                # Qdrant vector database
│   ├── graph/                 # File-feature graph
│   └── cli/                   # SMS debug tools
├── 💻 vscode_extension/       # VS Code Extension
│   ├── src/                   # TypeScript source
│   ├── package.json           # Extension manifest
│   └── webpack.config.js      # Build configuration
├── 🌀 session_management/     # Session Management
│   ├── lifecycle/             # Session lifecycle
│   ├── events/                # Event tracking
│   └── finalization/          # Session finalization
├── 🔁 template_intelligence/  # Template Intelligence
│   ├── updater/               # Template updater agent
│   ├── splitter/              # Subtask split agent
│   └── analyzer/              # Performance analyzer
├── 🔧 infrastructure/         # Infrastructure & DevOps
│   ├── docker/                # Docker configurations
│   ├── k8s/                   # Kubernetes manifests
│   ├── terraform/             # Infrastructure as Code
│   └── monitoring/            # Observability setup
├── 📋 docs/                   # Documentation
├── 🧪 tests/                  # Test suites
├── 🔧 scripts/                # Utility scripts
└── 📦 config/                 # Configuration files
```

## 🔧 Development Environment

### Prerequisites
- Python 3.9+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL
- Redis

### Environment Setup

1. **Clone and Setup**
```bash
git clone <repository-url>
cd Jr-dev-agent
python -m venv venv
source venv/bin/activate
```

2. **Install Dependencies**
```bash
pip install -r requirements.txt
cd vscode_extension && npm install
```

3. **Configure Environment**
```bash
cp .env.example .env
# Edit .env with your OpenAI API key, Jira credentials, etc.
```

4. **Start Services**
```bash
docker-compose up -d  # Start PostgreSQL, Redis, Qdrant
python -m langgraph_mcp.server  # Start MCP Server
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific component tests
pytest tests/test_langgraph_mcp/
pytest tests/test_pess/
pytest tests/test_promptbuilder/

# Run integration tests
pytest tests/integration/
```

## 📊 Monitoring & Observability

- **Health Checks**: `http://localhost:8000/health`
- **Metrics**: Prometheus metrics at `http://localhost:8000/metrics`
- **Logs**: Centralized logging with structured JSON format
- **Tracing**: Distributed tracing with OpenTelemetry

## 🔒 Security

- API key authentication for all endpoints
- Secure token management for Jira integration
- Data encryption at rest and in transit
- No PII storage in embeddings or logs

## 🚀 Deployment

### Local Development
```bash
docker-compose up -d
python -m langgraph_mcp.server
```

### Production
```bash
# Build and deploy with Kubernetes
kubectl apply -f infrastructure/k8s/
```

## 📖 Documentation

- **Architecture**: See `docs/architecture.md`
- **API Reference**: See `docs/api.md`
- **User Guide**: See `docs/user-guide.md`
- **Contributing**: See `docs/contributing.md`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📝 License

This project is proprietary and confidential. All rights reserved.

## 🆘 Support

For support and questions:
- Internal Documentation: `docs/`
- Issue Tracker: GitHub Issues
- Team Contact: [team contact info]

---

**🎯 Ready to transform how we develop software with AI-powered automation!** 