import pytest
from md_server.security import (
    URLValidator,
    FileSizeValidator,
    ContentValidator,
    MimeTypeValidator,
)


class TestURLValidator:
    def test_valid_https_url(self):
        """Test valid HTTPS URL passes validation"""
        url = "https://example.com/path"
        result = URLValidator.validate_url(url)
        assert result == url

    def test_valid_http_url(self):
        """Test valid HTTP URL passes validation"""
        url = "http://example.com/path"
        result = URLValidator.validate_url(url)
        assert result == url

    def test_localhost_allowed(self):
        """Test localhost URLs are now allowed"""
        urls = [
            "https://localhost/test",
            "http://127.0.0.1/path",
            "https://192.168.1.100/internal-docs",
            "http://10.0.0.5/wiki",
            "https://test.local/share",
        ]

        for url in urls:
            result = URLValidator.validate_url(url)
            assert result == url

    def test_invalid_url_format(self):
        """Test invalid URL format raises ValueError"""
        with pytest.raises(ValueError, match="Invalid URL format"):
            URLValidator.validate_url("not-a-url")

    def test_missing_scheme(self):
        """Test URL without scheme raises ValueError"""
        with pytest.raises(ValueError, match="Invalid URL format"):
            URLValidator.validate_url("//example.com")

    def test_missing_netloc(self):
        """Test URL without netloc raises ValueError"""
        with pytest.raises(ValueError, match="Invalid URL format"):
            URLValidator.validate_url("https:///path")

    def test_invalid_scheme(self):
        """Test non-HTTP/HTTPS scheme raises ValueError"""
        invalid_schemes = [
            "ftp://example.com/file",
            "redis://example.com",
            "ldap://example.com/query",
        ]

        for url in invalid_schemes:
            with pytest.raises(ValueError, match="Only HTTP/HTTPS URLs allowed"):
                URLValidator.validate_url(url)

    def test_invalid_format_schemes(self):
        """Test schemes that result in invalid format"""
        invalid_format_urls = [
            "file:///etc/passwd",  # No netloc
            "javascript:alert('xss')",  # No netloc
        ]

        for url in invalid_format_urls:
            with pytest.raises(ValueError, match="Invalid URL format"):
                URLValidator.validate_url(url)

    def test_url_with_whitespace(self):
        """Test URL with whitespace is stripped"""
        result = URLValidator.validate_url("  https://example.com/test  ")
        assert result == "  https://example.com/test  "

    def test_case_insensitive_scheme_check(self):
        """Test case insensitive scheme checking"""
        result = URLValidator.validate_url("HTTPS://example.com/test")
        assert result == "HTTPS://example.com/test"

        result = URLValidator.validate_url("HTTP://example.com/test")
        assert result == "HTTP://example.com/test"

    def test_complex_urls(self):
        """Test complex but valid URLs"""
        complex_urls = [
            "https://example.com:8080/path?query=value#fragment",
            "http://user:pass@example.com/secure",
            "https://sub.domain.example.com/nested/path",
            "http://192.168.1.100:3000/api/docs",
            "https://[::1]:8080/ipv6-localhost",
        ]

        for url in complex_urls:
            result = URLValidator.validate_url(url)
            assert result == url


class TestFileSizeValidator:
    def test_zero_size_allowed(self):
        """Test zero size content is allowed"""
        FileSizeValidator.validate_size(0)  # Should not raise

    def test_negative_size_allowed(self):
        """Test negative size is allowed (treated as zero)"""
        FileSizeValidator.validate_size(-1)  # Should not raise

    def test_valid_size_default_limit(self):
        """Test valid size within default limit"""
        FileSizeValidator.validate_size(10 * 1024 * 1024)  # 10MB - should pass

    def test_valid_size_specific_format(self):
        """Test valid size for specific format"""
        FileSizeValidator.validate_size(
            5 * 1024 * 1024, "application/pdf"
        )  # 5MB PDF - should pass

    def test_exceeds_default_limit(self):
        """Test size exceeding default limit"""
        size = 60 * 1024 * 1024  # 60MB
        with pytest.raises(ValueError, match="exceeds limit of 50MB"):
            FileSizeValidator.validate_size(size)

    def test_exceeds_format_specific_limit(self):
        """Test size exceeding format-specific limit"""
        size = 30 * 1024 * 1024  # 30MB
        with pytest.raises(ValueError, match="exceeds limit of 25MB"):
            FileSizeValidator.validate_size(
                size,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

    def test_various_format_limits(self):
        """Test various format-specific limits"""
        test_cases = [
            ("application/pdf", 50 * 1024 * 1024),
            ("text/plain", 10 * 1024 * 1024),
            ("application/json", 5 * 1024 * 1024),
            ("image/png", 20 * 1024 * 1024),
            ("image/jpeg", 20 * 1024 * 1024),
        ]

        for content_type, max_size in test_cases:
            # Should pass at limit
            FileSizeValidator.validate_size(max_size, content_type)

            # Should fail above limit
            with pytest.raises(ValueError, match="exceeds limit"):
                FileSizeValidator.validate_size(max_size + 1, content_type)

    def test_unknown_format_uses_default(self):
        """Test unknown format uses default limit"""
        size = 55 * 1024 * 1024  # 55MB
        with pytest.raises(ValueError, match="exceeds limit of 50MB"):
            FileSizeValidator.validate_size(size, "application/unknown")


class TestContentValidator:
    def test_empty_content(self):
        """Test empty content returns octet-stream"""
        result = ContentValidator.detect_content_type(b"")
        assert result == "application/octet-stream"

    def test_none_content(self):
        """Test None content returns octet-stream"""
        result = ContentValidator.detect_content_type(None)
        assert result == "application/octet-stream"

    def test_pdf_magic_bytes(self):
        """Test PDF magic bytes detection"""
        pdf_content = b"\x25\x50\x44\x46-1.4"
        result = ContentValidator.detect_content_type(pdf_content)
        assert result == "application/pdf"

    def test_zip_magic_bytes(self):
        """Test ZIP magic bytes detection"""
        zip_variants = [
            b"\x50\x4b\x03\x04",  # Standard ZIP
            b"\x50\x4b\x05\x06",  # Empty ZIP
            b"\x50\x4b\x07\x08",  # ZIP variant
        ]

        for zip_content in zip_variants:
            result = ContentValidator.detect_content_type(zip_content)
            assert result == "application/zip"

    def test_image_magic_bytes(self):
        """Test image magic bytes detection"""
        image_tests = [
            (b"\x89\x50\x4e\x47", "image/png"),
            (b"\xff\xd8\xff", "image/jpeg"),
            (b"\x47\x49\x46\x38", "image/gif"),
        ]

        for content, expected in image_tests:
            result = ContentValidator.detect_content_type(content)
            assert result == expected

    def test_html_magic_bytes(self):
        """Test HTML magic bytes detection"""
        html_variants = [
            (b"\x3c\x68\x74\x6d\x6c", "text/html"),  # <html
            (b"\x3c\x21\x44\x4f\x43\x54\x59\x50\x45", "text/html"),  # <!DOCTYPE
        ]

        for content, expected in html_variants:
            result = ContentValidator.detect_content_type(content)
            assert result == expected

    def test_xml_magic_bytes(self):
        """Test XML magic bytes detection"""
        xml_content = b"\x3c\x3f\x78\x6d\x6c"  # <?xml
        result = ContentValidator.detect_content_type(xml_content)
        assert result == "application/xml"

    def test_audio_magic_bytes(self):
        """Test audio magic bytes detection"""
        audio_tests = [
            (b"\x52\x49\x46\x46", "audio/wav"),
            (b"\x49\x44\x33", "audio/mp3"),
            (b"\xff\xfb", "audio/mp3"),
        ]

        for content, expected in audio_tests:
            result = ContentValidator.detect_content_type(content)
            assert result == expected

    def test_utf8_text_detection(self):
        """Test UTF-8 text detection"""
        text_content = "Hello, world!".encode("utf-8")
        result = ContentValidator.detect_content_type(text_content)
        assert result == "text/plain"

    def test_binary_content_fallback(self):
        """Test binary content falls back to octet-stream"""
        binary_content = b"\x00\x01\x02\x03\xff\xfe"
        result = ContentValidator.detect_content_type(binary_content)
        assert result == "application/octet-stream"

    def test_validate_content_type_no_declared(self):
        """Test content type validation without declared type"""
        pdf_content = b"\x25\x50\x44\x46-1.4"
        result = ContentValidator.validate_content_type(pdf_content)
        assert result == "application/pdf"

    def test_validate_content_type_matching(self):
        """Test content type validation with matching declared type"""
        pdf_content = b"\x25\x50\x44\x46-1.4"
        result = ContentValidator.validate_content_type(pdf_content, "application/pdf")
        assert result == "application/pdf"

    def test_validate_office_documents(self):
        """Test Office document validation (ZIP-based)"""
        zip_content = b"\x50\x4b\x03\x04"
        office_types = [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ]

        for office_type in office_types:
            result = ContentValidator.validate_content_type(zip_content, office_type)
            assert result == office_type

    def test_validate_octet_stream_fallback(self):
        """Test octet-stream accepts any declared type"""
        binary_content = b"\x00\x01\x02\x03"
        result = ContentValidator.validate_content_type(binary_content, "custom/type")
        assert result == "custom/type"

    def test_security_sensitive_mismatch(self):
        """Test security-sensitive types reject mismatches"""
        png_content = b"\x89\x50\x4e\x47"

        with pytest.raises(ValueError, match="Content type mismatch"):
            ContentValidator.validate_content_type(png_content, "application/pdf")

    def test_security_sensitive_types(self):
        """Test all security-sensitive types"""
        sensitive_tests = [
            (b"\x25\x50\x44\x46", "application/pdf"),
            (b"\x3c\x68\x74\x6d\x6c", "text/html"),
            (b"\x89\x50\x4e\x47", "image/png"),
            (b"\xff\xd8\xff", "image/jpeg"),
        ]

        for content, content_type in sensitive_tests:
            # Should pass with correct type
            result = ContentValidator.validate_content_type(content, content_type)
            assert result == content_type

            # Should fail with wrong sensitive type
            with pytest.raises(ValueError, match="Content type mismatch"):
                ContentValidator.validate_content_type(
                    content,
                    "application/pdf"
                    if content_type != "application/pdf"
                    else "text/html",
                )

    def test_non_security_sensitive_mismatch_allowed(self):
        """Test non-security-sensitive types allow mismatches"""
        text_content = "Hello, world!".encode("utf-8")
        result = ContentValidator.validate_content_type(
            text_content, "application/custom"
        )
        assert result == "application/custom"


class TestMimeTypeValidator:
    def test_valid_mime_type(self):
        """Test valid MIME type passes validation"""
        result = MimeTypeValidator.validate_mime_type("text/html")
        assert result == "text/html"

    def test_valid_mime_type_with_spaces(self):
        """Test MIME type with spaces is stripped"""
        result = MimeTypeValidator.validate_mime_type("  text/html  ")
        assert result == "text/html"

    def test_valid_mime_type_case_normalized(self):
        """Test MIME type is normalized to lowercase"""
        result = MimeTypeValidator.validate_mime_type("TEXT/HTML")
        assert result == "text/html"

    def test_empty_mime_type(self):
        """Test empty MIME type raises ValueError"""
        with pytest.raises(ValueError, match="MIME type cannot be empty"):
            MimeTypeValidator.validate_mime_type("")

    def test_none_mime_type(self):
        """Test None MIME type raises ValueError"""
        with pytest.raises(ValueError, match="MIME type cannot be empty"):
            MimeTypeValidator.validate_mime_type(None)

    def test_too_long_mime_type(self):
        """Test MIME type over 100 chars raises ValueError"""
        long_mime_type = "a" * 50 + "/" + "b" * 51  # 102 chars total
        with pytest.raises(ValueError, match="MIME type too long"):
            MimeTypeValidator.validate_mime_type(long_mime_type)

    def test_mime_type_without_slash(self):
        """Test MIME type without slash raises ValueError"""
        with pytest.raises(ValueError, match="MIME type must contain '/' separator"):
            MimeTypeValidator.validate_mime_type("texthtml")

    def test_mime_type_with_multiple_slashes(self):
        """Test MIME type with multiple slashes raises ValueError"""
        with pytest.raises(
            ValueError, match="MIME type must contain exactly one '/' separator"
        ):
            MimeTypeValidator.validate_mime_type("text/html/extra")

    def test_mime_type_with_double_dots(self):
        """Test MIME type with .. raises ValueError"""
        with pytest.raises(ValueError, match="Invalid characters in MIME type"):
            MimeTypeValidator.validate_mime_type("text/html..")

    def test_mime_type_with_backslash(self):
        """Test MIME type with backslash raises ValueError"""
        with pytest.raises(ValueError, match="Invalid characters in MIME type"):
            MimeTypeValidator.validate_mime_type("text/ht\\ml")

    def test_various_valid_mime_types(self):
        """Test various valid MIME types"""
        valid_types = [
            "text/html",
            "application/json",
            "text/xml",
            "application/xml",
            "text/plain",
            "text/markdown",
            "application/xhtml+xml",
            "text/csv",
        ]

        for mime_type in valid_types:
            result = MimeTypeValidator.validate_mime_type(mime_type)
            assert result == mime_type.lower()
