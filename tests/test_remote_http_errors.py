"""
Test HTTP error handling for remote SDK.

Tests proper mapping of HTTP status codes to SDK exceptions,
error response parsing, and error detail extraction.
"""

import pytest
import httpx
from unittest.mock import patch, Mock

from md_server.sdk.remote import RemoteMDConverter
from md_server.sdk.exceptions import (
    InvalidInputError,
    TimeoutError,
    ConversionError,
    NetworkError,
)


class TestRemoteHTTPErrors:
    """Test HTTP error response handling in remote SDK."""

    @pytest.fixture
    def client(self):
        """Create remote client for testing."""
        return RemoteMDConverter(
            endpoint="http://127.0.0.1:8999",
            timeout=5,
            max_retries=0,  # Disable retries for direct error testing
        )

    def create_mock_error_response(
        self, status_code: int, error_data: dict = None, text: str = None
    ):
        """Create mock HTTP error response."""
        response = Mock(spec=httpx.Response)
        response.status_code = status_code
        response.text = text or f"HTTP {status_code} Error"

        if error_data:
            response.json.return_value = error_data
        else:
            response.json.side_effect = ValueError("No JSON content")

        return response

    @pytest.mark.asyncio
    async def test_400_bad_request_mapping(self, client):
        """Test 400 Bad Request maps to InvalidInputError."""
        error_data = {
            "error": {
                "message": "Invalid request format",
                "details": {"field": "content", "issue": "missing"},
            }
        }

        mock_response = self.create_mock_error_response(400, error_data)

        with patch.object(client._client, "request", return_value=mock_response):
            with pytest.raises(InvalidInputError) as exc_info:
                await client.convert_text("test", "text/plain")

            assert "Invalid request format" in str(exc_info.value)
            assert exc_info.value.details["field"] == "content"

    @pytest.mark.asyncio
    async def test_401_unauthorized_mapping(self, client):
        """Test 401 Unauthorized maps to ConversionError."""
        error_data = {
            "error": {
                "message": "API key required",
                "details": {"code": "UNAUTHORIZED"},
            }
        }

        mock_response = self.create_mock_error_response(401, error_data)

        with patch.object(client._client, "request", return_value=mock_response):
            with pytest.raises(ConversionError) as exc_info:
                await client.convert_text("test", "text/plain")

            assert "Server error (401)" in str(exc_info.value)
            assert "API key required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_403_forbidden_mapping(self, client):
        """Test 403 Forbidden maps to ConversionError."""
        error_data = {
            "error": {
                "message": "Access denied",
                "details": {"reason": "quota_exceeded"},
            }
        }

        mock_response = self.create_mock_error_response(403, error_data)

        with patch.object(client._client, "request", return_value=mock_response):
            with pytest.raises(ConversionError) as exc_info:
                await client.convert_text("test", "text/plain")

            assert "Server error (403)" in str(exc_info.value)
            assert "Access denied" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_404_not_found_mapping(self, client):
        """Test 404 Not Found maps to ConversionError."""
        error_data = {
            "error": {"message": "Endpoint not found", "details": {"path": "/convert"}}
        }

        mock_response = self.create_mock_error_response(404, error_data)

        with patch.object(client._client, "request", return_value=mock_response):
            with pytest.raises(ConversionError) as exc_info:
                await client.convert_text("test", "text/plain")

            assert "Server error (404)" in str(exc_info.value)
            assert "Endpoint not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_408_request_timeout_mapping(self, client):
        """Test 408 Request Timeout maps to TimeoutError."""
        error_data = {
            "error": {
                "message": "Request processing timeout",
                "details": {"timeout_seconds": 30},
            }
        }

        mock_response = self.create_mock_error_response(408, error_data)

        with patch.object(client._client, "request", return_value=mock_response):
            with pytest.raises(TimeoutError) as exc_info:
                await client.convert_text("test", "text/plain")

            assert "Request processing timeout" in str(exc_info.value)
            assert exc_info.value.details["timeout_seconds"] == 30

    @pytest.mark.asyncio
    async def test_413_payload_too_large_mapping(self, client):
        """Test 413 Payload Too Large maps to InvalidInputError."""
        error_data = {
            "error": {
                "message": "File size exceeds limit",
                "details": {"max_size": "10MB", "actual_size": "15MB"},
            }
        }

        mock_response = self.create_mock_error_response(413, error_data)

        with patch.object(client._client, "request", return_value=mock_response):
            with pytest.raises(InvalidInputError) as exc_info:
                await client.convert_text("test", "text/plain")

            assert "File too large" in str(exc_info.value)
            assert "File size exceeds limit" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_415_unsupported_media_type_mapping(self, client):
        """Test 415 Unsupported Media Type maps to InvalidInputError."""
        error_data = {
            "error": {
                "message": "Unsupported file format",
                "details": {"format": "unknown", "supported": ["pdf", "docx"]},
            }
        }

        mock_response = self.create_mock_error_response(415, error_data)

        with patch.object(client._client, "request", return_value=mock_response):
            with pytest.raises(InvalidInputError) as exc_info:
                await client.convert_text("test", "text/plain")

            assert "Unsupported format" in str(exc_info.value)
            assert "Unsupported file format" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_422_validation_error_mapping(self, client):
        """Test 422 Unprocessable Entity maps to InvalidInputError."""
        error_data = {
            "error": {
                "message": "Validation failed",
                "details": {
                    "field_errors": [{"field": "url", "message": "Invalid URL format"}]
                },
            }
        }

        mock_response = self.create_mock_error_response(422, error_data)

        with patch.object(client._client, "request", return_value=mock_response):
            with pytest.raises(ConversionError) as exc_info:
                await client.convert_text("test", "text/plain")

            assert "Server error (422)" in str(exc_info.value)
            assert "Validation failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_500_internal_server_error_mapping(self, client):
        """Test 500 Internal Server Error maps to ConversionError."""
        error_data = {
            "error": {
                "message": "Internal processing error",
                "details": {"error_id": "err_12345"},
            }
        }

        mock_response = self.create_mock_error_response(500, error_data)

        with patch.object(client._client, "request", return_value=mock_response):
            with pytest.raises(ConversionError) as exc_info:
                await client.convert_text("test", "text/plain")

            assert "Server error (500)" in str(exc_info.value)
            assert "Internal processing error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_502_bad_gateway_mapping(self, client):
        """Test 502 Bad Gateway maps to ConversionError."""
        error_data = {
            "error": {
                "message": "Upstream service unavailable",
                "details": {"service": "conversion_engine"},
            }
        }

        mock_response = self.create_mock_error_response(502, error_data)

        with patch.object(client._client, "request", return_value=mock_response):
            with pytest.raises(ConversionError) as exc_info:
                await client.convert_text("test", "text/plain")

            assert "Server error (502)" in str(exc_info.value)
            assert "Upstream service unavailable" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_503_service_unavailable_mapping(self, client):
        """Test 503 Service Unavailable maps to ConversionError."""
        error_data = {
            "error": {
                "message": "Service temporarily unavailable",
                "details": {"retry_after": 300},
            }
        }

        mock_response = self.create_mock_error_response(503, error_data)

        with patch.object(client._client, "request", return_value=mock_response):
            with pytest.raises(ConversionError) as exc_info:
                await client.convert_text("test", "text/plain")

            assert "Server error (503)" in str(exc_info.value)
            assert "Service temporarily unavailable" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_error_response_without_json(self, client):
        """Test error response without JSON content."""
        mock_response = self.create_mock_error_response(
            500,
            None,  # No JSON
            "Internal Server Error",
        )

        with patch.object(client._client, "request", return_value=mock_response):
            with pytest.raises(ConversionError) as exc_info:
                await client.convert_text("test", "text/plain")

            assert "HTTP 500: Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_error_response_invalid_json(self, client):
        """Test error response with invalid JSON."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_response.json.side_effect = ValueError("Invalid JSON")

        with patch.object(client._client, "request", return_value=mock_response):
            with pytest.raises(ConversionError) as exc_info:
                await client.convert_text("test", "text/plain")

            assert "HTTP 400: Bad Request" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_error_response_missing_error_field(self, client):
        """Test error response with missing error field."""
        error_data = {"success": False}  # Missing "error" field
        mock_response = self.create_mock_error_response(400, error_data)

        with patch.object(client._client, "request", return_value=mock_response):
            with pytest.raises(ConversionError) as exc_info:
                await client.convert_text("test", "text/plain")

            assert "HTTP 400" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_error_response_malformed_error_structure(self, client):
        """Test error response with malformed error structure."""
        error_data = {"error": "This should be an object, not a string"}
        mock_response = self.create_mock_error_response(400, error_data)

        with patch.object(client._client, "request", return_value=mock_response):
            with pytest.raises(ConversionError) as exc_info:
                await client.convert_text("test", "text/plain")

            assert "HTTP 400" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_health_check_http_errors(self, client):
        """Test health check with HTTP errors."""
        mock_response = self.create_mock_error_response(
            503, {"error": {"message": "Service unavailable"}}
        )

        with patch.object(client._client, "request", return_value=mock_response):
            with pytest.raises(NetworkError) as exc_info:
                await client.health_check()

            assert "Health check failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_formats_http_errors(self, client):
        """Test get_formats with HTTP errors."""
        mock_response = self.create_mock_error_response(
            404, {"error": {"message": "Endpoint not found"}}
        )

        with patch.object(client._client, "request", return_value=mock_response):
            with pytest.raises(NetworkError) as exc_info:
                await client.get_formats()

            assert "Failed to get formats" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_error_details_preservation(self, client):
        """Test that error details are preserved across exception mapping."""
        error_data = {
            "error": {
                "message": "Validation failed",
                "details": {
                    "request_id": "req_123",
                    "timestamp": "2024-01-01T00:00:00Z",
                    "validation_errors": [
                        {"field": "content", "code": "REQUIRED"},
                        {"field": "format", "code": "INVALID"},
                    ],
                },
            }
        }

        mock_response = self.create_mock_error_response(400, error_data)

        with patch.object(client._client, "request", return_value=mock_response):
            with pytest.raises(InvalidInputError) as exc_info:
                await client.convert_text("test", "text/plain")

            # Check that details are preserved
            details = exc_info.value.details
            assert details["request_id"] == "req_123"
            assert details["timestamp"] == "2024-01-01T00:00:00Z"
            assert len(details["validation_errors"]) == 2

    @pytest.mark.asyncio
    async def test_all_conversion_methods_with_http_errors(self, client, tmp_path):
        """Test all conversion methods handle HTTP errors consistently."""
        error_data = {
            "error": {
                "message": "Service unavailable",
                "details": {"code": "SERVICE_DOWN"},
            }
        }
        mock_response = self.create_mock_error_response(503, error_data)

        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        methods_and_args = [
            (client.convert_text, ("test", "text/plain")),
            (client.convert_url, ("https://example.com",)),
            (client.convert_content, (b"test", "test.txt")),
            (client.convert_file, (str(test_file),)),
        ]

        for method, args in methods_and_args:
            with patch.object(client._client, "request", return_value=mock_response):
                with pytest.raises(ConversionError) as exc_info:
                    await method(*args)

                assert "Server error (503)" in str(exc_info.value)
                assert "Service unavailable" in str(exc_info.value)
                assert exc_info.value.details["code"] == "SERVICE_DOWN"
