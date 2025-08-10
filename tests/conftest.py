import asyncio
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import Mock, AsyncMock

import pytest
from aiohttp import web, ClientSession
from aiohttp.test_utils import TestServer
from litestar.testing import TestClient

from md_server.app import app
from md_server.browser import BrowserChecker
from md_server.factories import MarkItDownFactory


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Path to test data directory."""
    return Path(__file__).parent / "test_data"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def mock_http_server() -> AsyncGenerator[TestServer, None]:
    """Mock HTTP server for testing URL conversions."""

    async def hello_handler(request):
        return web.Response(text="Hello from mock server")

    async def html_handler(request):
        return web.Response(
            text="<html><body><h1>Mock HTML</h1><p>Test content</p></body></html>",
            content_type="text/html",
        )

    async def pdf_handler(request):
        return web.Response(
            body=b"%PDF-1.4 mock pdf content", content_type="application/pdf"
        )

    app = web.Application()
    app.router.add_get("/", hello_handler)
    app.router.add_get("/test.html", html_handler)
    app.router.add_get("/test.pdf", pdf_handler)

    server = TestServer(app)
    await server.start_server()

    yield server

    await server.close()


@pytest.fixture
def mock_browser_checker() -> Mock:
    """Mock browser checker for testing."""
    mock = Mock(spec=BrowserChecker)
    mock.is_available.return_value = True
    mock.log_availability.return_value = None
    return mock


@pytest.fixture
def mock_http_session() -> AsyncMock:
    """Mock HTTP session for testing."""
    mock_session = AsyncMock(spec=ClientSession)
    mock_session.get.return_value.__aenter__.return_value.text.return_value = (
        "Mock HTML content"
    )
    return mock_session


@pytest.fixture
def mock_markitdown_factory() -> Mock:
    """Mock MarkItDown factory for testing."""
    mock = Mock(spec=MarkItDownFactory)
    mock_converter = Mock()
    mock_converter.convert.return_value = Mock(text_content="Mock converted content")
    mock.create.return_value = mock_converter
    return mock


@pytest.fixture
def mock_converter() -> Mock:
    """Mock MarkItDown converter for testing."""
    mock = Mock()
    mock.convert.return_value = Mock(text_content="Mock converted content")
    return mock


@pytest.fixture
def client() -> TestClient:
    """Test client for API testing."""
    return TestClient(app=app)


@pytest.fixture
def auth_headers() -> dict:
    """Headers with API key for authenticated requests."""
    return {"X-API-Key": "test-api-key"}


@pytest.fixture
def sample_files(test_data_dir) -> dict:
    """Paths to sample test files."""
    return {
        "pdf": test_data_dir / "test.pdf",
        "docx": test_data_dir / "test.docx",
        "html": test_data_dir / "test_blog.html",
        "json": test_data_dir / "test.json",
        "binary": test_data_dir / "random.bin",
    }
