"""
Tests for pure utility functions extracted in Phase 0.
"""

import pytest
import base64
import httpx

from src.md_server.sdk.core.utils import (
    build_auth_headers,
    classify_request_exception,
    should_retry_request,
    calculate_retry_delay,
)
from src.md_server.core.error_mapper import (
    map_conversion_error,
    map_value_error,
    map_generic_error,
    calculate_source_size,
)
from src.md_server.sdk.core.validation import (
    validate_file_path,
    validate_file_size_limits,
    validate_remote_file_size,
    detect_file_content_type,
    validate_conversion_options,
    sanitize_filename_for_api,
)
from src.md_server.security import (
    URLValidator,
    FileSizeValidator,
    ContentValidator,
    MimeTypeValidator,
)
from src.md_server.sdk.exceptions import (
    InvalidInputError,
    FileSizeError,
    UnsupportedFormatError,
    TimeoutError,
    NetworkError,
)


class TestSDKCoreUtils:
    """Test utility functions from sdk/core/utils.py"""

    def test_build_auth_headers_without_api_key(self):
        headers = build_auth_headers(None)
        expected = {"User-Agent": "md-server-sdk/1.0", "Accept": "application/json"}
        assert headers == expected
        assert "Authorization" not in headers

    def test_build_auth_headers_with_api_key(self):
        api_key = "test-api-key-123"
        headers = build_auth_headers(api_key)
        expected = {
            "User-Agent": "md-server-sdk/1.0", 
            "Accept": "application/json",
            "Authorization": "Bearer test-api-key-123"
        }
        assert headers == expected

    def test_build_auth_headers_with_empty_api_key(self):
        headers = build_auth_headers("")
        expected = {"User-Agent": "md-server-sdk/1.0", "Accept": "application/json"}
        assert headers == expected
        assert "Authorization" not in headers

    @pytest.mark.parametrize("exception,expected", [
        (httpx.TimeoutException("Timeout"), "timeout"),
        (httpx.NetworkError("Network error"), "network"),
        (httpx.ConnectError("Connection failed"), "network"),
        (ConnectionError("Connection refused"), "network"),
        (OSError("OS error"), "network"),
        (Exception("connection lost"), "network"),
        (Exception("network unavailable"), "network"),
        (Exception("connection refused"), "network"),
        (Exception("host unreachable"), "network"),
        (Exception("something else"), "unknown"),
    ])
    def test_classify_request_exception(self, exception, expected):
        result = classify_request_exception(exception)
        assert result == expected

    @pytest.mark.parametrize("attempt,max_retries,exception_type,expected", [
        (0, 3, httpx.TimeoutException, True),
        (1, 3, httpx.NetworkError, True),
        (2, 3, httpx.ConnectError, True),
        (3, 3, httpx.TimeoutException, False),  # At max retries
        (4, 3, httpx.NetworkError, False),  # Exceeded max retries
        (0, 3, ValueError, False),  # Non-retryable exception
        (1, 3, Exception, False),  # Generic exception not retryable
    ])
    def test_should_retry_request(self, attempt, max_retries, exception_type, expected):
        exception = exception_type("Test error")
        result = should_retry_request(attempt, max_retries, exception)
        assert result == expected

    @pytest.mark.parametrize("attempt,base_delay,expected", [
        (0, 1.0, 1.0),
        (1, 1.0, 2.0),
        (2, 1.0, 4.0),
        (3, 1.0, 8.0),
        (0, 0.5, 0.5),
        (1, 0.5, 1.0),
        (2, 0.5, 2.0),
    ])
    def test_calculate_retry_delay(self, attempt, base_delay, expected):
        result = calculate_retry_delay(attempt, base_delay)
        assert result == expected


class TestErrorMapper:
    """Test error mapping functions from core/error_mapper.py"""

    @pytest.mark.parametrize("error,expected_code,expected_status", [
        (InvalidInputError("Invalid input"), "INVALID_INPUT", 400),
        (FileSizeError("File too large"), "FILE_TOO_LARGE", 413),
        (UnsupportedFormatError("Unsupported format"), "UNSUPPORTED_FORMAT", 415),
        (TimeoutError("Request timeout"), "TIMEOUT", 408),
        (NetworkError("Network error"), "NETWORK_ERROR", 400),
        (Exception("Generic error"), "CONVERSION_FAILED", 500),
    ])
    def test_map_conversion_error(self, error, expected_code, expected_status):
        code, message, status_code, suggestions = map_conversion_error(error)
        assert code == expected_code
        assert message == str(error)
        assert status_code == expected_status
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0

    @pytest.mark.parametrize("error_msg,expected_code,expected_status", [
        ("File size exceeds limit", "FILE_TOO_LARGE", 413),
        ("URL not allowed", "INVALID_URL", 400),
        ("Private IP blocked", "INVALID_URL", 400), 
        ("Content type mismatch detected", "INVALID_CONTENT", 400),
        ("Random error message", "INVALID_INPUT", 400),
    ])
    def test_map_value_error(self, error_msg, expected_code, expected_status):
        code, status_code, suggestions = map_value_error(error_msg)
        assert code == expected_code
        assert status_code == expected_status
        assert isinstance(suggestions, list)

    def test_map_generic_error_unsupported_format(self):
        error_msg = "Format unsupported by converter"
        format_type = "application/custom"
        code, status_code, details, suggestions = map_generic_error(error_msg, format_type)
        assert code == "UNSUPPORTED_FORMAT"
        assert status_code == 415
        assert details == {"detected_format": format_type}
        assert isinstance(suggestions, list)

    def test_map_generic_error_generic_case(self):
        error_msg = "Random conversion error"
        code, status_code, details, suggestions = map_generic_error(error_msg)
        assert code == "CONVERSION_FAILED"
        assert status_code == 500
        assert details == {}
        assert isinstance(suggestions, list)

    @pytest.mark.parametrize("input_type,request_data,expected", [
        ("json_url", {"url": "https://example.com"}, 19),
        ("json_text", {"text": "Hello world"}, 11),
        ("json_text_typed", {"text": "Test content"}, 12),
        ("json_content", {"content": base64.b64encode(b"test").decode()}, 4),
        ("json_content", {"content": "invalid-base64!"}, 0),  # Invalid base64
        ("unknown", {}, 0),
    ])
    def test_calculate_source_size(self, input_type, request_data, expected):
        content_data = None
        result = calculate_source_size(input_type, content_data, request_data)
        assert result == expected

    def test_calculate_source_size_with_content_data(self):
        input_type = "unknown"
        content_data = {"content": "test content"}
        request_data = {}
        result = calculate_source_size(input_type, content_data, request_data)
        assert result == len("test content")


class TestSDKValidation:
    """Test validation functions from sdk/core/validation.py"""

    def test_validate_file_path_valid(self):
        path = validate_file_path("/path/to/file.txt")
        assert path.name == "file.txt"

    @pytest.mark.parametrize("invalid_path", [
        "",
        None,
        "   ",
        "/",
        "//",
    ])
    def test_validate_file_path_invalid(self, invalid_path):
        with pytest.raises(InvalidInputError):
            validate_file_path(invalid_path)

    def test_validate_file_size_limits_valid(self):
        limits = {"default": 1024, "image": 512}
        validate_file_size_limits(100, "image/png", limits)  # Should not raise

    @pytest.mark.parametrize("size,content_type,should_fail", [
        (-1, "text/plain", True),  # Negative size
        (0, "text/plain", True),   # Zero size
        (1000, "image/png", True), # Exceeds image limit (512)
        (500, "image/png", False), # Within image limit
        (2000, "text/plain", True), # Exceeds default limit (1024)
        (800, "text/plain", False), # Within default limit
    ])
    def test_validate_file_size_limits(self, size, content_type, should_fail):
        limits = {"default": 1024, "image": 512}
        if should_fail:
            with pytest.raises(InvalidInputError):
                validate_file_size_limits(size, content_type, limits)
        else:
            validate_file_size_limits(size, content_type, limits)

    @pytest.mark.parametrize("size,max_size,should_fail", [
        (-1, 1024, True),   # Negative size
        (0, 1024, True),    # Zero size
        (2000, 1024, True), # Exceeds limit
        (500, 1024, False), # Within limit
    ])
    def test_validate_remote_file_size(self, size, max_size, should_fail):
        if should_fail:
            with pytest.raises(InvalidInputError):
                validate_remote_file_size(size, max_size)
        else:
            validate_remote_file_size(size, max_size)

    @pytest.mark.parametrize("content,filename,expected", [
        (b"", "test.txt", "application/octet-stream"),
        (b"\x89PNG\r\n\x1a\n", "test.png", "image/png"),
        (b"\xff\xd8\xff", "test.jpg", "image/jpeg"),
        (b"GIF87a", "test.gif", "image/gif"),
        (b"%PDF", "test.pdf", "application/pdf"),
        (b"PK\x03\x04", "test.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        (b"PK\x03\x04", "test.zip", "application/zip"),
        (b"\xd0\xcf\x11\xe0", "test.doc", "application/msword"),
        (b"Hello world", "test.html", "text/html"),
        (b"Hello world", "test.txt", "text/plain"),
    ])
    def test_detect_file_content_type(self, content, filename, expected):
        result = detect_file_content_type(content, filename)
        assert result == expected

    def test_validate_conversion_options_valid(self):
        options = {
            "js_rendering": True,
            "timeout": 30,
            "extract_images": False,
            "unknown_option": "ignored"
        }
        allowed_keys = {"js_rendering", "timeout", "extract_images"}
        result = validate_conversion_options(options, allowed_keys)
        expected = {
            "js_rendering": True,
            "timeout": 30,
            "extract_images": False
        }
        assert result == expected

    @pytest.mark.parametrize("options,should_fail", [
        ({"js_rendering": "true"}, True),  # Should be bool
        ({"timeout": -5}, True),           # Should be positive
        ({"timeout": 0}, True),            # Should be positive
        ({"timeout": 30.5}, False),        # Float is OK
        ({"extract_images": False}, False), # Valid bool
    ])
    def test_validate_conversion_options_invalid(self, options, should_fail):
        allowed_keys = {"js_rendering", "timeout", "extract_images"}
        if should_fail:
            with pytest.raises(InvalidInputError):
                validate_conversion_options(options, allowed_keys)
        else:
            validate_conversion_options(options, allowed_keys)

    @pytest.mark.parametrize("filename,expected", [
        ("", "unknown"),
        ("test.txt", "test.txt"),
        ("path/to/file.txt", "file.txt"),  # Path components removed
        ("file with spaces.txt", "file_with_spaces.txt"),  # Spaces replaced
        ("file@#$%.txt", "file____.txt"),  # Special chars replaced
        (".hidden", "file_.hidden"),       # Leading dot fixed
        ("-dash", "file_-dash"),           # Leading dash fixed
        ("a" * 300 + ".txt", "a" * 250 + ".txt"),  # Long names truncated
    ])
    def test_sanitize_filename_for_api(self, filename, expected):
        result = sanitize_filename_for_api(filename)
        assert result == expected


class TestSecurityValidators:
    """Test security validation classes"""

    def test_url_validator_valid_urls(self):
        valid_urls = [
            "http://example.com",
            "https://example.com",
            "https://example.com/path",
            "http://sub.example.com:8080/path?query=value",
        ]
        for url in valid_urls:
            result = URLValidator.validate_url(url)
            assert result == url

    @pytest.mark.parametrize("invalid_url", [
        "not-a-url",
        "ftp://example.com",
        "file:///path/to/file",
        "://example.com",
        "http://",
        "",
    ])
    def test_url_validator_invalid_urls(self, invalid_url):
        with pytest.raises(ValueError):
            URLValidator.validate_url(invalid_url)

    def test_file_size_validator_within_limits(self):
        FileSizeValidator.validate_size(1024, "text/plain")  # Should not raise

    def test_file_size_validator_exceeds_limit(self):
        large_size = 100 * 1024 * 1024  # 100MB
        with pytest.raises(ValueError, match="exceeds limit"):
            FileSizeValidator.validate_size(large_size, "text/plain")

    def test_file_size_validator_zero_size(self):
        FileSizeValidator.validate_size(0, "text/plain")  # Should not raise

    @pytest.mark.parametrize("content,expected", [
        (b"%PDF-1.4", "application/pdf"),
        (b"PK\x03\x04", "application/zip"),
        (b"\x89PNG\r\n\x1a\n", "image/png"),
        (b"\xff\xd8\xff", "image/jpeg"),
        (b"Hello world", "text/plain"),  # UTF-8 text
        (b"\xff\xfe\x00\x00\x80\x81\x82", "application/octet-stream"),  # Binary data that fails UTF-8 decode
    ])
    def test_content_validator_detect_content_type(self, content, expected):
        result = ContentValidator.detect_content_type(content)
        assert result == expected

    def test_content_validator_validate_content_type_match(self):
        content = b"%PDF-1.4"
        declared = "application/pdf"
        result = ContentValidator.validate_content_type(content, declared)
        assert result == declared

    def test_content_validator_validate_content_type_mismatch(self):
        content = b"Hello world"  # Text content
        declared = "application/pdf"  # Security sensitive type
        with pytest.raises(ValueError, match="Content type mismatch"):
            ContentValidator.validate_content_type(content, declared)

    def test_content_validator_office_documents(self):
        content = b"PK\x03\x04"  # ZIP signature
        declared = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        result = ContentValidator.validate_content_type(content, declared)
        assert result == declared

    @pytest.mark.parametrize("mime_type,should_fail", [
        ("text/plain", False),
        ("application/json", False),
        ("", True),            # Empty
        ("text", True),        # No separator
        ("text/plain/extra", True),  # Multiple separators
        ("text/../plain", True),     # Invalid characters
        ("text\\plain", True),       # Backslash
        ("a" * 101, True),     # Too long
    ])
    def test_mime_type_validator(self, mime_type, should_fail):
        if should_fail:
            with pytest.raises(ValueError):
                MimeTypeValidator.validate_mime_type(mime_type)
        else:
            result = MimeTypeValidator.validate_mime_type(mime_type)
            assert result == mime_type.strip().lower()