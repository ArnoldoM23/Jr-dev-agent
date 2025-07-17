# Jr Dev Agent Test Suite

This directory contains comprehensive tests for all Jr Dev Agent services. The test suite includes unit tests, integration tests, and end-to-end tests to ensure all services work correctly individually and together.

## Test Structure

```
tests/
├── conftest.py              # Shared pytest configuration and fixtures
├── pytest.ini              # Pytest configuration
├── requirements.txt         # Test dependencies
├── run_tests.py            # Test runner script
├── README.md               # This file
├── unit/                   # Unit tests
│   ├── test_pess_scoring.py
│   ├── test_promptbuilder.py
│   └── test_template_intelligence.py
├── integration/            # Integration tests
│   ├── test_pess_service_api.py
│   ├── test_promptbuilder_api.py
│   └── test_template_intelligence_api.py
└── e2e/                    # End-to-end tests
    └── test_complete_workflow.py
```

## Services Tested

The test suite covers the following services:

1. **PESS (Prompt Effectiveness Scoring System)** - Port 8005
   - 8-dimensional scoring algorithm
   - 5-stage pipeline (Ingestor → Normalizer → Evaluator → Versioner → Emitter)
   - Feedback system and analytics

2. **PromptBuilder Service** - Port 8001
   - Template-based prompt generation
   - Support for feature, bugfix, and refactor templates
   - Context enrichment integration

3. **Template Intelligence Service** - Port 8002
   - Intelligent template selection
   - 7 default templates (feature, bugfix, refactor, version_upgrade, config_update, schema_change, test_generation)
   - Template validation and suggestions

4. **Session Management Service** - Port 8003
   - User session tracking and management
   - Context preservation across requests

5. **Synthetic Memory System** - Port 8004
   - Qdrant vector database integration
   - Context enrichment and retrieval

6. **LangGraph MCP Server** - Port 8000
   - Main orchestration service
   - 5-node workflow integration

## Prerequisites

1. **Install test dependencies:**
   ```bash
   pip install -r tests/requirements.txt
   ```

2. **Start all services:**
   ```bash
   docker-compose up -d
   ```

3. **Verify services are running:**
   ```bash
   python tests/run_tests.py health
   ```

## Running Tests

### Using the Test Runner Script

The `run_tests.py` script provides a convenient way to run different types of tests:

```bash
# Run all tests
python tests/run_tests.py all

# Run unit tests only
python tests/run_tests.py unit

# Run integration tests only
python tests/run_tests.py integration

# Run end-to-end tests only
python tests/run_tests.py e2e

# Run smoke tests
python tests/run_tests.py smoke

# Run with coverage
python tests/run_tests.py coverage

# Check service health
python tests/run_tests.py health

# Generate service status report
python tests/run_tests.py status

# Run with verbose output
python tests/run_tests.py unit --verbose
```

### Using pytest directly

You can also run tests directly with pytest:

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/unit/test_pess_scoring.py

# Run specific test class
pytest tests/unit/test_pess_scoring.py::TestPESSModels

# Run specific test method
pytest tests/unit/test_pess_scoring.py::TestPESSModels::test_prompt_data_creation

# Run with coverage
pytest tests/ --cov=pess_scoring --cov=promptbuilder --cov=template_intelligence

# Run with specific markers
pytest tests/ -m "not requires_services"
pytest tests/ -m "unit"
pytest tests/ -m "integration"
```

## Test Categories

### Unit Tests
- Test individual components in isolation
- Mock external dependencies
- Fast execution
- No service dependencies required

**Examples:**
- PESS scoring algorithm tests
- PromptBuilder template generation
- Template Intelligence selection logic

### Integration Tests
- Test API endpoints and service interactions
- Require running services
- Test real HTTP requests and responses
- Verify service contracts

**Examples:**
- PESS API endpoint tests
- PromptBuilder API tests
- Template Intelligence API tests

### End-to-End Tests
- Test complete workflows across multiple services
- Require all services to be running
- Test real user scenarios
- Verify service integration

**Examples:**
- Complete ticket processing workflow
- Multi-service template selection and prompt generation
- Error handling across services

## Test Markers

Tests are organized using pytest markers:

```python
@pytest.mark.unit                    # Unit tests
@pytest.mark.integration            # Integration tests
@pytest.mark.e2e                    # End-to-end tests
@pytest.mark.slow                   # Slow running tests
@pytest.mark.requires_services      # Tests requiring running services
@pytest.mark.requires_database      # Tests requiring database
@pytest.mark.requires_redis         # Tests requiring Redis
@pytest.mark.requires_qdrant        # Tests requiring Qdrant
@pytest.mark.smoke                  # Smoke tests
```

Run tests by marker:
```bash
pytest tests/ -m "unit"
pytest tests/ -m "integration and not slow"
pytest tests/ -m "requires_services"
```

## Service Health Checks

Before running integration or E2E tests, verify services are healthy:

```bash
# Check all services
python tests/run_tests.py health

# Generate detailed status report
python tests/run_tests.py status
```

The health check will verify:
- Service is responding on expected port
- `/health` endpoint returns 200
- Service-specific health indicators

## Configuration

### pytest.ini
Contains pytest configuration including:
- Test discovery paths
- Markers definition
- Async test support
- Logging configuration
- Timeout settings

### conftest.py
Provides shared fixtures:
- Service client factory
- Mock objects (database, Redis, Qdrant)
- Sample test data
- Service health checks

## Coverage Reports

Generate coverage reports:

```bash
# HTML coverage report
python tests/run_tests.py coverage

# View coverage report
open htmlcov/index.html
```

Coverage is tracked for all service modules:
- `pess_scoring/`
- `promptbuilder/`
- `template_intelligence/`
- `session_management/`
- `synthetic_memory/`
- `langgraph_mcp/`

## Troubleshooting

### Common Issues

1. **Services not running:**
   ```bash
   docker-compose up -d
   python tests/run_tests.py health
   ```

2. **Port conflicts:**
   Check if ports 8000-8005 are available:
   ```bash
   netstat -tlnp | grep 800
   ```

3. **Test failures due to timeouts:**
   Increase timeout in pytest.ini or use `--timeout` flag:
   ```bash
   pytest tests/ --timeout=300
   ```

4. **Import errors:**
   Ensure all dependencies are installed:
   ```bash
   pip install -r tests/requirements.txt
   ```

### Service-Specific Issues

1. **PESS Service:**
   - Check PostgreSQL is running
   - Verify database connection
   - Check Redis for caching

2. **Synthetic Memory:**
   - Ensure Qdrant is running
   - Check vector database connection
   - Verify collection exists

3. **Template Intelligence:**
   - Verify all 7 templates are loaded
   - Check template validation logic

## Continuous Integration

For CI/CD pipelines:

```bash
# Install dependencies
pip install -r tests/requirements.txt

# Start services
docker-compose up -d

# Wait for services to be ready
python tests/run_tests.py health

# Run tests with coverage
python tests/run_tests.py coverage

# Generate reports
pytest tests/ --junit-xml=test-results.xml --cov-report=xml
```

## Test Data

The test suite uses:
- **Sample ticket data** for different scenarios
- **Mock responses** for external services
- **Test fixtures** for consistent data
- **Factory patterns** for generating test objects

## Contributing

When adding new tests:

1. Follow the existing test structure
2. Use appropriate test markers
3. Include both positive and negative test cases
4. Add integration tests for API endpoints
5. Update this README if adding new test categories

## Performance Testing

For performance testing:

```bash
# Run with multiple workers
pytest tests/ -n auto

# Run only fast tests
pytest tests/ -m "not slow"

# Profile test execution
pytest tests/ --profile
```

## Example Test Run

```bash
$ python tests/run_tests.py all --verbose

============================================================
                    CHECKING SERVICE HEALTH                    
============================================================
✓ mcp_server is healthy
✓ promptbuilder is healthy
✓ template_intelligence is healthy
✓ session_management is healthy
✓ synthetic_memory is healthy
✓ pess is healthy
✓ All 6 services are healthy

============================================================
                      RUNNING UNIT TESTS                      
============================================================
ℹ Running: python -m pytest tests/unit/ -m not requires_services --tb=short -v
====================== test session starts ======================
collected 87 items

tests/unit/test_pess_scoring.py::TestPESSModels::test_prompt_data_creation PASSED
tests/unit/test_pess_scoring.py::TestPESSModels::test_scoring_request_validation PASSED
tests/unit/test_pess_scoring.py::TestScoringAlgorithm::test_clarity_scoring PASSED
...
====================== 87 passed in 12.34s ======================

============================================================
                   RUNNING INTEGRATION TESTS                   
============================================================
ℹ Running: python -m pytest tests/integration/ --tb=short -v
====================== test session starts ======================
collected 45 items

tests/integration/test_pess_service_api.py::TestPESSServiceAPI::test_health_check PASSED
tests/integration/test_pess_service_api.py::TestPESSServiceAPI::test_score_prompt_endpoint PASSED
...
====================== 45 passed in 23.56s ======================

============================================================
                      RUNNING E2E TESTS                       
============================================================
ℹ Running: python -m pytest tests/e2e/ --tb=short -v
====================== test session starts ======================
collected 8 items

tests/e2e/test_complete_workflow.py::TestCompleteWorkflow::test_complete_ticket_processing_workflow PASSED
tests/e2e/test_complete_workflow.py::TestCompleteWorkflow::test_feature_development_workflow PASSED
...
====================== 8 passed in 34.12s ======================

✓ All tests passed!
```

This comprehensive test suite ensures that all Jr Dev Agent services work correctly both individually and as an integrated system. 