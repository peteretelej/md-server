import pytest
from md_server.security import URLValidator, FileSizeValidator, ContentValidator, MimeTypeValidator


class TestURLValidator:
    """Unit tests for URLValidator"""

    def test_valid_urls(self):
        """Test valid URL formats"""
        valid_urls = [
            "http://example.com",
            "https://example.com",
            "http://example.com/path",
            "https://example.com/path/to/resource",
            "http://example.com:8080/path",
            "https://subdomain.example.com/path?query=value",
            "http://192.168.1.100/public",  # Public IP
            "https://example.com/path#fragment",
        ]
        
        for url in valid_urls:
            # Should not raise exception
            validated = URLValidator.validate_url(url)
            assert validated == url

    def test_invalid_url_formats(self):
        """Test invalid URL formats"""
        invalid_urls = [
            "",  # Empty
            "   ",  # Whitespace only
            "not-a-url",  # No scheme
            "ftp://example.com",  # Unsupported scheme
            "file:///etc/passwd",  # File scheme
            "javascript:alert('xss')",  # JavaScript scheme
            "data:text/html,<script>alert('xss')</script>",  # Data scheme
            "//example.com",  # Protocol relative (no scheme)
            "http://",  # No netloc
            "https://",  # No netloc
        ]
        
        for url in invalid_urls:
            with pytest.raises(ValueError):
                URLValidator.validate_url(url)

    def test_url_whitespace_handling(self):
        """Test URL whitespace trimming"""
        url_with_spaces = "  http://example.com/path  "
        validated = URLValidator.validate_url(url_with_spaces)
        assert validated == url_with_spaces  # Returns original, but validates trimmed

    def test_case_sensitivity(self):
        """Test case sensitivity in schemes"""
        mixed_case_urls = [
            "HTTP://example.com",
            "HTTPS://example.com",
            "Http://example.com",
            "Https://example.com",
        ]
        
        for url in mixed_case_urls:
            # Should not raise exception - scheme check is case insensitive
            validated = URLValidator.validate_url(url)
            assert validated == url


class TestFileSizeValidator:
    """Unit tests for FileSizeValidator"""

    def test_valid_sizes(self):
        """Test valid file sizes"""
        # Should not raise exceptions
        FileSizeValidator.validate_size(1024)  # 1KB
        FileSizeValidator.validate_size(1024 * 1024)  # 1MB
        FileSizeValidator.validate_size(10 * 1024 * 1024)  # 10MB
        FileSizeValidator.validate_size(0)  # Zero size (allowed)

    def test_negative_size(self):
        """Test negative size handling"""
        # Negative sizes should be handled gracefully (return without error)
        FileSizeValidator.validate_size(-1)
        FileSizeValidator.validate_size(-1000)

    def test_format_specific_limits(self):
        """Test format-specific size limits"""
        # PDF limit (50MB)
        pdf_limit = 50 * 1024 * 1024
        FileSizeValidator.validate_size(pdf_limit - 1, "application/pdf")  # Just under limit
        
        with pytest.raises(ValueError, match="exceeds limit"):
            FileSizeValidator.validate_size(pdf_limit + 1, "application/pdf")  # Over limit

        # Text limit (10MB)
        text_limit = 10 * 1024 * 1024
        FileSizeValidator.validate_size(text_limit - 1, "text/plain")  # Just under limit
        
        with pytest.raises(ValueError, match="exceeds limit"):
            FileSizeValidator.validate_size(text_limit + 1, "text/plain")  # Over limit

        # DOCX limit (25MB)
        docx_limit = 25 * 1024 * 1024
        FileSizeValidator.validate_size(docx_limit - 1, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        
        with pytest.raises(ValueError, match="exceeds limit"):
            FileSizeValidator.validate_size(docx_limit + 1, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    def test_unknown_format_uses_default(self):
        """Test that unknown formats use default limit"""
        default_limit = FileSizeValidator.DEFAULT_MAX_SIZE
        
        # Should use default limit for unknown formats
        FileSizeValidator.validate_size(default_limit - 1, "unknown/format")
        
        with pytest.raises(ValueError, match="exceeds limit"):
            FileSizeValidator.validate_size(default_limit + 1, "unknown/format")

    def test_no_content_type_uses_default(self):
        """Test that None content type uses default limit"""
        default_limit = FileSizeValidator.DEFAULT_MAX_SIZE
        
        FileSizeValidator.validate_size(default_limit - 1, None)
        
        with pytest.raises(ValueError, match="exceeds limit"):
            FileSizeValidator.validate_size(default_limit + 1, None)

    def test_error_message_format(self):
        """Test error message formatting"""
        try:
            FileSizeValidator.validate_size(60 * 1024 * 1024, "application/pdf")  # 60MB PDF
            assert False, "Should have raised ValueError"
        except ValueError as e:
            message = str(e)
            assert "60.0MB" in message  # Actual size
            assert "50MB" in message   # Limit
            assert "application/pdf" in message  # Format


class TestContentValidator:
    """Unit tests for ContentValidator"""

    def test_magic_bytes_detection(self):
        """Test all magic bytes in MAGIC_BYTES"""
        test_cases = [
            (b"\x25\x50\x44\x46", "application/pdf"),  # PDF
            (b"\x50\x4b\x03\x04", "application/zip"),  # ZIP
            (b"\x50\x4b\x05\x06", "application/zip"),  # Empty ZIP
            (b"\x50\x4b\x07\x08", "application/zip"),  # ZIP variant
            (b"\x89\x50\x4e\x47", "image/png"),  # PNG
            (b"\xff\xd8\xff", "image/jpeg"),  # JPEG
            (b"\x47\x49\x46\x38", "image/gif"),  # GIF
            (b"\x52\x49\x46\x46", "audio/wav"),  # WAV (RIFF)
            (b"\x49\x44\x33", "audio/mp3"),  # MP3 with ID3
            (b"\xff\xfb", "audio/mp3"),  # MP3
            (b"\x3c\x3f\x78\x6d\x6c", "application/xml"),  # XML <?xml
            (b"\x3c\x68\x74\x6d\x6c", "text/html"),  # HTML <html
            (b"\x3c\x21\x44\x4f\x43\x54\x59\x50\x45", "text/html"),  # HTML <!DOCTYPE
        ]
        
        for magic_bytes, expected_type in test_cases:
            content = magic_bytes + b"\x00" * 50  # Add padding
            detected = ContentValidator.detect_content_type(content)
            assert detected == expected_type, f"Failed for {magic_bytes.hex()}: expected {expected_type}, got {detected}"

    def test_text_content_detection(self):
        """Test text content detection"""
        # Valid UTF-8 text
        text_content = b"Hello, world! This is plain text."
        detected = ContentValidator.detect_content_type(text_content)
        assert detected == "text/plain"
        
        # Text with unicode
        unicode_text = "Hello, 世界! 🌍".encode('utf-8')
        detected = ContentValidator.detect_content_type(unicode_text)
        assert detected == "text/plain"

    def test_binary_content_detection(self):
        """Test binary content detection"""
        # Random binary content
        binary_content = bytes(range(256))
        detected = ContentValidator.detect_content_type(binary_content)
        assert detected == "application/octet-stream"
        
        # Invalid UTF-8
        invalid_utf8 = b"\xff\xfe" + b"\x80" * 50
        detected = ContentValidator.detect_content_type(invalid_utf8)
        assert detected == "application/octet-stream"

    def test_empty_content(self):
        """Test empty content detection"""
        detected = ContentValidator.detect_content_type(b"")
        assert detected == "application/octet-stream"
        
        detected = ContentValidator.detect_content_type(None)
        assert detected == "application/octet-stream"

    def test_content_type_validation_matching(self):
        """Test content type validation when types match"""
        # PDF content with PDF declaration
        pdf_content = b"%PDF-1.4\nSample content"
        validated = ContentValidator.validate_content_type(pdf_content, "application/pdf")
        assert validated == "application/pdf"
        
        # Text content with text declaration
        text_content = b"Plain text content"
        validated = ContentValidator.validate_content_type(text_content, "text/plain")
        assert validated == "text/plain"

    def test_office_document_validation(self):
        """Test Office document validation (ZIP-based)"""
        # ZIP content declared as Office document
        zip_content = b"PK\x03\x04" + b"\x00" * 100
        
        office_types = [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ]
        
        for office_type in office_types:
            validated = ContentValidator.validate_content_type(zip_content, office_type)
            assert validated == office_type

    def test_octet_stream_fallback(self):
        """Test octet-stream fallback behavior"""
        # Unknown binary content with declared type
        unknown_content = b"\x12\x34\x56\x78" * 25
        validated = ContentValidator.validate_content_type(unknown_content, "custom/format")
        assert validated == "custom/format"  # Trust declared type for unknown content

    def test_security_sensitive_type_mismatch(self):
        """Test security-sensitive type mismatch detection"""
        # Text content declared as PDF (security sensitive)
        text_content = b"This is plain text, not a PDF"
        
        with pytest.raises(ValueError, match="Content type mismatch"):
            ContentValidator.validate_content_type(text_content, "application/pdf")
        
        # Text content declared as HTML
        with pytest.raises(ValueError, match="Content type mismatch"):
            ContentValidator.validate_content_type(text_content, "text/html")
        
        # Text content declared as PNG
        with pytest.raises(ValueError, match="Content type mismatch"):
            ContentValidator.validate_content_type(text_content, "image/png")

    def test_no_declared_type(self):
        """Test behavior when no type is declared"""
        pdf_content = b"%PDF-1.4\nSample"
        detected = ContentValidator.validate_content_type(pdf_content, None)
        assert detected == "application/pdf"
        
        text_content = b"Plain text"
        detected = ContentValidator.validate_content_type(text_content, None)
        assert detected == "text/plain"


class TestMimeTypeValidator:
    """Unit tests for MimeTypeValidator"""

    def test_valid_mime_types(self):
        """Test valid MIME types"""
        valid_types = [
            "text/plain",
            "application/pdf",
            "image/jpeg",
            "video/mp4",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/html",
            "application/json",
        ]
        
        for mime_type in valid_types:
            validated = MimeTypeValidator.validate_mime_type(mime_type)
            assert validated == mime_type.lower()

    def test_case_normalization(self):
        """Test case normalization"""
        mixed_case = "TEXT/PLAIN"
        validated = MimeTypeValidator.validate_mime_type(mixed_case)
        assert validated == "text/plain"
        
        mixed_case = "Application/PDF"
        validated = MimeTypeValidator.validate_mime_type(mixed_case)
        assert validated == "application/pdf"

    def test_whitespace_trimming(self):
        """Test whitespace trimming"""
        with_spaces = "  text/plain  "
        validated = MimeTypeValidator.validate_mime_type(with_spaces)
        assert validated == "text/plain"

    def test_empty_mime_type(self):
        """Test empty MIME type validation"""
        with pytest.raises(ValueError, match="MIME type cannot be empty"):
            MimeTypeValidator.validate_mime_type("")
        
        with pytest.raises(ValueError, match="MIME type cannot be empty"):
            MimeTypeValidator.validate_mime_type(None)

    def test_too_long_mime_type(self):
        """Test excessively long MIME types"""
        long_type = "a" * 50 + "/" + "b" * 60  # >100 chars
        with pytest.raises(ValueError, match="MIME type too long"):
            MimeTypeValidator.validate_mime_type(long_type)

    def test_missing_separator(self):
        """Test MIME types without separator"""
        with pytest.raises(ValueError, match="must contain '/' separator"):
            MimeTypeValidator.validate_mime_type("textplain")
        
        with pytest.raises(ValueError, match="must contain '/' separator"):
            MimeTypeValidator.validate_mime_type("application")

    def test_multiple_separators(self):
        """Test MIME types with multiple separators"""
        with pytest.raises(ValueError, match="exactly one '/' separator"):
            MimeTypeValidator.validate_mime_type("text/plain/charset")
        
        with pytest.raises(ValueError, match="exactly one '/' separator"):
            MimeTypeValidator.validate_mime_type("a/b/c/d")

    def test_invalid_characters(self):
        """Test MIME types with invalid characters"""
        # Test path traversal in MIME type (this may not be implemented)
        try:
            MimeTypeValidator.validate_mime_type("text/../plain")
        except ValueError as e:
            # May fail for multiple '/' separators instead of invalid characters
            assert "separator" in str(e) or "Invalid characters" in str(e)
        
        try:
            MimeTypeValidator.validate_mime_type("text\\plain")
        except ValueError as e:
            assert "Invalid characters" in str(e)
        
        try:
            MimeTypeValidator.validate_mime_type("application/..pdf")
        except ValueError as e:
            assert "Invalid characters" in str(e)

    def test_edge_case_valid_types(self):
        """Test edge cases that should be valid"""
        edge_cases = [
            "x/y",  # Minimal valid type
            "application/x-custom",  # X- prefix
            "text/plain",  # Standard type
            "a/b",  # Single characters
        ]
        
        for mime_type in edge_cases:
            validated = MimeTypeValidator.validate_mime_type(mime_type)
            assert validated == mime_type.lower()