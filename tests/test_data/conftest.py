from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from md_server.main import app


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
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
async def async_client() -> AsyncClient:
    """Async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def file_test_vectors() -> Dict[str, FileTestVector]:
    """Test vectors for file conversion validation."""
    return {
        "pdf": FileTestVector(
            filename="test.pdf",
            content_type="application/pdf",
            must_include=["# Test PDF", "sample document"]
        ),
        "docx": FileTestVector(
            filename="test.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            must_include=["This is a test document"]
        ),
        "docx_equations": FileTestVector(
            filename="equations.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            must_include=["equation", "formula"]
        ),
        "docx_comments": FileTestVector(
            filename="test_with_comment.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            must_include=["comment"]
        ),
        "pptx": FileTestVector(
            filename="test.pptx",
            content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            must_include=["slide", "presentation"]
        ),
        "xlsx": FileTestVector(
            filename="test.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            must_include=["data", "table"]
        ),
        "epub": FileTestVector(
            filename="test.epub",
            content_type="application/epub+zip",
            must_include=["chapter", "book"]
        ),
        "jpg": FileTestVector(
            filename="test.jpg",
            content_type="image/jpeg",
            must_include=["image"]
        ),
        "html_blog": FileTestVector(
            filename="test_blog.html",
            content_type="text/html",
            must_include=["blog", "article"]
        ),
        "html_wikipedia": FileTestVector(
            filename="test_wikipedia.html",
            content_type="text/html",
            must_include=["wikipedia"]
        ),
        "unsupported": FileTestVector(
            filename="random.bin",
            content_type="application/octet-stream",
            must_include=[],
            expected_status=415
        )
    }


@pytest.fixture
def url_test_vectors() -> Dict[str, Dict]:
    """Test vectors for URL conversion validation."""
    return {
        "valid_webpage": {
            "url": "https://httpbin.org/html",
            "must_include": ["html", "Herman Melville"],
            "expected_status": 200
        },
        "invalid_url": {
            "url": "not-a-url",
            "must_include": [],
            "expected_status": 400
        },
        "nonexistent_url": {
            "url": "https://nonexistent-domain-12345.com",
            "must_include": [],
            "expected_status": 400
        }
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
        "unsupported": test_data_dir / "random.bin"
    }