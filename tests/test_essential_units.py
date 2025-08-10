import pytest
from unittest.mock import patch

from md_server.detection import ContentTypeDetector
from md_server.security import FileSizeValidator, SSRFProtection
from md_server.models import ConversionOptions


class TestSecurityValidators:
    """Unit tests for critical security validation logic."""

    def test_file_size_validation_enforced(self):
        """Test that file size limits are enforced."""

        # Small file should pass
        FileSizeValidator.validate_size(1024, "text/plain")  # 1KB

        # Large file should fail
        with pytest.raises(ValueError, match="exceeds"):
            FileSizeValidator.validate_size(100 * 1024 * 1024, "text/plain")  # 100MB

    def test_ssrf_protection_blocks_private_ips(self):
        """Test that SSRF protection blocks private IP addresses."""

        # Valid public URL should pass
        SSRFProtection.validate_url("https://example.com")

        # Private IP addresses should be blocked
        private_urls = [
            "http://127.0.0.1/test",
            "http://192.168.1.1/admin",
            "http://10.0.0.1/internal",
            "http://169.254.169.254/metadata",
        ]

        for url in private_urls:
            with pytest.raises(ValueError):
                SSRFProtection.validate_url(url)

    def test_ssrf_protection_blocks_invalid_schemes(self):
        """Test that SSRF protection blocks dangerous schemes."""

        dangerous_urls = [
            "file:///etc/passwd",
            "ftp://example.com/file",
            "javascript:alert('xss')",
            "ldap://attacker.com",
        ]

        for url in dangerous_urls:
            with pytest.raises(ValueError):
                SSRFProtection.validate_url(url)


class TestContentDetection:
    """Unit tests for content type detection."""

    def test_json_input_detection(self):
        """Test JSON input type detection."""

        # URL input
        input_type, format_type = ContentTypeDetector.detect_input_type(
            request_data={"url": "https://example.com"}
        )
        assert input_type == "json_url"
        assert format_type == "text/url"

        # Text input
        input_type, format_type = ContentTypeDetector.detect_input_type(
            request_data={"text": "Some text"}
        )
        assert input_type == "json_text"
        assert format_type == "text/plain"

    def test_supported_formats_structure(self):
        """Test that supported formats have correct structure."""
        formats = ContentTypeDetector.get_supported_formats()

        assert isinstance(formats, dict)
        assert "pdf" in formats

        # Check required fields in format definitions
        pdf_info = formats["pdf"]
        required_fields = ["mime_types", "extensions", "features", "max_size_mb"]
        assert all(field in pdf_info for field in required_fields)
        assert isinstance(pdf_info["mime_types"], list)
        assert isinstance(pdf_info["features"], list)


class TestConversionOptions:
    """Unit tests for conversion options validation."""

    def test_default_options_are_safe(self):
        """Test that default options are secure."""
        options = ConversionOptions()

        # Default should be secure/conservative settings
        assert (
            options.js_rendering is None or options.js_rendering is False
        )  # JS disabled by default
        assert options.timeout is None  # No custom timeout
        assert options.extract_images is False  # Images not extracted by default
        assert options.max_length is None  # No length limit by default

    def test_options_validation(self):
        """Test options can be set correctly."""
        options = ConversionOptions(js_rendering=True, timeout=30, max_length=1000)

        assert options.js_rendering is True
        assert options.timeout == 30
        assert options.max_length == 1000


class TestErrorHandling:
    """Unit tests for error response formats."""

    def test_error_response_structure(self):
        """Test that error responses have consistent structure."""
        from md_server.models import ErrorResponse

        error = ErrorResponse.create_error(
            code="TEST_ERROR",
            message="Test error message",
            suggestions=["Try something else"],
        )

        assert error.success is False
        assert error.error.code == "TEST_ERROR"
        assert error.error.message == "Test error message"
        assert "Try something else" in error.error.suggestions
        assert error.request_id.startswith("req_")

    def test_success_response_structure(self):
        """Test that success responses have consistent structure."""
        from md_server.models import ConvertResponse

        response = ConvertResponse.create_success(
            markdown="# Test",
            source_type="text",
            source_size=10,
            conversion_time_ms=100,
            detected_format="text/plain",
            warnings=[],
        )

        assert response.success is True
        assert response.markdown == "# Test"
        assert response.metadata.source_type == "text"
        assert response.metadata.source_size == 10
        assert response.metadata.conversion_time_ms == 100
        assert response.request_id.startswith("req_")


class TestAuthMiddleware:
    """Unit tests for authentication middleware."""

    def test_auth_middleware_creation(self):
        """Test auth middleware is created when API key is set."""
        from md_server.middleware.auth import create_auth_middleware
        from md_server.core.config import Settings

        # No API key - no middleware
        settings = Settings()
        middleware = create_auth_middleware(settings)
        assert middleware is None

        # With API key - middleware created
        settings_with_key = Settings(api_key="test-key")
        middleware = create_auth_middleware(settings_with_key)
        assert middleware is not None

    @patch.dict("os.environ", {"MD_SERVER_API_KEY": "env-test-key"})
    def test_auth_middleware_from_env(self):
        """Test auth middleware picks up API key from environment."""
        from md_server.middleware.auth import create_auth_middleware
        from md_server.core.config import Settings

        settings = Settings()
        middleware = create_auth_middleware(settings)
        assert middleware is not None  # Should create middleware from env var
