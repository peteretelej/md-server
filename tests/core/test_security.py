import pytest

from src.md_server.core.validation import (
    URLValidator,
    FileSizeValidator,
    ValidationError,
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

    def test_validate_url_with_query(self):
        url = "https://example.com/path?param=value"
        result = URLValidator.validate_url(url)
        assert result == url

    def test_validate_url_strips_whitespace(self):
        url = "  https://example.com  "
        result = URLValidator.validate_url(url)
        assert result == url.strip()

    def test_validate_url_invalid_no_scheme(self):
        with pytest.raises(ValidationError, match="Invalid URL format"):
            URLValidator.validate_url("example.com")

    def test_validate_url_invalid_no_netloc(self):
        with pytest.raises(ValidationError, match="Invalid URL format"):
            URLValidator.validate_url("https://")

    def test_validate_url_invalid_scheme_ftp(self):
        with pytest.raises(ValidationError, match="Only HTTP/HTTPS URLs allowed"):
            URLValidator.validate_url("ftp://example.com")

    def test_validate_url_invalid_scheme_file(self):
        with pytest.raises(ValidationError, match="Only HTTP/HTTPS URLs allowed"):
            URLValidator.validate_url("file:///path/to/file")

    def test_validate_url_empty_string(self):
        with pytest.raises(ValidationError, match="URL cannot be empty"):
            URLValidator.validate_url("")


class TestFileSizeValidator:
    def test_validate_size_under_limit(self):
        size_bytes = 1024 * 1024  # 1MB
        content_type = "text/plain"
        # Should not raise exception
        FileSizeValidator.validate_size(size_bytes, content_type)

    def test_validate_size_at_limit(self):
        size_bytes = 10 * 1024 * 1024  # 10MB - limit for text/plain
        content_type = "text/plain"
        # Should not raise exception
        FileSizeValidator.validate_size(size_bytes, content_type)

    def test_validate_size_over_limit(self):
        size_bytes = 11 * 1024 * 1024  # 11MB - over limit for text/plain
        content_type = "text/plain"
        with pytest.raises(ValidationError, match="File size.*exceeds limit"):
            FileSizeValidator.validate_size(size_bytes, content_type)

    def test_validate_size_pdf_under_limit(self):
        size_bytes = 25 * 1024 * 1024  # 25MB
        content_type = "application/pdf"
        # Should not raise exception
        FileSizeValidator.validate_size(size_bytes, content_type)

    def test_validate_size_pdf_over_limit(self):
        size_bytes = 51 * 1024 * 1024  # 51MB
        content_type = "application/pdf"
        with pytest.raises(ValidationError, match="File size.*exceeds limit"):
            FileSizeValidator.validate_size(size_bytes, content_type)

    def test_validate_size_docx_under_limit(self):
        size_bytes = 20 * 1024 * 1024  # 20MB
        content_type = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        # Should not raise exception
        FileSizeValidator.validate_size(size_bytes, content_type)

    def test_validate_size_docx_over_limit(self):
        size_bytes = 26 * 1024 * 1024  # 26MB
        content_type = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        with pytest.raises(ValidationError, match="File size.*exceeds limit"):
            FileSizeValidator.validate_size(size_bytes, content_type)

    def test_validate_size_zero_bytes(self):
        # Zero size should not raise exception
        FileSizeValidator.validate_size(0, "text/plain")

    def test_validate_size_with_custom_limit(self):
        size_bytes = 2 * 1024 * 1024  # 2MB
        # Should not raise with 5MB custom limit
        FileSizeValidator.validate_size(size_bytes, "text/plain", max_size_mb=5)

        # Should raise with 1MB custom limit
        with pytest.raises(ValidationError):
            FileSizeValidator.validate_size(size_bytes, "text/plain", max_size_mb=1)
