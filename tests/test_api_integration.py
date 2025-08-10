import pytest
import base64
from litestar.testing import AsyncTestClient

from md_server.app import app


@pytest.fixture
def client():
    """Create test client for integration testing."""
    return AsyncTestClient(app=app)


class TestConvertAPIIntegration:
    """Integration tests for the unified /convert endpoint covering all input methods."""

    async def test_all_input_methods(self, client: AsyncTestClient):
        """Test all supported input methods work correctly."""

        # Test 1: JSON text input
        response = await client.post("/convert", json={"text": "# Test\n\nContent"})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Test" in data["markdown"]
        assert data["metadata"]["source_type"] == "text"

        # Test 2: JSON URL input
        response = await client.post(
            "/convert", json={"url": "https://httpbin.org/html"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["markdown"]) > 100
        assert data["metadata"]["source_type"] == "url"

        # Test 3: JSON base64 content
        content = '{"message": "hello world"}'
        b64_content = base64.b64encode(content.encode()).decode()
        response = await client.post(
            "/convert", json={"content": b64_content, "filename": "test.json"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "hello world" in data["markdown"]
        assert data["metadata"]["source_type"] == "json"

        # Test 4: Binary upload
        response = await client.post(
            "/convert",
            content="Simple content".encode(),
            headers={"Content-Type": "text/plain"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Simple content" in data["markdown"]

        # Test 5: Multipart form upload
        files = {"file": ("test.md", "# Multipart Test", "text/markdown")}
        response = await client.post("/convert", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Multipart Test" in data["markdown"]

    async def test_conversion_options(self, client: AsyncTestClient):
        """Test that conversion options work across input methods."""

        # Test options with JSON input
        response = await client.post(
            "/convert",
            json={
                "text": "Long text " * 20,
                "options": {"max_length": 20, "clean_markdown": True},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["markdown"]) <= 23  # 20 + "..."

        # Test options with multipart upload
        files = {"file": ("test.md", "# Test Doc", "text/markdown")}
        form_data = {"options": '{"clean_markdown": true}'}
        response = await client.post("/convert", files=files, data=form_data)
        assert response.status_code == 200
        assert response.json()["success"] is True

    async def test_error_handling(self, client: AsyncTestClient):
        """Test error handling across different scenarios."""

        # Invalid JSON
        response = await client.post(
            "/convert",
            content='{"invalid": json}',
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400
        error_data = response.json().get("detail", response.json())
        assert error_data["success"] is False
        assert error_data["error"]["code"] == "INVALID_INPUT"

        # Missing required fields
        response = await client.post("/convert", json={"options": {"timeout": 10}})
        assert response.status_code == 400
        error_data = response.json().get("detail", response.json())
        assert error_data["success"] is False

        # Invalid URL
        response = await client.post("/convert", json={"url": "not-a-url"})
        assert response.status_code == 400
        error_data = response.json().get("detail", response.json())
        assert error_data["success"] is False

        # Blocked URL (private IP)
        response = await client.post(
            "/convert", json={"url": "http://127.0.0.1:8080/test"}
        )
        assert response.status_code == 400
        error_data = response.json().get("detail", response.json())
        assert error_data["success"] is False
        assert error_data["error"]["code"] == "INVALID_URL"

    async def test_response_consistency(self, client: AsyncTestClient):
        """Test that all successful responses follow the same format."""
        test_cases = [
            {"json": {"text": "Test"}},
            {"content": b"Binary", "headers": {"Content-Type": "text/plain"}},
            {"files": {"file": ("test.txt", "File", "text/plain")}},
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

            # Verify consistent structure
            required_fields = ["success", "markdown", "metadata", "request_id"]
            assert all(field in data for field in required_fields)
            assert data["success"] is True

            # Verify metadata structure
            metadata_fields = [
                "source_type",
                "source_size",
                "markdown_size",
                "conversion_time_ms",
                "detected_format",
                "warnings",
            ]
            assert all(field in data["metadata"] for field in metadata_fields)
            assert isinstance(data["metadata"]["warnings"], list)
            assert data["request_id"].startswith("req_")


class TestAuxiliaryEndpoints:
    """Integration tests for auxiliary endpoints."""

    async def test_health_and_formats(self, client: AsyncTestClient):
        """Test health and formats endpoints work correctly."""

        # Health endpoint
        response = await client.get("/healthz")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

        # Formats endpoint
        response = await client.get("/formats")
        assert response.status_code == 200
        data = response.json()
        assert "formats" in data

        # Verify format structure
        for format_name, format_info in data["formats"].items():
            required_fields = ["mime_types", "extensions", "features", "max_size_mb"]
            assert all(field in format_info for field in required_fields)
            assert isinstance(format_info["mime_types"], list)
            assert isinstance(format_info["extensions"], list)
            assert isinstance(format_info["features"], list)


class TestEndToEndScenarios:
    """End-to-end tests simulating real usage scenarios."""

    async def test_typical_document_workflow(self, client: AsyncTestClient):
        """Test typical document conversion workflows."""

        # Scenario 1: Web content processing
        response = await client.post(
            "/convert", json={"url": "https://example.com", "options": {"timeout": 10}}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Example Domain" in data["markdown"]
        assert data["metadata"]["conversion_time_ms"] > 0

        # Scenario 2: File processing with options
        test_json = '{"title": "Document", "content": "Important information"}'
        b64_content = base64.b64encode(test_json.encode()).decode()

        response = await client.post(
            "/convert",
            json={
                "content": b64_content,
                "filename": "document.json",
                "options": {"preserve_formatting": True},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "Document" in data["markdown"]
        assert "Important information" in data["markdown"]

        # Scenario 3: Text processing pipeline
        response = await client.post(
            "/convert",
            json={
                "text": "# Raw Markdown\n\nWith extra   spaces    and formatting issues.",
                "options": {"clean_markdown": True, "max_length": 100},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["markdown"]) <= 103  # max_length + "..."

    async def test_error_recovery_scenarios(self, client: AsyncTestClient):
        """Test system behavior under error conditions."""

        # Skip network timeout test to avoid blocking test suite
        # (timeout functionality is tested in unit tests)

        # Large content handling
        large_text = "Large content line.\n" * 500  # ~9KB
        response = await client.post("/convert", json={"text": large_text})
        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["source_size"] > 5000

    async def test_api_compatibility(self, client: AsyncTestClient):
        """Test API compatibility and backward compatibility."""

        # Test legacy health endpoint
        response = await client.get("/healthz")
        assert response.status_code == 200

        # Test new health endpoint format
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        health_fields = ["status", "version", "uptime_seconds", "conversions_last_hour"]
        assert all(field in data for field in health_fields)

        # Test content type flexibility
        response = await client.post(
            "/convert", content="Plain text", headers={"Content-Type": "text/plain"}
        )
        assert response.status_code == 200

        response = await client.post(
            "/convert", content="Plain text"
        )  # No content type
        assert response.status_code == 200
