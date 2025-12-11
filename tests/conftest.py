"""
Shared pytest configuration and fixtures for Jr Dev Agent tests.
"""

import pytest
import pytest_asyncio
import asyncio
import aiohttp
import time
import logging
from typing import Dict, Any, Optional
from unittest.mock import MagicMock, AsyncMock

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service URLs for testing
SERVICE_URLS = {
    "mcp_server": "http://localhost:8000",
    "promptbuilder": "http://localhost:8001", 
    "template_intelligence": "http://localhost:8002",
    "session_management": "http://localhost:8003",
    "synthetic_memory": "http://localhost:8004",
    "pess": "http://localhost:8005"
}


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def aiohttp_session():
    """Create an aiohttp session for each test."""
    async with aiohttp.ClientSession() as session:
        yield session


@pytest.fixture
def mock_database():
    """Mock database connection for testing."""
    return MagicMock()


@pytest.fixture
def mock_redis():
    """Mock Redis connection for testing."""
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    mock.exists = AsyncMock(return_value=False)
    return mock


@pytest.fixture
def mock_qdrant():
    """Mock Qdrant connection for testing."""
    mock = AsyncMock()
    mock.search = AsyncMock(return_value=[])
    mock.upsert = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    return mock


@pytest.fixture
async def service_health_check(aiohttp_session):
    """Check if all services are healthy before running tests."""
    async def check_service(service_name: str, url: str) -> bool:
        try:
            async with aiohttp_session.get(f"{url}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                return response.status == 200
        except Exception as e:
            logger.warning(f"Health check failed for {service_name}: {e}")
            return False
    
    return check_service


@pytest.fixture
def sample_prompt_data():
    """Sample prompt data for testing."""
    return {
        "ticket_id": "TICKET-123",
        "description": "Fix login validation bug",
        "requirements": ["Validate email format", "Check password strength"],
        "context": "User authentication system",
        "priority": "high",
        "estimated_effort": "2 hours"
    }


@pytest.fixture
def sample_session_data():
    """Sample session data for testing."""
    return {
        "session_id": "session-123",
        "user_id": "user-456",
        "context": {
            "current_task": "TICKET-123",
            "workspace": "/path/to/workspace",
            "files": ["src/auth.py", "tests/test_auth.py"]
        },
        "state": "active",
        "created_at": "2024-01-01T00:00:00Z"
    }


@pytest.fixture
def sample_memory_data():
    """Sample memory data for testing."""
    return {
        "content": "User authentication implementation using JWT tokens",
        "metadata": {
            "type": "code_snippet",
            "language": "python",
            "file_path": "src/auth.py",
            "created_at": "2024-01-01T00:00:00Z"
        },
        "embedding": [0.1, 0.2, 0.3, 0.4, 0.5] * 200  # 1000-dim vector
    }


@pytest.fixture
def sample_pess_data():
    """Sample PESS scoring data for testing."""
    return {
        "prompt": "Fix the login bug in the authentication system",
        "context": {
            "ticket_id": "TICKET-123",
            "codebase_size": 50000,
            "complexity": "medium"
        },
        "expected_scores": {
            "clarity": 0.8,
            "completeness": 0.7,
            "context_relevance": 0.9,
            "technical_accuracy": 0.8,
            "actionability": 0.9,
            "scope_appropriateness": 0.8,
            "error_handling": 0.7,
            "maintainability": 0.8
        }
    }


@pytest.fixture
def sample_template_data():
    """Sample template data for testing."""
    return {
        "template_id": "auth_bug_fix",
        "name": "Authentication Bug Fix Template",
        "description": "Template for fixing authentication-related bugs",
        "category": "bug_fix",
        "tags": ["authentication", "security", "backend"],
        "content": "Analyze the authentication bug: {bug_description}",
        "variables": ["bug_description"],
        "usage_count": 42,
        "success_rate": 0.87
    }


class ServiceTestClient:
    """Helper class for testing service endpoints."""
    
    def __init__(self, base_url: str, session: aiohttp.ClientSession):
        self.base_url = base_url
        self.session = session
    
    async def get(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make GET request to service endpoint."""
        async with self.session.get(f"{self.base_url}{endpoint}", **kwargs) as response:
            return {
                "status": response.status,
                "data": await response.json() if response.content_type == "application/json" else await response.text()
            }
    
    async def post(self, endpoint: str, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Make POST request to service endpoint."""
        async with self.session.post(f"{self.base_url}{endpoint}", json=data, **kwargs) as response:
            return {
                "status": response.status,
                "data": await response.json() if response.content_type == "application/json" else await response.text()
            }
    
    async def put(self, endpoint: str, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Make PUT request to service endpoint."""
        async with self.session.put(f"{self.base_url}{endpoint}", json=data, **kwargs) as response:
            return {
                "status": response.status,
                "data": await response.json() if response.content_type == "application/json" else await response.text()
            }
    
    async def delete(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make DELETE request to service endpoint."""
        async with self.session.delete(f"{self.base_url}{endpoint}", **kwargs) as response:
            return {
                "status": response.status,
                "data": await response.json() if response.content_type == "application/json" else await response.text()
            }


@pytest.fixture
def service_client_factory(aiohttp_session):
    """Factory for creating service test clients."""
    def create_client(service_name: str) -> ServiceTestClient:
        base_url = SERVICE_URLS.get(service_name)
        if not base_url:
            raise ValueError(f"Unknown service: {service_name}")
        return ServiceTestClient(base_url, aiohttp_session)
    
    return create_client


def wait_for_service(service_url: str, timeout: int = 30) -> bool:
    """Wait for a service to be healthy."""
    import requests

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{service_url}/health", timeout=5)
            if response.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    
    return False


def check_service_available(service_url: str) -> bool:
    """Check if a service is available without waiting."""
    import requests
    try:
        response = requests.get(f"{service_url}/health", timeout=1)
        return response.status_code == 200
    except Exception:
        return False


def check_any_service_available() -> bool:
    """Check if any service is available."""
    return any(check_service_available(url) for url in SERVICE_URLS.values())


# Skip condition for tests requiring services
skip_if_no_services = pytest.mark.skipif(
    not check_any_service_available(),
    reason="Test requires running services which are not available"
)


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up the test environment before running tests."""
    logger.info("Setting up test environment...")
    
    # Check for critical services availability (optional, don't wait)
    critical_services = ["mcp_server", "promptbuilder", "template_intelligence", "session_management"]
    
    for service_name in critical_services:
        service_url = SERVICE_URLS[service_name]
        if check_service_available(service_url):
            logger.info(f"Service {service_name} is healthy")
        else:
            logger.warning(f"Service {service_name} is not available, related tests will be skipped")
    
    yield
    
    logger.info("Tearing down test environment...") 