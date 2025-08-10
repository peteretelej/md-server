import base64
from md_server.detection import ContentTypeDetector


class TestContentTypeDetector:
    def test_detect_from_content_type_header_valid(self):
        """Test content type detection from valid header"""
        result = ContentTypeDetector.detect_from_content_type_header("application/pdf")
        assert result == "application/pdf"

    def test_detect_from_content_type_header_with_charset(self):
        """Test content type detection with charset parameter"""
        result = ContentTypeDetector.detect_from_content_type_header(
            "text/html; charset=utf-8"
        )
        assert result == "text/html"

    def test_detect_from_content_type_header_with_whitespace(self):
        """Test content type detection with whitespace"""
        result = ContentTypeDetector.detect_from_content_type_header(
            "  application/json  ; charset=utf-8"
        )
        assert result == "application/json"

    def test_detect_from_content_type_header_none(self):
        """Test content type detection with None input"""
        result = ContentTypeDetector.detect_from_content_type_header(None)
        assert result is None

    def test_detect_from_content_type_header_empty(self):
        """Test content type detection with empty string"""
        result = ContentTypeDetector.detect_from_content_type_header("")
        assert result is None

    def test_detect_from_content_type_header_semicolon_only(self):
        """Test content type detection with semicolon only"""
        result = ContentTypeDetector.detect_from_content_type_header(";charset=utf-8")
        assert result is None

    def test_detect_from_filename_valid(self):
        """Test filename detection with valid extensions"""
        test_cases = [
            ("document.pdf", "application/pdf"),
            (
                "document.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
            ("image.png", "image/png"),
            ("data.json", "application/json"),
            ("page.html", "text/html"),
        ]

        for filename, expected in test_cases:
            result = ContentTypeDetector.detect_from_filename(filename)
            assert result == expected

    def test_detect_from_filename_none(self):
        """Test filename detection with None input"""
        result = ContentTypeDetector.detect_from_filename(None)
        assert result is None

    def test_detect_from_filename_empty(self):
        """Test filename detection with empty string"""
        result = ContentTypeDetector.detect_from_filename("")
        assert result is None

    def test_detect_from_filename_unknown_extension(self):
        """Test filename detection with unknown extension"""
        result = ContentTypeDetector.detect_from_filename("file.unknown123")
        assert result is None

    def test_detect_from_filename_no_extension(self):
        """Test filename detection with no extension"""
        result = ContentTypeDetector.detect_from_filename("README")
        assert result is None

    def test_detect_from_magic_bytes_pdf(self):
        """Test magic bytes detection for PDF"""
        pdf_content = b"%PDF-1.4"
        result = ContentTypeDetector.detect_from_magic_bytes(pdf_content)
        assert result == "application/pdf"

    def test_detect_from_magic_bytes_zip(self):
        """Test magic bytes detection for ZIP"""
        zip_content = b"PK\x03\x04"
        result = ContentTypeDetector.detect_from_magic_bytes(zip_content)
        assert result == "application/zip"

    def test_detect_from_magic_bytes_images(self):
        """Test magic bytes detection for images"""
        test_cases = [
            (b"\x89PNG\r\n\x1a\n", "image/png"),
            (b"\xff\xd8\xff", "image/jpeg"),
            (b"GIF87a", "image/gif"),
            (b"GIF89a", "image/gif"),
        ]

        for content, expected in test_cases:
            result = ContentTypeDetector.detect_from_magic_bytes(content)
            assert result == expected

    def test_detect_from_magic_bytes_audio_video(self):
        """Test magic bytes detection for audio/video"""
        test_cases = [
            (b"RIFF", "audio/wav"),
            (b"ID3", "audio/mpeg"),
            (b"\x00\x00\x00 ftypmp4", "video/mp4"),
        ]

        for content, expected in test_cases:
            result = ContentTypeDetector.detect_from_magic_bytes(content)
            assert result == expected

    def test_detect_from_magic_bytes_markup(self):
        """Test magic bytes detection for markup"""
        test_cases = [
            (b"<html>", "text/html"),
            (b"<!DOCTYPE html>", "text/html"),
            (b"<?xml version='1.0'?>", "text/xml"),
        ]

        for content, expected in test_cases:
            result = ContentTypeDetector.detect_from_magic_bytes(content)
            assert result == expected

    def test_detect_from_magic_bytes_json(self):
        """Test magic bytes detection for JSON"""
        test_cases = [
            (b'{"key": "value"}', "application/json"),
            (b'[{"item": 1}]', "application/json"),
        ]

        for content, expected in test_cases:
            result = ContentTypeDetector.detect_from_magic_bytes(content)
            assert result == expected

    def test_detect_from_magic_bytes_empty(self):
        """Test magic bytes detection with empty content"""
        result = ContentTypeDetector.detect_from_magic_bytes(b"")
        assert result == "text/plain"

    def test_detect_from_magic_bytes_none(self):
        """Test magic bytes detection with None content"""
        result = ContentTypeDetector.detect_from_magic_bytes(None)
        assert result == "text/plain"

    def test_detect_from_magic_bytes_html_in_header(self):
        """Test HTML detection anywhere in first 512 bytes"""
        html_content = b"Some preamble\n<html>\n<head><title>Test</title></head>\n"
        result = ContentTypeDetector.detect_from_magic_bytes(html_content)
        assert result == "text/html"

    def test_detect_from_magic_bytes_doctype_in_header(self):
        """Test DOCTYPE detection anywhere in first 512 bytes"""
        doctype_content = b"  \n  <!doctype html>\n<html>"
        result = ContentTypeDetector.detect_from_magic_bytes(doctype_content)
        assert result == "text/html"

    def test_detect_from_magic_bytes_markdown(self):
        """Test markdown detection from content"""
        # Test markdown detection based on actual logic
        test_cases = [
            (b"# Heading 1", "text/markdown"),
            (b"## Heading 2", "text/markdown"),
            (b"* List item", "text/markdown"),
            (b"  # Heading with spaces", "text/markdown"),
            (b"  * List with spaces", "text/markdown"),
        ]

        for content, expected in test_cases:
            result = ContentTypeDetector.detect_from_magic_bytes(content)
            assert result == expected

    def test_detect_from_magic_bytes_plain_text(self):
        """Test plain text detection"""
        text_content = "Hello, world!".encode("utf-8")
        result = ContentTypeDetector.detect_from_magic_bytes(text_content)
        assert result == "text/plain"

    def test_detect_from_magic_bytes_unicode_decode_error(self):
        """Test handling of binary content that can't be decoded"""
        binary_content = b"\x00\x01\x02\x03\xff\xfe\xfd"
        result = ContentTypeDetector.detect_from_magic_bytes(binary_content)
        assert result is None

    def test_detect_office_format(self):
        """Test Office format detection (simplified)"""
        zip_content = b"PK\x03\x04"
        result = ContentTypeDetector._detect_office_format(zip_content)
        assert result == "application/zip"

    def test_detect_input_type_json_url(self):
        """Test input type detection for JSON URL request"""
        request_data = {"url": "https://example.com"}
        input_type, format_type = ContentTypeDetector.detect_input_type(
            request_data=request_data
        )

        assert input_type == "json_url"
        assert format_type == "text/url"

    def test_detect_input_type_json_content_with_base64(self):
        """Test input type detection for JSON content with valid base64"""
        pdf_content = b"%PDF-1.4"
        b64_content = base64.b64encode(pdf_content).decode("utf-8")
        request_data = {"content": b64_content}

        input_type, format_type = ContentTypeDetector.detect_input_type(
            request_data=request_data
        )

        assert input_type == "json_content"
        assert format_type == "application/pdf"

    def test_detect_input_type_json_content_invalid_base64(self):
        """Test input type detection for JSON content with invalid base64"""
        request_data = {"content": "invalid-base64!", "filename": "test.pdf"}

        input_type, format_type = ContentTypeDetector.detect_input_type(
            request_data=request_data
        )

        assert input_type == "json_content"
        assert format_type == "application/pdf"

    def test_detect_input_type_json_content_no_filename(self):
        """Test input type detection for JSON content without filename"""
        request_data = {"content": "invalid-base64!"}

        input_type, format_type = ContentTypeDetector.detect_input_type(
            request_data=request_data
        )

        assert input_type == "json_content"
        assert format_type == "application/octet-stream"

    def test_detect_input_type_json_text(self):
        """Test input type detection for JSON text request"""
        request_data = {"text": "Some plain text content"}

        input_type, format_type = ContentTypeDetector.detect_input_type(
            request_data=request_data
        )

        assert input_type == "json_text"
        assert format_type == "text/markdown"

    def test_detect_input_type_json_text_typed_html(self):
        """Test input type detection for JSON text with HTML MIME type"""
        request_data = {"text": "<h1>Hello World</h1>", "mime_type": "text/html"}

        input_type, format_type = ContentTypeDetector.detect_input_type(
            request_data=request_data
        )

        assert input_type == "json_text_typed"
        assert format_type == "text/html"

    def test_detect_input_type_json_text_typed_xml(self):
        """Test input type detection for JSON text with XML MIME type"""
        request_data = {"text": "<root><item>test</item></root>", "mime_type": "text/xml"}

        input_type, format_type = ContentTypeDetector.detect_input_type(
            request_data=request_data
        )

        assert input_type == "json_text_typed"
        assert format_type == "text/xml"

    def test_detect_input_type_json_text_typed_custom(self):
        """Test input type detection for JSON text with custom MIME type"""
        request_data = {"text": "custom content", "mime_type": "application/custom"}

        input_type, format_type = ContentTypeDetector.detect_input_type(
            request_data=request_data
        )

        assert input_type == "json_text_typed"
        assert format_type == "application/custom"

    def test_detect_input_type_multipart(self):
        """Test input type detection for multipart upload"""
        content = b"%PDF-1.4"
        filename = "document.pdf"

        input_type, format_type = ContentTypeDetector.detect_input_type(
            content=content, filename=filename
        )

        assert input_type == "multipart"
        assert format_type == "application/pdf"

    def test_detect_input_type_binary(self):
        """Test input type detection for binary upload"""
        content = b"%PDF-1.4"

        input_type, format_type = ContentTypeDetector.detect_input_type(content=content)

        assert input_type == "binary"
        assert format_type == "application/pdf"

    def test_detect_input_type_content_type_priority(self):
        """Test content type header takes priority over other detection"""
        content = b"%PDF-1.4"
        content_type = "text/plain"
        filename = "document.pdf"

        input_type, format_type = ContentTypeDetector.detect_input_type(
            content_type=content_type, filename=filename, content=content
        )

        assert input_type == "multipart"
        assert format_type == "text/plain"

    def test_detect_input_type_filename_priority(self):
        """Test filename detection takes priority over magic bytes"""
        content = b"Some text content"  # Would normally be text/plain
        filename = "document.pdf"

        input_type, format_type = ContentTypeDetector.detect_input_type(
            filename=filename, content=content
        )

        assert input_type == "multipart"
        assert format_type == "application/pdf"

    def test_detect_input_type_fallback(self):
        """Test fallback behavior with binary content"""
        # Use content that will actually fail UTF-8 decode
        content = b"\xff\xfe\xfd\xfc"

        input_type, format_type = ContentTypeDetector.detect_input_type(content=content)

        assert input_type == "binary"
        # Binary content that can't be decoded falls through magic bytes detection and returns None,
        # which gets caught by the "or" chain and defaults to "application/octet-stream"
        assert format_type == "application/octet-stream"

    def test_detect_input_type_unknown(self):
        """Test unknown input type"""
        input_type, format_type = ContentTypeDetector.detect_input_type()

        assert input_type == "unknown"
        assert format_type == "application/octet-stream"

    def test_get_source_type_known_types(self):
        """Test source type mapping for known MIME types"""
        test_cases = [
            ("application/pdf", "pdf"),
            (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "docx",
            ),
            (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "xlsx",
            ),
            (
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                "pptx",
            ),
            ("text/html", "html"),
            ("text/plain", "text"),
            ("text/markdown", "markdown"),
            ("application/json", "json"),
            ("text/url", "url"),
            ("image/png", "image"),
            ("image/jpeg", "image"),
            ("image/gif", "image"),
            ("audio/mpeg", "audio"),
            ("audio/wav", "audio"),
            ("video/mp4", "video"),
        ]

        for mime_type, expected in test_cases:
            result = ContentTypeDetector.get_source_type(mime_type)
            assert result == expected

    def test_get_source_type_unknown(self):
        """Test source type for unknown MIME type"""
        result = ContentTypeDetector.get_source_type("application/unknown")
        assert result == "unknown"

    def test_is_supported_format_supported(self):
        """Test supported format detection"""
        supported_formats = [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "text/html",
            "text/plain",
            "text/markdown",
            "application/json",
            "text/url",
            "image/png",
            "image/jpeg",
            "image/gif",
            "text/xml",
            "application/xml",
        ]

        for format_type in supported_formats:
            assert ContentTypeDetector.is_supported_format(format_type) is True

    def test_is_supported_format_unsupported(self):
        """Test unsupported format detection"""
        unsupported_formats = [
            "application/unknown",
            "video/mp4",
            "audio/mpeg",
            "image/bmp",
        ]

        for format_type in unsupported_formats:
            assert ContentTypeDetector.is_supported_format(format_type) is False

    def test_get_supported_formats_structure(self):
        """Test supported formats structure"""
        formats = ContentTypeDetector.get_supported_formats()

        # Check that key format types exist
        required_formats = [
            "pdf",
            "docx",
            "xlsx",
            "pptx",
            "html",
            "markdown",
            "text",
            "json",
            "xml",
            "images",
        ]
        for format_name in required_formats:
            assert format_name in formats

        # Check structure of one format
        pdf_format = formats["pdf"]
        assert "mime_types" in pdf_format
        assert "extensions" in pdf_format
        assert "features" in pdf_format
        assert "max_size_mb" in pdf_format

        assert isinstance(pdf_format["mime_types"], list)
        assert isinstance(pdf_format["extensions"], list)
        assert isinstance(pdf_format["features"], list)
        assert isinstance(pdf_format["max_size_mb"], int)

    def test_get_supported_formats_specific_values(self):
        """Test specific values in supported formats"""
        formats = ContentTypeDetector.get_supported_formats()

        # Test PDF format
        pdf_format = formats["pdf"]
        assert "application/pdf" in pdf_format["mime_types"]
        assert ".pdf" in pdf_format["extensions"]
        assert "ocr" in pdf_format["features"]
        assert pdf_format["max_size_mb"] == 50

        # Test HTML format
        html_format = formats["html"]
        assert "text/html" in html_format["mime_types"]
        assert ".html" in html_format["extensions"]
        assert "js_rendering" in html_format["features"]
        assert html_format["max_size_mb"] == 10
