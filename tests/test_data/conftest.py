from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List
from unittest.mock import Mock

import pytest
from httpx import AsyncClient, ASGITransport
from litestar.testing import TestClient

from md_server.app import app
from md_server.core.config import Settings
from md_server.core.markitdown_config import MarkItDownConfig


@dataclass
class FileTestVector:
    """Test vector for file conversion validation."""

    filename: str
    content_type: str
    must_include: List[str]
    must_not_include: List[str] = None
    expected_status: int = 200

    def __post_init__(self):
        if self.must_not_include is None:
            self.must_not_include = []


@pytest.fixture
def test_data_dir() -> Path:
    """Return path to test data directory."""
    return Path(__file__).parent


@pytest.fixture
def client() -> TestClient:
    """Litestar test client."""
    return TestClient(app)


@pytest.fixture
async def async_client() -> AsyncClient:
    """Async HTTP client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
def file_test_vectors() -> Dict[str, FileTestVector]:
    """Test vectors for file conversion validation."""
    return {
        "pdf": FileTestVector(
            filename="test.pdf",
            content_type="application/pdf",
            must_include=["# Test PDF", "sample document"],
        ),
        "docx": FileTestVector(
            filename="test.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            must_include=["This is a test document"],
        ),
        "docx_equations": FileTestVector(
            filename="equations.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            must_include=["equation", "formula"],
        ),
        "docx_comments": FileTestVector(
            filename="test_with_comment.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            must_include=["comment"],
        ),
        "pptx": FileTestVector(
            filename="test.pptx",
            content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            must_include=["slide", "presentation"],
        ),
        "xlsx": FileTestVector(
            filename="test.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            must_include=["data", "table"],
        ),
        "epub": FileTestVector(
            filename="test.epub",
            content_type="application/epub+zip",
            must_include=["chapter", "book"],
        ),
        "jpg": FileTestVector(
            filename="test.jpg", content_type="image/jpeg", must_include=["image"]
        ),
        "html_blog": FileTestVector(
            filename="test_blog.html",
            content_type="text/html",
            must_include=["blog", "article"],
        ),
        "html_wikipedia": FileTestVector(
            filename="test_wikipedia.html",
            content_type="text/html",
            must_include=["wikipedia"],
        ),
        "unsupported": FileTestVector(
            filename="random.bin",
            content_type="application/octet-stream",
            must_include=[],
            expected_status=415,
        ),
    }


@pytest.fixture
def url_test_vectors() -> Dict[str, Dict]:
    """Test vectors for URL conversion validation."""
    return {
        "valid_webpage": {
            "url": "https://httpbin.org/html",
            "must_include": ["html", "Herman Melville"],
            "expected_status": 200,
        },
        "invalid_url": {"url": "not-a-url", "must_include": [], "expected_status": 400},
        "nonexistent_url": {
            "url": "https://nonexistent-domain-12345.com",
            "must_include": [],
            "expected_status": 400,
        },
    }


@pytest.fixture
def sample_files(test_data_dir: Path) -> Dict[str, Path]:
    """Dictionary of sample file paths for testing."""
    return {
        "pdf": test_data_dir / "test.pdf",
        "docx": test_data_dir / "test.docx",
        "pptx": test_data_dir / "test.pptx",
        "xlsx": test_data_dir / "test.xlsx",
        "epub": test_data_dir / "test.epub",
        "jpg": test_data_dir / "test.jpg",
        "html": test_data_dir / "test_blog.html",
        "unsupported": test_data_dir / "random.bin",
    }


@pytest.fixture
def mock_settings() -> Settings:
    """Mock settings for testing."""
    return Settings(
        max_file_size=10 * 1024 * 1024,  # 10MB for testing
        timeout_seconds=5,
        allowed_file_types=[
            "text/plain",
            "text/html",
            "text/markdown",
            "application/pdf",
            "application/json",
        ],
    )


@pytest.fixture
def mock_markitdown_config() -> MarkItDownConfig:
    """Mock MarkItDown configuration for testing."""
    return MarkItDownConfig(
        enable_builtins=True, enable_plugins=False, timeout_seconds=30
    )


@pytest.fixture
def mock_converter():
    """Mock converter for testing."""
    mock = Mock()
    mock.convert.return_value = "# Test Content\n\nThis is mock converted content."
    return mock


@pytest.fixture
def test_file_content() -> Dict[str, bytes]:
    """Sample file content for testing."""
    return {
        "text": b"Hello World\nThis is a test file.",
        "json": b'{"message": "Hello World", "status": "test"}',
        "html": b"<html><body><h1>Test</h1><p>Content</p></body></html>",
        "empty": b"",
    }
