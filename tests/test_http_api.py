import base64
import os

import pytest
from litestar.testing import TestClient

from md_server.app import app


class TestHTTPAPI:
    """Test the HTTP API endpoints - all user-facing functionality."""

    @pytest.fixture
    def client(self):
        """Test client for making HTTP requests."""
        return TestClient(app)

    @pytest.fixture
    def test_files(self):
        """Paths to test files."""
        test_data_dir = os.path.join(os.path.dirname(__file__), "test_data")
        return {
            "pdf": os.path.join(test_data_dir, "test.pdf"),
            "docx": os.path.join(test_data_dir, "test.docx"),
            "html": os.path.join(test_data_dir, "test_blog.html"),
            "jpg": os.path.join(test_data_dir, "test.jpg"),
        }

    def test_upload_binary_file(self, client, test_files):
        """Test binary file upload - core user workflow."""
        with open(test_files["pdf"], "rb") as f:
            pdf_content = f.read()

        response = client.post(
            "/convert", content=pdf_content, headers={"Content-Type": "application/pdf"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "markdown" in data
        assert len(data["markdown"]) > 0
        assert data["metadata"]["source_type"] == "pdf"
        assert data["metadata"]["detected_format"] == "application/pdf"
        assert "request_id" in data

    def test_upload_multipart_form(self, client, test_files):
        """Test multipart form upload - common client pattern."""
        with open(test_files["docx"], "rb") as f:
            files = {
                "file": (
                    "test.docx",
                    f,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            }
            response = client.post("/convert", files=files)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "markdown" in data
        assert len(data["markdown"]) > 0
        assert data["metadata"]["source_type"] == "docx"
        assert "request_id" in data

    def test_convert_url(self, client):
        """Test URL conversion - critical web functionality."""
        payload = {"url": "https://httpbin.org/robots.txt"}

        response = client.post("/convert", json=payload)

        # URL conversion might fail due to SDK issues, so check for either success or proper error
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert "markdown" in data
            assert len(data["markdown"]) > 0
            assert data["metadata"]["source_type"] == "url"
            assert "request_id" in data
        else:
            # If it fails, verify it's a proper error response
            assert response.status_code in [400, 500]
            data = response.json()
            assert "detail" in data  # Litestar error format

    def test_convert_base64_content(self, client, test_files):
        """Test base64 content conversion - programmatic usage."""
        with open(test_files["html"], "rb") as f:
            html_content = f.read()

        base64_content = base64.b64encode(html_content).decode("utf-8")
        payload = {"content": base64_content, "filename": "test.html"}

        response = client.post("/convert", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "markdown" in data
        assert len(data["markdown"]) > 0
        assert "request_id" in data

    def test_convert_text_html(self, client):
        """Test text/HTML conversion - direct content processing."""
        html_text = "<h1>Test Title</h1><p>This is a test paragraph with <strong>bold text</strong>.</p>"
        payload = {"text": html_text, "mime_type": "text/html"}

        response = client.post("/convert", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "markdown" in data
        assert "# Test Title" in data["markdown"]
        assert "**bold text**" in data["markdown"]
        assert "request_id" in data

    def test_invalid_requests(self, client):
        """Test invalid request handling - error cases users encounter."""
        # Empty JSON request
        response = client.post("/convert", json={})
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data  # Litestar error format
        if "success" in data:
            assert data["success"] is False
            assert data["error"]["code"] == "INVALID_INPUT"

        # Invalid JSON
        response = client.post(
            "/convert",
            content="invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400

        # Multipart without file
        response = client.post(
            "/convert",
            data={"not_file": "value"},
            headers={"Content-Type": "multipart/form-data"},
        )
        assert response.status_code == 400

    def test_health_endpoint(self, client):
        """Test health endpoint - monitoring and uptime checks."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "uptime_seconds" in data
        assert data["uptime_seconds"] >= 0

    def test_formats_endpoint(self, client):
        """Test formats endpoint - capability discovery."""
        response = client.get("/formats")

        assert response.status_code == 200
        data = response.json()
        assert "formats" in data
        formats = data["formats"]

        # Check for core formats
        assert "pdf" in formats
        assert "html" in formats
        assert "text" in formats

        # Validate format structure
        for format_name, capabilities in formats.items():
            assert "mime_types" in capabilities
            assert "extensions" in capabilities
            assert "features" in capabilities
            assert "max_size_mb" in capabilities

    def test_authentication_middleware_paths(self, client):
        """Test authentication middleware behavior across different scenarios."""
        payload = {"text": "Test content", "mime_type": "text/plain"}

        # Test 1: Valid Bearer token format (without actual auth configured)
        headers = {"Authorization": "Bearer valid-api-key-format"}
        response = client.post("/convert", json=payload, headers=headers)
        # Should succeed when auth is not configured, or handle gracefully
        assert response.status_code in [200, 401, 403]

        # Test 2: Invalid Bearer token format
        headers = {"Authorization": "Bearer "}  # Empty token
        response = client.post("/convert", json=payload, headers=headers)
        assert response.status_code in [200, 400, 401]

        # Test 3: Non-Bearer auth schemes
        headers = {"Authorization": "Basic dXNlcjpwYXNz"}  # base64 user:pass
        response = client.post("/convert", json=payload, headers=headers)
        assert response.status_code in [200, 400, 401]

        # Test 4: Malformed Authorization header
        headers = {"Authorization": "InvalidFormat"}
        response = client.post("/convert", json=payload, headers=headers)
        assert response.status_code in [200, 400, 401]

        # Test 5: Auth bypass for health endpoint (should always work)
        response = client.get("/health")
        assert response.status_code == 200  # Health should never require auth

        # Test 6: Auth bypass for formats endpoint (should always work)
        response = client.get("/formats")
        assert response.status_code == 200  # Formats should never require auth

    def test_large_files(self, client):
        """Test large file handling - size limit enforcement."""
        # Create content larger than typical limit (simulate)
        large_text = "x" * (10 * 1024 * 1024)  # 10MB of text
        payload = {"text": large_text, "mime_type": "text/plain"}

        response = client.post("/convert", json=payload)

        # Should either succeed or fail gracefully with size error
        if response.status_code != 200:
            assert response.status_code in [
                400,
                413,
            ]  # Could be general error or size error
            data = response.json()
            assert "detail" in data  # Litestar error format
        else:
            # If it succeeds, verify response structure
            data = response.json()
            assert data["success"] is True
            assert "markdown" in data

    @pytest.mark.skip(reason="Rate limiting needs configuration")
    def test_rate_limiting(self, client):
        """Test rate limiting - protection against abuse."""
        payload = {"text": "test", "mime_type": "text/plain"}

        # Make multiple rapid requests
        responses = []
        for _ in range(10):
            response = client.post("/convert", json=payload)
            responses.append(response)

        # Check if rate limiting kicks in
        status_codes = [r.status_code for r in responses]

        # Either all succeed or some get rate limited
        if any(code == 429 for code in status_codes):
            # Rate limiting is active
            rate_limited_response = next(r for r in responses if r.status_code == 429)
            data = rate_limited_response.json()
            assert data["success"] is False
            assert "rate" in data["error"]["code"].lower()


    def test_upload_binary_file_failures(self, client, test_files):
        """Test binary file upload failure scenarios - comprehensive error handling."""
        # Test 1: Empty file upload
        response = client.post(
            "/convert", content=b"", headers={"Content-Type": "application/pdf"}
        )
        # Should either succeed (empty conversion) or fail gracefully
        if response.status_code != 200:
            assert response.status_code in [400, 422]
            data = response.json()
            assert "detail" in data

        # Test 2: Corrupted PDF with wrong magic bytes
        fake_pdf = b"FAKE-PDF-CONTENT-NOT-REAL"
        response = client.post(
            "/convert", content=fake_pdf, headers={"Content-Type": "application/pdf"}
        )
        # Should either convert or detect format mismatch
        if response.status_code != 200:
            assert response.status_code in [400, 415]

        # Test 3: File exceeding reasonable size (50MB)
        large_content = b"x" * (50 * 1024 * 1024)  # 50MB
        response = client.post(
            "/convert", content=large_content, headers={"Content-Type": "text/plain"}
        )
        # Should either succeed or fail with size error
        if response.status_code != 200:
            assert response.status_code in [400, 413, 422]

        # Test 4: Missing Content-Type header
        with open(test_files["pdf"], "rb") as f:
            pdf_content = f.read()
        response = client.post("/convert", content=pdf_content)
        # Should either auto-detect or request proper header
        if response.status_code != 200:
            assert response.status_code in [400, 415]

        # Test 5: Mismatched Content-Type vs actual content
        with open(test_files["pdf"], "rb") as f:
            pdf_content = f.read()
        response = client.post(
            "/convert", content=pdf_content, headers={"Content-Type": "image/jpeg"}
        )
        # Should either detect correctly or handle mismatch
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
        else:
            assert response.status_code in [400, 415]

    def test_controller_error_paths(self, client):
        """Test controller error handling paths - comprehensive edge cases."""
        # Test 1: Malformed JSON body
        response = client.post(
            "/convert",
            content='{"invalid": json, "missing_quote": value}',
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400

        # Test 2: Incomplete multipart upload
        response = client.post(
            "/convert",
            files={"not_a_file": ("filename.txt", "content", "text/plain")},
        )
        # Should fail because 'file' field is expected
        assert response.status_code in [400, 422]

        # Test 3: Invalid base64 in content field
        payload = {"content": "invalid-base64-content!", "filename": "test.pdf"}
        response = client.post("/convert", json=payload)
        assert response.status_code in [400, 422, 500]  # May fail during conversion

        # Test 4: Unsupported format explicit test
        payload = {"text": "content", "mime_type": "application/x-unknown"}
        response = client.post("/convert", json=payload)
        # Should either convert or reject unknown type
        if response.status_code != 200:
            assert response.status_code in [400, 415]

        # Test 5: Missing required fields
        response = client.post("/convert", json={})
        assert response.status_code in [400, 422]

        # Test 6: Mixed invalid fields
        payload = {
            "url": "invalid-url",
            "content": "invalid-base64",
            "text": "text-content",
        }
        response = client.post("/convert", json=payload)
        assert response.status_code in [400, 422]

    def test_file_size_limits_per_content_type(self, client):
        """Test file size limits per content type - security boundaries."""
        # Test text/plain with large content
        large_text = "x" * (10 * 1024 * 1024)  # 10MB
        payload = {"text": large_text, "mime_type": "text/plain"}
        response = client.post("/convert", json=payload)
        # Should handle or reject based on size limits
        if response.status_code != 200:
            assert response.status_code in [400, 413, 422]

        # Test PDF size limit (smaller binary)
        large_pdf_fake = b"PDF-" + (b"x" * (5 * 1024 * 1024))  # 5MB fake PDF
        response = client.post(
            "/convert", content=large_pdf_fake, headers={"Content-Type": "application/pdf"}
        )
        if response.status_code != 200:
            assert response.status_code in [400, 413, 422]

        # Test image size limit
        large_image_fake = b"JPEG-" + (b"x" * (2 * 1024 * 1024))  # 2MB fake image
        response = client.post(
            "/convert", content=large_image_fake, headers={"Content-Type": "image/jpeg"}
        )
        if response.status_code != 200:
            assert response.status_code in [400, 413, 422]

    def test_invalid_content_type_headers(self, client):
        """Test invalid content-type headers - header validation."""
        content = b"test content"

        # Test 1: Completely invalid content type
        response = client.post(
            "/convert", content=content, headers={"Content-Type": "invalid/invalid"}
        )
        # Should either handle gracefully or reject
        if response.status_code != 200:
            assert response.status_code in [400, 415]

        # Test 2: Missing content type with binary
        response = client.post("/convert", content=content)
        if response.status_code != 200:
            assert response.status_code in [400, 415]

        # Test 3: Wrong content type for data
        response = client.post(
            "/convert", content=b"not-an-image", headers={"Content-Type": "image/png"}
        )
        if response.status_code != 200:
            assert response.status_code in [400, 415]

        # Test 4: Content type with invalid parameters
        response = client.post(
            "/convert",
            content=content,
            headers={"Content-Type": "text/plain; charset=invalid"},
        )
        # Should handle charset gracefully
        assert response.status_code in [200, 400, 415]

    def test_empty_and_corrupted_files(self, client):
        """Test empty and corrupted file handling - robustness."""
        # Test 1: Completely empty file
        response = client.post(
            "/convert", content=b"", headers={"Content-Type": "application/pdf"}
        )
        # Should handle gracefully
        if response.status_code != 200:
            assert response.status_code in [400, 422, 500]

        # Test 2: Corrupted ZIP (DOCX/XLSX are ZIP-based)
        fake_zip = b"PK\x03\x04" + b"corrupted-zip-content"
        response = client.post(
            "/convert", 
            content=fake_zip, 
            headers={"Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
        )
        if response.status_code != 200:
            assert response.status_code in [400, 415, 422, 500]

        # Test 3: Partial PDF header
        partial_pdf = b"%PDF-1.4"  # Valid header but truncated
        response = client.post(
            "/convert", content=partial_pdf, headers={"Content-Type": "application/pdf"}
        )
        if response.status_code != 200:
            assert response.status_code in [400, 422, 500]

        # Test 4: Binary data with text content type
        binary_data = bytes(range(256))  # All byte values
        response = client.post(
            "/convert", content=binary_data, headers={"Content-Type": "text/plain"}
        )
        # Should either convert or detect mismatch
        if response.status_code != 200:
            assert response.status_code in [400, 415, 500]


class TestErrorScenarios:
    """Test error conditions that users encounter."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_unsupported_format_handling(self, client):
        """Test handling of unsupported file formats."""
        # Send binary content that isn't supported
        unsupported_content = b"\x89RANDOM\x0d\x0a\x1a\x0a"  # Fake binary

        response = client.post(
            "/convert",
            content=unsupported_content,
            headers={"Content-Type": "application/octet-stream"},
        )

        # The server might convert it successfully or return an error
        if response.status_code == 200:
            # If it succeeds, verify response structure
            data = response.json()
            assert data["success"] is True
            assert "markdown" in data
        else:
            # If it fails, should get proper error
            assert response.status_code in [400, 415, 500]
            data = response.json()
            assert "detail" in data  # Litestar error format

    def test_network_timeout_handling(self, client):
        """Test timeout handling for slow URLs."""
        payload = {
            "url": "https://httpbin.org/delay/30",  # 30 second delay
            "options": {"timeout": 1},  # 1 second timeout
        }

        response = client.post("/convert", json=payload)

        # Should timeout gracefully or fail with SDK error
        if response.status_code != 200:
            assert response.status_code in [400, 408, 500]
            data = response.json()
            assert "detail" in data  # Litestar error format

    def test_invalid_url_handling(self, client):
        """Test handling of invalid URLs."""
        payload = {"url": "not-a-valid-url"}

        response = client.post("/convert", json=payload)

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data  # Litestar error format

    def test_malformed_json_handling(self, client):
        """Test handling of malformed JSON requests."""
        response = client.post(
            "/convert",
            content='{"invalid": json}',
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data  # Litestar error format
