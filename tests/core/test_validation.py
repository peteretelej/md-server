import pytest

from md_server.core.validation import (
    ValidationError,
    URLValidator,
    FileSizeValidator,
    ContentValidator,
    MimeTypeValidator,
)


class TestURLValidator:
    def test_validate_url_valid_http(self):
        url = "http://example.com"
        result = URLValidator.validate_url(url)
        assert result == url

    def test_validate_url_valid_https(self):
        url = "https://example.com"
        result = URLValidator.validate_url(url)
        assert result == url

    def test_validate_url_with_path(self):
        url = "https://example.com/path/to/resource"
        result = URLValidator.validate_url(url)
        assert result == url

    def test_validate_url_strips_whitespace(self):
        url = "  https://example.com  "
        result = URLValidator.validate_url(url)
        assert result == "https://example.com"

    def test_validate_url_empty_raises(self):
        with pytest.raises(ValidationError, match="URL cannot be empty"):
            URLValidator.validate_url("")

    def test_validate_url_whitespace_only_raises(self):
        with pytest.raises(ValidationError, match="URL cannot be empty"):
            URLValidator.validate_url("   ")

    def test_validate_url_none_raises(self):
        with pytest.raises(ValidationError, match="URL cannot be empty"):
            URLValidator.validate_url(None)

    def test_validate_url_invalid_scheme_raises(self):
        with pytest.raises(ValidationError, match="Only HTTP/HTTPS URLs allowed"):
            URLValidator.validate_url("ftp://example.com")

    def test_validate_url_no_scheme_raises(self):
        with pytest.raises(ValidationError, match="Invalid URL format"):
            URLValidator.validate_url("example.com")

    def test_validate_url_no_netloc_raises(self):
        with pytest.raises(ValidationError, match="Invalid URL format"):
            URLValidator.validate_url("https://")


class TestFileSizeValidator:
    def test_validate_size_under_limit(self):
        size_bytes = 1024 * 1024  # 1MB
        FileSizeValidator.validate_size(size_bytes, "text/plain")
        # Should not raise an exception

    def test_validate_size_at_default_limit(self):
        size_bytes = FileSizeValidator.DEFAULT_MAX_SIZE
        FileSizeValidator.validate_size(size_bytes, None)
        # Should not raise an exception

    def test_validate_size_over_limit_raises(self):
        size_bytes = FileSizeValidator.DEFAULT_MAX_SIZE + 1
        with pytest.raises(ValidationError, match="exceeds limit"):
            FileSizeValidator.validate_size(size_bytes, None)

    def test_validate_size_pdf_under_limit(self):
        size_bytes = 25 * 1024 * 1024  # 25MB
        FileSizeValidator.validate_size(size_bytes, "application/pdf")
        # Should not raise an exception

    def test_validate_size_pdf_over_limit_raises(self):
        size_bytes = 51 * 1024 * 1024  # 51MB
        with pytest.raises(ValidationError, match="exceeds limit"):
            FileSizeValidator.validate_size(size_bytes, "application/pdf")

    def test_validate_size_custom_limit(self):
        size_bytes = 2 * 1024 * 1024  # 2MB
        max_size_mb = 1  # 1MB limit

        with pytest.raises(ValidationError, match="exceeds limit"):
            FileSizeValidator.validate_size(size_bytes, "text/plain", max_size_mb)

    def test_validate_size_zero_or_negative(self):
        # Zero or negative size should be allowed (no validation)
        FileSizeValidator.validate_size(0, "text/plain")
        FileSizeValidator.validate_size(-1, "text/plain")


class TestContentValidator:
    def test_detect_content_type_pdf(self):
        pdf_bytes = b"%PDF-1.4"
        content_type = ContentValidator.detect_content_type(pdf_bytes)
        assert content_type == "application/pdf"

    def test_detect_content_type_html(self):
        html_bytes = b"<html><body>test</body></html>"
        content_type = ContentValidator.detect_content_type(html_bytes)
        assert content_type == "text/html"

    def test_detect_content_type_text(self):
        text_bytes = b"Plain text content"
        content_type = ContentValidator.detect_content_type(text_bytes)
        assert content_type == "text/plain"

    def test_detect_content_type_empty(self):
        empty_bytes = b""
        content_type = ContentValidator.detect_content_type(empty_bytes)
        assert content_type == "application/octet-stream"

    def test_detect_content_type_binary(self):
        binary_bytes = b"\x00\x01\x02\x03\xff"
        content_type = ContentValidator.detect_content_type(binary_bytes)
        assert content_type == "application/octet-stream"

    def test_validate_content_type_match(self):
        pdf_bytes = b"%PDF-1.4"
        result = ContentValidator.validate_content_type(pdf_bytes, "application/pdf")
        assert result == "application/pdf"

    def test_validate_content_type_office_document(self):
        zip_bytes = b"PK\x03\x04"
        declared_type = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        result = ContentValidator.validate_content_type(zip_bytes, declared_type)
        assert result == declared_type

    def test_validate_content_type_mismatch_raises(self):
        text_bytes = b"Plain text"
        with pytest.raises(ValidationError, match="Content type mismatch"):
            ContentValidator.validate_content_type(text_bytes, "application/pdf")


class TestMimeTypeValidator:
    def test_validate_mime_type_valid(self):
        result = MimeTypeValidator.validate_mime_type("text/html")
        assert result == "text/html"

    def test_validate_mime_type_valid_application(self):
        result = MimeTypeValidator.validate_mime_type("application/json")
        assert result == "application/json"

    def test_validate_mime_type_strips_case(self):
        result = MimeTypeValidator.validate_mime_type("TEXT/HTML")
        assert result == "text/html"

    def test_validate_mime_type_empty_raises(self):
        with pytest.raises(ValidationError, match="MIME type cannot be empty"):
            MimeTypeValidator.validate_mime_type("")

    def test_validate_mime_type_too_long_raises(self):
        long_mime = "a" * 101  # 101 characters
        with pytest.raises(ValidationError, match="MIME type too long"):
            MimeTypeValidator.validate_mime_type(long_mime)

    def test_validate_mime_type_no_separator_raises(self):
        with pytest.raises(ValidationError, match="must contain '/' separator"):
            MimeTypeValidator.validate_mime_type("texthtml")

    def test_validate_mime_type_multiple_separators_raises(self):
        with pytest.raises(ValidationError, match="exactly one '/' separator"):
            MimeTypeValidator.validate_mime_type("text/html/extra")

    def test_validate_mime_type_invalid_chars_raises(self):
        with pytest.raises(ValidationError, match="Invalid characters"):
            MimeTypeValidator.validate_mime_type("text/../html")


class TestValidationError:
    def test_validation_error_basic(self):
        error = ValidationError("Test error")
        assert str(error) == "Test error"
        assert error.details == {}

    def test_validation_error_with_details(self):
        details = {"field": "url", "value": "invalid"}
        error = ValidationError("Test error", details)
        assert str(error) == "Test error"
        assert error.details == details
