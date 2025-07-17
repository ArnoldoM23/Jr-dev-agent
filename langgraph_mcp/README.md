# LangGraph MCP Server

AI-powered orchestration server for the Jr Dev Agent system using LangGraph for workflow management.

## 🚀 Features

- **LangGraph Workflow**: Orchestrates the entire ticket-to-prompt pipeline
- **FastAPI REST API**: Clean REST endpoints for VS Code extension integration
- **Fallback Support**: Seamless integration with existing fallback system
- **Session Management**: Tracks development sessions from start to finish
- **Template Engine**: Intelligent template selection and prompt generation
- **Health Monitoring**: Comprehensive health checks and debugging
- **Development Mode**: Enhanced debugging and development features

## 🏗️ Architecture

### Core Components

1. **FastAPI Server** (`server/main.py`)
   - REST API endpoints
   - Session management
   - Background task processing
   - Health monitoring

2. **LangGraph Workflow** (`graph/jr_dev_graph.py`)
   - State-based workflow orchestration
   - 5-node processing pipeline
   - Error handling and retry logic
   - Performance tracking

3. **Services**
   - **PromptBuilder** (`services/prompt_builder.py`): Generates AI-optimized prompts
   - **TemplateEngine** (`services/template_engine.py`): Manages and selects templates
   - **SessionManager** (`models/session.py`): Tracks session lifecycle

4. **Models**
   - **Ticket Models** (`models/ticket.py`): Pydantic models for ticket data
   - **Prompt Models** (`models/prompt.py`): Request/response models
   - **Session Models** (`models/session.py`): Session state management

## 📋 API Endpoints

### Core Endpoints

- **GET /health** - Health check with service status
- **GET /api/ticket/{ticket_id}** - Fetch ticket metadata
- **POST /api/prompt/generate** - Generate AI-optimized prompt
- **POST /api/session/complete** - Mark session as complete

### Debug Endpoints (Dev Mode Only)

- **GET /api/debug/health** - Detailed health information
- **GET /api/debug/sessions** - View active sessions

## 🎯 LangGraph Workflow

The system uses a 5-node LangGraph workflow:

```
fetch_ticket → select_template → enrich_context → generate_prompt → finalize
```

### Node Details

1. **fetch_ticket**: Retrieves ticket metadata using fallback system
2. **select_template**: Chooses appropriate template based on content
3. **enrich_context**: Adds context from Synthetic Memory (future)
4. **generate_prompt**: Creates final AI-optimized prompt
5. **finalize**: Prepares response and cleanup

## 🔧 Template Engine

### Available Templates

- **feature**: New feature implementation
- **bugfix**: Bug fix procedures
- **refactor**: Code refactoring
- **version_upgrade**: Dependency updates
- **config_update**: Configuration changes
- **schema_change**: Database/GraphQL schema changes
- **test_generation**: Test case creation

### Template Selection

The system automatically selects templates based on:
- Explicit template specification in ticket
- Keyword analysis of summary/description
- Label matching
- Priority weighting

## 📊 Session Management

### Session Lifecycle

1. **Created**: New session initiated
2. **In Progress**: Processing ticket
3. **Completed**: Successfully finished
4. **Failed**: Error occurred
5. **Expired**: Timed out (60 minutes)

### Session Features

- UUID-based session IDs
- Automatic timeout handling
- Progress tracking
- Error logging
- PR URL association

## 🚀 Quick Start

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DEV_MODE=true
export HOST=0.0.0.0
export PORT=8000
```

### Start the Server

```bash
# Method 1: Using the startup script
python scripts/start_mcp_server.py

# Method 2: Direct uvicorn
uvicorn langgraph_mcp.server.main:app --host 0.0.0.0 --port 8000 --reload
```

### Test the Server

```bash
# Run comprehensive tests
python scripts/test_mcp_server.py

# Manual API testing
curl http://localhost:8000/health
curl http://localhost:8000/api/ticket/CEPG-67890
```

## 📝 Usage Examples

### Generate Prompt for Ticket

```python
import aiohttp
import asyncio

async def generate_prompt():
    async with aiohttp.ClientSession() as session:
        # Get ticket data
        async with session.get("http://localhost:8000/api/ticket/CEPG-67890") as response:
            ticket_data = await response.json()
        
        # Generate prompt
        request = {"ticket_data": ticket_data}
        async with session.post("http://localhost:8000/api/prompt/generate", json=request) as response:
            prompt_data = await response.json()
            print(f"Generated prompt: {prompt_data['prompt']}")

asyncio.run(generate_prompt())
```

### VS Code Extension Integration

The server is designed to work with the VS Code extension:

```typescript
// VS Code extension calls
const ticketData = await fetch(`${serverUrl}/api/ticket/${ticketId}`);
const promptData = await fetch(`${serverUrl}/api/prompt/generate`, {
    method: 'POST',
    body: JSON.stringify({ ticket_data: ticketData })
});
```

## 🔍 Development

### Dev Mode Features

- **Enhanced Logging**: Detailed request/response logging
- **Debug Endpoints**: Additional debugging information
- **Auto-reload**: Server restarts on code changes
- **Fallback Testing**: Test fallback scenarios easily

### Environment Variables

```bash
# Server configuration
HOST=0.0.0.0                    # Server host
PORT=8000                       # Server port
DEV_MODE=true                   # Enable development mode

# Fallback configuration
FALLBACK_FILE_PATH=langgraph_mcp/fallback/jira_prompt.json
```

### Adding New Templates

1. **Update Template Engine** (`services/template_engine.py`):
   ```python
   self.templates["new_template"] = {
       "name": "new_template",
       "keywords": ["keyword1", "keyword2"],
       "priority": 3
   }
   ```

2. **Add Prompt Logic** (`services/prompt_builder.py`):
   ```python
   def _generate_new_template_prompt(self, ticket_data, enrichment_data):
       # Implementation here
   ```

## 🔗 Integration

### VS Code Extension

The MCP server integrates seamlessly with the VS Code extension:

1. Extension calls `/api/ticket/{id}` to fetch metadata
2. Extension calls `/api/prompt/generate` to create prompt
3. Extension calls `/api/session/complete` when PR is done

### Future Integrations

- **PESS Scoring**: Automatic scoring of generated prompts
- **Synthetic Memory**: Context enrichment from historical data
- **Jira API**: Direct integration with Jira servers
- **GitHub API**: PR creation and management

## 🛠️ Troubleshooting

### Common Issues

1. **Import Errors**:
   ```bash
   # Ensure Python path is set
   export PYTHONPATH=/path/to/Jr-dev-agent
   ```

2. **Port Already in Use**:
   ```bash
   # Change port
   export PORT=8001
   ```

3. **Fallback File Not Found**:
   ```bash
   # Check fallback file exists
   ls langgraph_mcp/fallback/jira_prompt.json
   ```

### Debug Mode

```bash
# Enable debug logging
export DEV_MODE=true

# Check debug endpoints
curl http://localhost:8000/api/debug/health
curl http://localhost:8000/api/debug/sessions
```

## 📈 Performance

### Metrics

- **Health Check**: ~5ms response time
- **Ticket Fetch**: ~50ms (with fallback)
- **Prompt Generation**: ~200-500ms (depends on template)
- **Session Management**: ~10ms per operation

### Optimization

- LangGraph state caching
- Template precompilation
- Session cleanup automation
- Background task processing

## 🔮 Future Enhancements

- **Streaming Responses**: Real-time prompt generation
- **Caching Layer**: Redis-based response caching
- **Metrics Collection**: Prometheus metrics
- **Authentication**: JWT-based security
- **Rate Limiting**: Request throttling
- **Horizontal Scaling**: Multi-instance deployment

---

**Built with ❤️ by the Jr Dev Agent Team** 