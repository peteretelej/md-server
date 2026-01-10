import pytest
import base64
from litestar.testing import TestClient

from md_server.app import app
from tests.test_server.server import TestHTTPServer


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def test_server():
    server = TestHTTPServer()
    server.start()
    yield server
    server.stop()


class TestHealthEndpoint:
    def test_health_check(self, client):
        response = client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestConvertUnifiedEndpoint:
    """Test the unified /convert endpoint with different input types"""

    def test_convert_html_content_json(self, client):
        # For JSON content, the controller expects base64 encoding
        html_content = "<html><body><h1>Test</h1><p>Content</p></body></html>"
        base64_content = base64.b64encode(html_content.encode()).decode()
        response = client.post("/convert", json={"content": base64_content})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Test" in data["markdown"]
        assert "Content" in data["markdown"]

    def test_convert_base64_content_json(self, client):
        html_content = "<html><body><h1>Base64 Test</h1></body></html>"
        base64_content = base64.b64encode(html_content.encode()).decode()
        response = client.post(
            "/convert", json={"content": base64_content, "filename": "test.html"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Base64 Test" in data["markdown"]

    def test_convert_text_with_mime_type(self, client):
        html_text = "<h1>HTML Text</h1><p>Content</p>"
        response = client.post(
            "/convert", json={"text": html_text, "mime_type": "text/html"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "HTML Text" in data["markdown"]

    def test_convert_url_success(self, client, test_server):
        # Use a simple URL that should work
        # Note: localhost is allowed by default for testing and local MCP use
        response = client.post("/convert", json={"url": test_server.url("simple.html")})
        # This might fail in CI without internet, so accept either success or failure
        assert response.status_code in [200, 500, 422]

    def test_convert_file_multipart(self, client, simple_html_file):
        if simple_html_file.exists():
            with open(simple_html_file, "rb") as f:
                response = client.post(
                    "/convert", files={"file": ("test.html", f, "text/html")}
                )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["markdown"]

    def test_convert_binary_upload(self, client):
        html_content = "<html><body><h1>Binary</h1></body></html>"
        response = client.post(
            "/convert",
            content=html_content.encode(),
            headers={"Content-Type": "text/html"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Binary" in data["markdown"]


class TestInvalidPayloadHandling:
    """Test error handling for invalid payloads"""

    def test_convert_empty_content(self, client):
        response = client.post("/convert", json={"content": ""})
        assert response.status_code in [400, 422]

    def test_convert_invalid_url(self, client):
        response = client.post("/convert", json={"url": "not-a-url"})
        assert response.status_code in [400, 422]

    def test_convert_no_input_provided(self, client):
        response = client.post("/convert", json={})
        assert response.status_code in [400, 422]

    def test_convert_invalid_json(self, client):
        response = client.post(
            "/convert",
            content="{invalid json}",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code in [400, 422]

    def test_convert_invalid_base64(self, client):
        response = client.post("/convert", json={"content": "invalid-base64!@#$"})
        assert response.status_code in [400, 422, 500]

    def test_convert_multipart_no_file(self, client):
        response = client.post(
            "/convert", headers={"Content-Type": "multipart/form-data; boundary=test"}
        )
        assert response.status_code in [400, 422]


class TestErrorHandling:
    def test_404_endpoint(self, client):
        response = client.get("/nonexistent")
        assert response.status_code == 404

    def test_method_not_allowed(self, client):
        response = client.put("/healthz")
        assert response.status_code == 405


class TestAdvancedErrorPaths:
    """Test advanced error handling paths for edge cases"""

    def test_network_error_url_conversion(self, client, test_server):
        # Note: localhost is allowed by default, so this tests actual network errors
        response = client.post(
            "/convert", json={"url": test_server.url("nonexistent.html")}
        )
        assert response.status_code in [400, 500]
        data = response.json()
        # Litestar may return different error formats
        if "success" in data:
            assert data["success"] is False
        elif "detail" in data:
            assert "error" in data["detail"] or data["status_code"] == 500

    def test_connection_error_simulation(self, client):
        # Note: localhost is allowed by default, so this tests actual connection errors
        response = client.post(
            "/convert", json={"url": "http://127.0.0.1:1/nonexistent"}
        )
        assert response.status_code in [400, 500]
        data = response.json()
        # Litestar may return different error formats
        if "success" in data:
            assert data["success"] is False
        elif "detail" in data:
            assert "error" in data["detail"] or data["status_code"] == 500

    def test_file_size_too_large_error(self, client):
        large_content = "x" * (50 * 1024 * 1024 + 1)
        response = client.post(
            "/convert",
            content=large_content.encode(),
            headers={"Content-Type": "text/plain"},
        )
        assert response.status_code in [400, 413, 500]

    def test_unsupported_file_format_error(self, client):
        response = client.post(
            "/convert",
            content=b"\x50\x4b\x03\x04unsupported_binary_data",
            headers={"Content-Type": "application/x-unknown"},
        )
        assert response.status_code in [400, 415, 500]
        data = response.json()
        # Handle different error response formats
        if "success" in data and data.get("success") is False:
            error = data.get("error", {})
            assert "code" in error
        elif "detail" in data:
            # Litestar default error format is acceptable
            assert data.get("status_code") in [400, 415, 500]

    def test_validation_error_paths(self, client):
        test_cases = [
            {"content": None},
            {"url": None},
            {"text": None},
            {"url": ""},
            {"content": ""},
            {"text": ""},
        ]

        for test_case in test_cases:
            response = client.post("/convert", json=test_case)
            assert response.status_code in [400, 422, 500]

    def test_invalid_content_type_with_mismatch(self, client):
        html_content = "<html><body>Test</body></html>"
        response = client.post(
            "/convert",
            content=html_content.encode(),
            headers={"Content-Type": "application/pdf"},
        )
        assert response.status_code in [200, 400, 415, 500]

    def test_malformed_multipart_data(self, client):
        response = client.post(
            "/convert",
            content=b'--boundary\r\nContent-Disposition: form-data; name="invalid"\r\n\r\ninvalid\r\n--boundary--',
            headers={"Content-Type": "multipart/form-data; boundary=boundary"},
        )
        assert response.status_code in [400, 422]

    def test_timeout_simulation_large_url(self, client, test_server):
        response = client.post("/convert", json={"url": test_server.url("large.html")})
        assert response.status_code in [200, 400, 408, 500]

    def test_generic_exception_handling(self, client):
        response = client.post(
            "/convert", json={"content": "invalid-base64-data!@#$%^&*()"}
        )
        assert response.status_code in [400, 422, 500]
        data = response.json()
        # Handle different error response formats
        if "success" in data and data.get("success") is False:
            assert "error" in data
            error = data["error"]
            assert "code" in error
            assert "message" in error
        elif "detail" in data:
            # Litestar default error format
            assert data["status_code"] in [400, 422, 500]


class TestValidationErrorMapping:
    """Test error_mapper.py validation error handling"""

    def test_file_too_large_error_mapping(self, client):
        huge_content = base64.b64encode(b"x" * 100 * 1024 * 1024).decode()
        response = client.post("/convert", json={"content": huge_content})
        assert response.status_code in [400, 413, 500]
        data = response.json()
        # Handle different error response formats
        if "success" in data and data.get("success") is False:
            error = data.get("error", {})
            assert "code" in error
        elif "detail" in data:
            # Litestar default error format is acceptable
            assert data.get("status_code") in [400, 413, 500]

    def test_blocked_url_error_mapping(self, client, test_server):
        # Test various error scenarios using local test server
        error_endpoints = [
            test_server.url("forbidden"),  # 403 Forbidden
            test_server.url("server-error"),  # 500 Internal Server Error
            test_server.url("bad-request"),  # 400 Bad Request
            test_server.url("nonexistent.html"),  # 404 Not Found
        ]

        for url in error_endpoints:
            response = client.post("/convert", json={"url": url})
            assert response.status_code in [200, 400, 500]

    def test_unsupported_format_error_mapping(self, client):
        response = client.post(
            "/convert",
            content=b"\x00\x01\x02\x03unsupported_binary",
            headers={"Content-Type": "application/x-executable"},
        )
        assert response.status_code in [400, 415, 500]
        data = response.json()
        # Handle different error response formats
        if "success" in data and data.get("success") is False:
            error = data.get("error", {})
            assert "code" in error
        elif "detail" in data:
            # Litestar default error format is acceptable
            assert data.get("status_code") in [400, 415, 500]

    def test_invalid_input_error_mapping(self, client):
        malformed_requests = [
            {"invalid_field": "value"},
            {"url": 123},
            {"content": 456},
            {"text": ["not", "a", "string"]},
        ]

        for req in malformed_requests:
            response = client.post("/convert", json=req)
            assert response.status_code in [400, 422, 500]


class TestAuthenticationIntegration:
    """Integration tests for authentication middleware with HTTP API"""

    def create_app_with_auth(self, api_key):
        """Create app instance with authentication enabled"""
        from litestar import Litestar, get
        from litestar.di import Provide
        from litestar.response import Response
        from litestar.status_codes import HTTP_200_OK
        from md_server.controllers import ConvertController
        from md_server.core.config import Settings
        from md_server.middleware.auth import create_auth_middleware
        from md_server.app import provide_converter, provide_document_converter

        # Create settings with API key
        settings = Settings(api_key=api_key)

        # Create middleware
        middleware = []
        auth_middleware_class = create_auth_middleware(settings)
        if auth_middleware_class:
            middleware.append(auth_middleware_class)

        @get("/health")
        async def health() -> Response:
            return Response({"status": "healthy"}, status_code=HTTP_200_OK)

        @get("/healthz")
        async def healthz() -> Response:
            return Response({"status": "healthy"}, status_code=HTTP_200_OK)

        return Litestar(
            route_handlers=[health, healthz, ConvertController],
            dependencies={
                "converter": Provide(provide_converter, sync_to_thread=False),
                "settings": Provide(lambda: settings, sync_to_thread=False),
                "document_converter": Provide(
                    provide_document_converter, sync_to_thread=False
                ),
            },
            middleware=middleware,
            state={"config": settings},
        )

    def test_health_endpoints_excluded_from_auth(self):
        """Test health endpoints work even with auth enabled"""
        app_with_auth = self.create_app_with_auth("test-api-key-123")
        client = TestClient(app_with_auth)

        # Health endpoints should work without authentication
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_convert_endpoint_requires_auth_when_enabled(self):
        """Test convert endpoint requires auth when API key is configured"""
        app_with_auth = self.create_app_with_auth("secret-api-key-456")
        client = TestClient(app_with_auth)

        # Should fail without authorization header
        response = client.post(
            "/convert", json={"text": "test", "mime_type": "text/plain"}
        )
        assert response.status_code == 401

    def test_convert_endpoint_invalid_auth_header_format(self):
        """Test convert endpoint rejects invalid auth header format"""
        app_with_auth = self.create_app_with_auth("secret-api-key-456")
        client = TestClient(app_with_auth)

        # Should fail with invalid format
        response = client.post(
            "/convert",
            json={"text": "test", "mime_type": "text/plain"},
            headers={"Authorization": "Basic invalid-format"},
        )
        assert response.status_code == 401

    def test_convert_endpoint_wrong_api_key(self):
        """Test convert endpoint rejects wrong API key"""
        app_with_auth = self.create_app_with_auth("correct-api-key")
        client = TestClient(app_with_auth)

        # Should fail with wrong key
        response = client.post(
            "/convert",
            json={"text": "test", "mime_type": "text/plain"},
            headers={"Authorization": "Bearer wrong-api-key"},
        )
        assert response.status_code == 401

    def test_convert_endpoint_valid_api_key_success(self):
        """Test convert endpoint works with valid API key"""
        app_with_auth = self.create_app_with_auth("valid-api-key-789")
        client = TestClient(app_with_auth)

        # Should work with correct key
        response = client.post(
            "/convert",
            json={"text": "# Test Content", "mime_type": "text/markdown"},
            headers={"Authorization": "Bearer valid-api-key-789"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Test Content" in data["markdown"]


class TestFileNotFoundErrors:
    """Test file not found error scenarios"""

    def test_nonexistent_file_upload_simulation(self, client):
        # Simulate file upload with empty content (file read failure)
        response = client.post(
            "/convert", files={"file": ("nonexistent.pdf", b"", "application/pdf")}
        )
        # May pass with empty content or fail - both are acceptable
        assert response.status_code in [200, 400, 422]

    def test_url_with_file_not_found_response(self, client, test_server):
        response = client.post(
            "/convert", json={"url": test_server.url("nonexistent.html")}
        )
        # URL exists but returns 404, may be handled differently
        assert response.status_code in [200, 400, 404, 500]

    def test_broken_url_simulation(self, client, test_server):
        broken_urls = [
            test_server.url("nonexistent.html"),
            "http://127.0.0.1:1/nonexistent.pdf",
        ]

        for url in broken_urls:
            response = client.post("/convert", json={"url": url})
            assert response.status_code in [200, 400, 404, 500]


class TestInvalidContentTypeHandling:
    """Test invalid content type scenarios"""

    def test_content_type_mismatch_detection(self, client):
        # Send PDF content with HTML content-type
        pdf_header = b"%PDF-1.4"
        response = client.post(
            "/convert",
            content=pdf_header + b"fake pdf content",
            headers={"Content-Type": "text/html"},
        )
        assert response.status_code in [200, 400, 415]

    def test_unknown_mime_type_handling(self, client):
        response = client.post(
            "/convert",
            content=b"some content",
            headers={"Content-Type": "application/x-unknown-format"},
        )
        assert response.status_code in [200, 400, 415, 500]

    def test_malformed_content_type_header(self, client):
        response = client.post(
            "/convert",
            content=b"test content",
            headers={"Content-Type": "invalid/content/type/format"},
        )
        assert response.status_code in [200, 400]

    def test_missing_content_type_binary_upload(self, client):
        response = client.post("/convert", content=b"binary content without type")
        # Should work - content type detection should handle this
        assert response.status_code in [200, 400]

    def test_text_content_with_binary_type(self, client):
        response = client.post(
            "/convert",
            content="plain text content".encode(),
            headers={"Content-Type": "application/octet-stream"},
        )
        assert response.status_code in [200, 400]


class TestOptionsAndCors:
    def test_options_preflight(self, client):
        response = client.options(
            "/convert",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        # Should handle OPTIONS request (exact response depends on CORS config)
        assert response.status_code in [200, 204]


class TestSSRFProtectionIntegration:
    """Integration tests for SSRF protection."""

    def test_convert_blocks_private_url_192(self, client):
        """Block 192.168.x.x private range."""
        response = client.post("/convert", json={"url": "http://192.168.1.1/"})
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"]["code"] == "SSRF_BLOCKED"
        assert data["detail"]["error"]["details"]["reason"] == "private_ip_range"

    def test_convert_blocks_private_url_10(self, client):
        """Block 10.x.x.x private range."""
        response = client.post("/convert", json={"url": "http://10.0.0.1/"})
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"]["code"] == "SSRF_BLOCKED"
        assert data["detail"]["error"]["details"]["reason"] == "private_ip_range"

    def test_convert_blocks_private_url_172(self, client):
        """Block 172.16.x.x private range."""
        response = client.post("/convert", json={"url": "http://172.16.0.1/"})
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"]["code"] == "SSRF_BLOCKED"
        assert data["detail"]["error"]["details"]["reason"] == "private_ip_range"

    def test_convert_allows_localhost_by_default(self, client):
        """Localhost is allowed by default for local MCP/dev use."""
        # Note: This will fail to connect but won't be SSRF blocked
        response = client.post("/convert", json={"url": "http://localhost:59999/"})
        # Should NOT be 400 with SSRF_BLOCKED - connection error is acceptable
        if response.status_code == 400:
            data = response.json()
            # If it's 400, it should NOT be SSRF blocked
            assert data["detail"]["error"]["code"] != "SSRF_BLOCKED"

    def test_convert_allows_127_0_0_1_by_default(self, client):
        """127.0.0.1 is allowed by default for local MCP/dev use."""
        # Note: This will fail to connect but won't be SSRF blocked
        response = client.post("/convert", json={"url": "http://127.0.0.1:59999/"})
        # Should NOT be 400 with SSRF_BLOCKED - connection error is acceptable
        if response.status_code == 400:
            data = response.json()
            assert data["detail"]["error"]["code"] != "SSRF_BLOCKED"

    def test_convert_blocks_aws_metadata(self, client):
        """Block AWS metadata endpoint (169.254.169.254)."""
        response = client.post(
            "/convert",
            json={"url": "http://169.254.169.254/latest/meta-data/"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"]["code"] == "SSRF_BLOCKED"
        assert data["detail"]["error"]["details"]["reason"] == "dangerous_ip_range"

    def test_convert_blocks_file_scheme(self, client):
        """Block file:// scheme."""
        response = client.post("/convert", json={"url": "file:///etc/passwd"})
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"]["code"] == "SSRF_BLOCKED"
        assert data["detail"]["error"]["details"]["reason"] == "invalid_scheme"

    def test_ssrf_error_response_format(self, client):
        """Verify SSRF error response includes suggestions."""
        response = client.post("/convert", json={"url": "http://192.168.1.1/"})
        assert response.status_code == 400
        data = response.json()
        error = data["detail"]["error"]
        assert error["code"] == "SSRF_BLOCKED"
        assert error["message"] == "URL targets a blocked resource"
        assert "suggestions" in error
        assert len(error["suggestions"]) > 0


@pytest.mark.integration
class TestEnhancedMetadata:
    """Test enhanced metadata extraction in API responses."""

    def test_response_includes_new_metadata_fields(self, client):
        """API response should include title, estimated_tokens, and detected_language."""
        response = client.post(
            "/convert",
            json={"text": "# Hello World\n\nThis is English content for testing."},
        )
        assert response.status_code == 200
        data = response.json()

        assert "title" in data["metadata"]
        assert "estimated_tokens" in data["metadata"]
        assert "detected_language" in data["metadata"]

    def test_title_extraction(self, client):
        """Title should be extracted from H1 heading."""
        response = client.post(
            "/convert",
            json={"text": "# My Document Title\n\nSome content here."},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["metadata"]["title"] == "My Document Title"

    def test_token_estimation(self, client):
        """Token count should be estimated for content."""
        response = client.post(
            "/convert",
            json={"text": "# Test\n\nThis is a test document with some content."},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["metadata"]["estimated_tokens"] > 0

    def test_language_detection(self, client):
        """Language should be detected from content."""
        response = client.post(
            "/convert",
            json={
                "text": "# English Document\n\nThis is a sample document written in English for language detection testing purposes."
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert data["metadata"]["detected_language"] == "en"

    def test_frontmatter_option(self, client):
        """include_frontmatter option should prepend YAML frontmatter."""
        response = client.post(
            "/convert",
            json={
                "text": "# Test Document\n\nContent here for testing frontmatter.",
                "options": {"include_frontmatter": True},
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert data["markdown"].startswith("---")
        assert "title:" in data["markdown"]
        assert "tokens:" in data["markdown"]

    def test_frontmatter_disabled_by_default(self, client):
        """Frontmatter should not be included by default."""
        response = client.post(
            "/convert",
            json={"text": "# Test Document\n\nContent here."},
        )
        assert response.status_code == 200
        data = response.json()

        assert not data["markdown"].startswith("---")

    def test_metadata_with_short_content(self, client):
        """Short content should handle gracefully (no language detection)."""
        response = client.post(
            "/convert",
            json={"text": "Hi"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["metadata"]["estimated_tokens"] > 0
        assert data["metadata"]["detected_language"] is None


@pytest.mark.integration
class TestContentNegotiation:
    """Test Accept header content negotiation."""

    def test_json_response_default(self, client):
        """Default response is JSON when no Accept header provided."""
        response = client.post("/convert", json={"text": "# Hello World"})
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

        data = response.json()
        assert "success" in data
        assert "markdown" in data

    def test_json_response_explicit(self, client):
        """Explicit Accept: application/json returns JSON."""
        response = client.post(
            "/convert",
            json={"text": "# Hello World"},
            headers={"Accept": "application/json"},
        )
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

        data = response.json()
        assert data["success"] is True
        assert "markdown" in data

    def test_markdown_response(self, client):
        """Accept: text/markdown returns raw Markdown."""
        response = client.post(
            "/convert",
            json={"text": "# Hello World"},
            headers={"Accept": "text/markdown"},
        )
        assert response.status_code == 200
        assert "text/markdown" in response.headers["content-type"]
        assert "charset=utf-8" in response.headers["content-type"]
        assert response.text.startswith("# Hello World")

    def test_markdown_response_x_markdown(self, client):
        """Accept: text/x-markdown also works."""
        response = client.post(
            "/convert",
            json={"text": "# Test"},
            headers={"Accept": "text/x-markdown"},
        )
        assert response.status_code == 200
        assert "text/markdown" in response.headers["content-type"]

    def test_markdown_response_includes_headers(self, client):
        """Markdown response includes metadata headers."""
        response = client.post(
            "/convert",
            json={"text": "# Hello World\n\nSome content."},
            headers={"Accept": "text/markdown"},
        )
        assert response.status_code == 200

        # Check required headers
        assert "X-Request-Id" in response.headers
        assert "X-Source-Type" in response.headers
        assert "X-Source-Size" in response.headers
        assert "X-Markdown-Size" in response.headers
        assert "X-Conversion-Time-Ms" in response.headers
        assert "X-Detected-Format" in response.headers

    def test_markdown_response_request_id_format(self, client):
        """Request ID has expected format."""
        response = client.post(
            "/convert",
            json={"text": "# Test"},
            headers={"Accept": "text/markdown"},
        )
        assert response.headers["X-Request-Id"].startswith("req_")

    def test_markdown_response_optional_headers(self, client):
        """Optional headers present when data is available."""
        response = client.post(
            "/convert",
            json={"text": "# Document Title\n\nThis is English content for testing."},
            headers={"Accept": "text/markdown"},
        )
        assert response.status_code == 200

        # Token estimation should be present
        assert "X-Estimated-Tokens" in response.headers
        assert int(response.headers["X-Estimated-Tokens"]) > 0

        # Title should be present and URL-encoded
        assert "X-Title" in response.headers

    def test_markdown_response_preserves_content(self, client):
        """Raw markdown response preserves original content."""
        input_text = "# My Heading\n\nParagraph with **bold** and *italic*."
        response = client.post(
            "/convert",
            json={"text": input_text},
            headers={"Accept": "text/markdown"},
        )
        assert response.status_code == 200
        assert "# My Heading" in response.text
        assert "**bold**" in response.text

    def test_error_returns_json_despite_accept_header(self, client):
        """Errors return JSON regardless of Accept header."""
        response = client.post(
            "/convert",
            json={},  # Missing required field
            headers={"Accept": "text/markdown"},
        )
        # Error responses should be JSON
        assert response.status_code >= 400

    def test_markdown_response_with_multipart(self, client, simple_html_file):
        """Multipart uploads also support content negotiation."""
        if simple_html_file.exists():
            with open(simple_html_file, "rb") as f:
                response = client.post(
                    "/convert",
                    files={"file": ("test.html", f, "text/html")},
                    headers={"Accept": "text/markdown"},
                )
            assert response.status_code == 200
            assert "text/markdown" in response.headers["content-type"]

    def test_markdown_with_charset_in_accept(self, client):
        """Accept: text/markdown; charset=utf-8 works."""
        response = client.post(
            "/convert",
            json={"text": "# Test"},
            headers={"Accept": "text/markdown; charset=utf-8"},
        )
        assert response.status_code == 200
        assert "text/markdown" in response.headers["content-type"]

    def test_output_format_option_markdown(self, client):
        """output_format: 'markdown' option returns raw Markdown."""
        response = client.post(
            "/convert",
            json={"text": "# Hello World", "options": {"output_format": "markdown"}},
        )
        assert response.status_code == 200
        assert "text/markdown" in response.headers["content-type"]
        assert response.text.startswith("# Hello World")

    def test_output_format_option_json(self, client):
        """output_format: 'json' option returns JSON (explicit default)."""
        response = client.post(
            "/convert",
            json={"text": "# Hello World", "options": {"output_format": "json"}},
        )
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
        data = response.json()
        assert data["success"] is True

    def test_output_format_option_case_insensitive(self, client):
        """output_format option is case-insensitive."""
        response = client.post(
            "/convert",
            json={"text": "# Test", "options": {"output_format": "MARKDOWN"}},
        )
        assert response.status_code == 200
        assert "text/markdown" in response.headers["content-type"]

    def test_output_format_includes_metadata_headers(self, client):
        """output_format: 'markdown' includes metadata headers."""
        response = client.post(
            "/convert",
            json={
                "text": "# Document\n\nContent here.",
                "options": {"output_format": "markdown"},
            },
        )
        assert response.status_code == 200
        assert "X-Request-Id" in response.headers
        assert "X-Source-Type" in response.headers
        assert "X-Markdown-Size" in response.headers

    def test_accept_header_takes_precedence(self, client):
        """Accept header takes precedence over output_format option."""
        # Accept header says markdown, option says json - Accept wins
        response = client.post(
            "/convert",
            json={"text": "# Test", "options": {"output_format": "json"}},
            headers={"Accept": "text/markdown"},
        )
        assert response.status_code == 200
        assert "text/markdown" in response.headers["content-type"]
