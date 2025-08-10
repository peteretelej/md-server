import pytest
import base64
from pathlib import Path
from litestar.testing import AsyncTestClient

from md_server.app import app


@pytest.fixture
def client():
    """Create test client for API testing."""
    return AsyncTestClient(app=app)


@pytest.fixture
def test_data_dir() -> Path:
    """Return path to test data directory."""
    return Path(__file__).parent / "test_data"


class TestUnifiedConvertAPI:
    """Test suite for the unified /convert endpoint."""

    async def test_json_text_input(self, client: AsyncTestClient):
        """Test converting text through JSON input."""
        response = await client.post(
            "/convert",
            json={"text": "# Test Markdown\n\nThis is a test"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "# Test Markdown" in data["markdown"]
        assert "This is a test" in data["markdown"]
        assert data["metadata"]["source_type"] == "text"
        assert data["metadata"]["source_size"] > 0
        assert "request_id" in data

    async def test_json_text_with_options(self, client: AsyncTestClient):
        """Test text conversion with options."""
        response = await client.post(
            "/convert",
            json={
                "text": "# Test Markdown\n\nThis is a very long test that should be truncated when max_length is applied",
                "options": {"max_length": 20, "clean_markdown": True},
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert len(data["markdown"]) <= 23  # 20 + "..."
        assert data["markdown"].endswith("...")

    async def test_json_url_input(self, client: AsyncTestClient):
        """Test converting URL through JSON input."""
        response = await client.post(
            "/convert",
            json={"url": "https://httpbin.org/html"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["metadata"]["source_type"] == "url"
        assert len(data["markdown"]) > 0
        assert "request_id" in data

    async def test_json_url_with_options(self, client: AsyncTestClient):
        """Test URL conversion with options."""
        response = await client.post(
            "/convert",
            json={"url": "https://httpbin.org/html", "options": {"timeout": 10}},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_json_base64_content(
        self, client: AsyncTestClient, test_data_dir: Path
    ):
        """Test converting base64 content through JSON input."""
        # Create test JSON content directly
        test_content = '{"message": "hello world", "number": 42}'
        b64_content = base64.b64encode(test_content.encode()).decode()

        response = await client.post(
            "/convert",
            json={"content": b64_content, "filename": "test.json"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "hello world" in data["markdown"]
        assert data["metadata"]["source_type"] == "json"

    async def test_binary_upload(self, client: AsyncTestClient):
        """Test binary file upload."""
        content = "# Simple Test\n\nThis is plain text content."

        response = await client.post(
            "/convert", content=content.encode(), headers={"Content-Type": "text/plain"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "Simple Test" in data["markdown"]
        assert data["metadata"]["source_type"] == "text"

    async def test_multipart_upload(self, client: AsyncTestClient):
        """Test multipart form file upload."""
        content = "# Test Document\n\nThis is a markdown file."

        files = {"file": ("test.md", content, "text/markdown")}

        response = await client.post("/convert", files=files)

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "Test Document" in data["markdown"]
        assert data["metadata"]["source_type"] == "markdown"

    async def test_multipart_with_options(self, client: AsyncTestClient):
        """Test multipart upload with options."""
        content = "# Test Document\n\nThis needs cleaning."

        files = {"file": ("test.md", content, "text/markdown")}
        data_fields = {"options": '{"clean_markdown": true}'}

        response = await client.post("/convert", files=files, data=data_fields)

        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True

    async def test_error_unsupported_format(self, client: AsyncTestClient):
        """Test error response for unsupported format."""
        # Send binary content that will trigger an error (empty content with image type)
        content = b""  # Empty content with image content type should fail

        response = await client.post(
            "/convert", content=content, headers={"Content-Type": "image/png"}
        )

        # Should get an error for empty content
        assert response.status_code >= 400
        data = response.json()
        # Error is wrapped by Litestar in the detail field
        error_data = data.get("detail", data)
        assert error_data["success"] is False
        assert "error" in error_data

    async def test_error_invalid_json(self, client: AsyncTestClient):
        """Test error response for invalid JSON."""
        response = await client.post(
            "/convert",
            content='{"invalid": json}',  # Invalid JSON
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 400
        data = response.json()
        # Error is wrapped by Litestar in the detail field
        error_data = data.get("detail", data)
        assert error_data["success"] is False
        assert error_data["error"]["code"] == "INVALID_INPUT"

    async def test_error_missing_json_input(self, client: AsyncTestClient):
        """Test error for JSON without required fields."""
        response = await client.post(
            "/convert",
            json={"options": {"timeout": 10}},  # Missing url, content, or text
        )

        assert response.status_code == 400
        data = response.json()
        error_data = data.get("detail", data)
        assert error_data["success"] is False

    async def test_error_invalid_url(self, client: AsyncTestClient):
        """Test error for invalid URL."""
        response = await client.post("/convert", json={"url": "not-a-url"})

        assert response.status_code == 400
        data = response.json()
        error_data = data.get("detail", data)
        assert error_data["success"] is False
        # The error code might be INVALID_INPUT for malformed URLs
        assert error_data["error"]["code"] in [
            "INVALID_URL",
            "FETCH_FAILED",
            "INVALID_INPUT",
        ]

    async def test_error_blocked_url(self, client: AsyncTestClient):
        """Test error for blocked URL (private IP)."""
        response = await client.post(
            "/convert", json={"url": "http://127.0.0.1:8080/secret"}
        )

        assert response.status_code == 400
        data = response.json()
        error_data = data.get("detail", data)
        assert error_data["success"] is False
        assert error_data["error"]["code"] == "INVALID_URL"

    async def test_response_format_consistency(self, client: AsyncTestClient):
        """Test that all successful responses have consistent format."""
        test_cases = [
            {"json": {"text": "Simple text"}},
            {"content": b"Binary content", "headers": {"Content-Type": "text/plain"}},
            {"files": {"file": ("test.txt", "File content", "text/plain")}},
        ]

        for case in test_cases:
            if "json" in case:
                response = await client.post("/convert", json=case["json"])
            elif "files" in case:
                response = await client.post("/convert", files=case["files"])
            else:
                response = await client.post("/convert", **case)

            assert response.status_code == 200
            data = response.json()

            # Check required fields in successful response
            assert "success" in data and data["success"] is True
            assert "markdown" in data
            assert "metadata" in data
            assert "request_id" in data

            # Check metadata structure
            metadata = data["metadata"]
            assert "source_type" in metadata
            assert "source_size" in metadata
            assert "markdown_size" in metadata
            assert "conversion_time_ms" in metadata
            assert "detected_format" in metadata
            assert "warnings" in metadata
            assert isinstance(metadata["warnings"], list)

    async def test_large_content_handling(self, client: AsyncTestClient):
        """Test handling of large content."""
        # Create large text content
        large_text = "Large content line.\n" * 1000  # ~19KB

        response = await client.post("/convert", json={"text": large_text})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["metadata"]["source_size"] > 10000

    async def test_request_id_uniqueness(self, client: AsyncTestClient):
        """Test that each request gets a unique request ID."""
        responses = []
        for _ in range(3):
            response = await client.post("/convert", json={"text": "Test content"})
            assert response.status_code == 200
            responses.append(response.json())

        # All request IDs should be different
        request_ids = [r["request_id"] for r in responses]
        assert len(set(request_ids)) == 3  # All unique

        # Request IDs should follow the expected format
        for request_id in request_ids:
            assert request_id.startswith("req_")
            assert len(request_id) > 10  # Should be reasonably long

    async def test_metadata_accuracy(self, client: AsyncTestClient):
        """Test that metadata accurately reflects the conversion."""
        test_content = "# Test\n\nContent for size testing."

        response = await client.post("/convert", json={"text": test_content})

        assert response.status_code == 200
        data = response.json()

        metadata = data["metadata"]

        # Source size should match input
        assert metadata["source_size"] == len(test_content.encode())

        # Markdown size should match output
        assert metadata["markdown_size"] == len(data["markdown"].encode())

        # Conversion time should be reasonable
        assert 0 <= metadata["conversion_time_ms"] <= 5000  # Should be fast

        # Source type should be correct
        assert metadata["source_type"] == "text"


class TestAuxiliaryEndpoints:
    """Test auxiliary endpoints."""

    async def test_health_endpoint(self, client: AsyncTestClient):
        """Test health check endpoint."""
        response = await client.get("/healthz")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    async def test_formats_endpoint(self, client: AsyncTestClient):
        """Test formats endpoint."""
        response = await client.get("/formats")

        assert response.status_code == 200
        data = response.json()

        assert "formats" in data
        formats = data["formats"]

        # Check that common formats are present
        assert "pdf" in formats
        assert "docx" in formats
        assert "html" in formats
        assert "text" in formats

        # Check format structure
        for format_name, format_info in formats.items():
            assert "mime_types" in format_info
            assert "extensions" in format_info
            assert "features" in format_info
            assert "max_size_mb" in format_info

            assert isinstance(format_info["mime_types"], list)
            assert isinstance(format_info["extensions"], list)
            assert isinstance(format_info["features"], list)
            assert isinstance(format_info["max_size_mb"], (int, float))
