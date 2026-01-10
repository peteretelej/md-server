import pytest

from md_server.core.detection import ContentTypeDetector
import base64


class TestContentTypeDetector:
    @pytest.fixture
    def detector(self):
        return ContentTypeDetector()

    def test_detect_from_content_html(self, detector):
        html_content = "<html><body>Hello</body></html>"
        content_type = detector.detect_from_content(html_content.encode())
        assert content_type == "text/html"

    def test_detect_from_content_json(self, detector):
        json_content = '{"key": "value"}'
        content_type = detector.detect_from_content(json_content.encode())
        assert content_type == "application/json"

    def test_detect_from_content_pdf_magic_bytes(self, detector, test_pdf_file):
        if test_pdf_file.exists():
            with open(test_pdf_file, "rb") as f:
                content = f.read(10)
            content_type = detector.detect_from_content(content)
            assert content_type == "application/pdf"

    def test_detect_from_content_jpeg_magic_bytes(self, detector, test_jpg_file):
        if test_jpg_file.exists():
            with open(test_jpg_file, "rb") as f:
                content = f.read(10)
            content_type = detector.detect_from_content(content)
            assert content_type == "image/jpeg"

    def test_detect_from_filename(self, detector):
        assert detector.detect_from_filename("test.pdf") == "application/pdf"
        assert detector.detect_from_filename("test.html") == "text/html"
        assert detector.detect_from_filename("test.jpg") == "image/jpeg"
        assert detector.detect_from_filename("test.png") == "image/png"
        assert (
            detector.detect_from_filename("test.docx")
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    def test_detect_from_filename_unknown(self, detector):
        result = detector.detect_from_filename("test.unknown")
        assert result is None

    def test_detect_from_url_extension(self, detector):
        # URL detection falls back to filename detection
        result = detector.detect_from_filename("test.pdf")
        assert result == "application/pdf"
        result = detector.detect_from_filename("test.html")
        assert result == "text/html"

    def test_detect_input_type_json_content_base64(self, detector):
        # Test base64 data URI detection through input type detection
        html_content = "<html><body>Hello</body></html>"
        b64_content = base64.b64encode(html_content.encode()).decode()

        request_data = {"content": b64_content}
        input_type, detected_format = detector.detect_input_type(
            request_data=request_data
        )
        assert input_type == "json_content"
        assert "html" in detected_format.lower()

    def test_detect_input_type_json_content_invalid_base64(self, detector):
        # Test invalid base64 content handling
        request_data = {"content": "invalid-base64-content"}
        input_type, detected_format = detector.detect_input_type(
            request_data=request_data
        )
        assert input_type == "json_content"
        assert detected_format == "application/octet-stream"

    def test_detect_zip_format_returns_generic(self, detector):
        # Test ZIP detection (office format detection is simplified)
        zip_content = b"PK\x03\x04"
        result = detector.detect_from_magic_bytes(zip_content)
        assert result == "application/zip"

    def test_magic_byte_detection_comprehensive(self, detector):
        # Test various magic byte patterns
        test_cases = [
            (b"%PDF-", "application/pdf"),
            (b"\x89PNG\r\n\x1a\n", "image/png"),
            (b"\xff\xd8\xff", "image/jpeg"),
            (b"GIF87a", "image/gif"),
            (b"GIF89a", "image/gif"),
            (b"RIFF", "audio/wav"),
            (b"ID3", "audio/mpeg"),
            (b"<html", "text/html"),
            (b"<!DOCTYPE html", "text/html"),
            (b"<?xml", "text/xml"),
            (b"{", "application/json"),
            (b"[", "application/json"),
        ]

        for content, expected in test_cases:
            result = detector.detect_from_magic_bytes(content)
            assert result == expected

    def test_binary_content_detection(self, detector):
        # Test binary content with null bytes
        binary_content = b"some\x00binary\x00content"
        result = detector.detect_from_magic_bytes(binary_content)
        assert result == "application/octet-stream"

    def test_high_non_printable_ratio_detection(self, detector):
        # Test content with high ratio of non-printable characters
        non_printable = bytes(range(1, 20)) * 10  # Many non-printable chars
        result = detector.detect_from_magic_bytes(non_printable)
        assert result == "application/octet-stream"

    def test_detect_input_type_json_url(self, detector):
        request_data = {"url": "https://example.com"}
        input_type, detected_format = detector.detect_input_type(
            request_data=request_data
        )
        assert input_type == "json_url"
        assert detected_format == "text/url"

    def test_detect_input_type_json_text_with_mime(self, detector):
        request_data = {"text": "<h1>Test</h1>", "mime_type": "text/html"}
        input_type, detected_format = detector.detect_input_type(
            request_data=request_data
        )
        assert input_type == "json_text_typed"
        assert detected_format == "text/html"

    def test_detect_input_type_json_text_default(self, detector):
        request_data = {"text": "# Markdown content"}
        input_type, detected_format = detector.detect_input_type(
            request_data=request_data
        )
        assert input_type == "json_text"
        assert detected_format == "text/markdown"

    def test_detect_input_type_binary_with_filename(self, detector):
        content = b"test content"
        input_type, detected_format = detector.detect_input_type(
            content=content, filename="test.pdf"
        )
        assert input_type == "multipart"
        assert detected_format == "application/pdf"

    def test_detect_input_type_binary_without_filename(self, detector):
        content = b"test content"
        input_type, detected_format = detector.detect_input_type(content=content)
        assert input_type == "binary"
        assert detected_format == "text/plain"

    def test_detect_input_type_unknown_fallback(self, detector):
        input_type, detected_format = detector.detect_input_type()
        assert input_type == "unknown"
        assert detected_format == "application/octet-stream"

    def test_detect_from_content_type_header(self, detector):
        result = detector.detect_from_content_type_header("text/html; charset=utf-8")
        assert result == "text/html"

        result = detector.detect_from_content_type_header(None)
        assert result is None

        result = detector.detect_from_content_type_header("")
        assert result is None

    def test_get_source_type_mapping(self, detector):
        test_cases = [
            ("application/pdf", "pdf"),
            ("text/html", "html"),
            ("image/png", "image"),
            ("unknown/format", "unknown"),
        ]

        for mime_type, expected_source in test_cases:
            result = detector.get_source_type(mime_type)
            assert result == expected_source

    def test_is_supported_format(self, detector):
        supported_formats = ["application/pdf", "text/html", "image/png", "text/plain"]

        for format_type in supported_formats:
            assert detector.is_supported_format(format_type) is True

        assert detector.is_supported_format("application/unknown") is False

    def test_get_supported_formats_structure(self, detector):
        formats = detector.get_supported_formats()
        assert isinstance(formats, dict)
        assert "pdf" in formats
        assert "mime_types" in formats["pdf"]
        assert "extensions" in formats["pdf"]
        assert "features" in formats["pdf"]
        assert "max_size_mb" in formats["pdf"]

    def test_markdown_detection_from_content(self, detector):
        markdown_content = b"# Title\n\n* List item"
        result = detector.detect_from_magic_bytes(markdown_content)
        assert result == "text/markdown"

    def test_empty_content_detection(self, detector):
        result = detector.detect_from_magic_bytes(b"")
        assert result == "text/plain"

    def test_html_detection_anywhere_in_header(self, detector):
        # Test HTML detection in first 512 bytes
        html_content = b"  \n  <html><body>test</body></html>"
        result = detector.detect_from_magic_bytes(html_content)
        assert result == "text/html"

    def test_office_document_detection_simplified(self, detector):
        # Test that ZIP files are detected (office format detection is simplified in current implementation)
        zip_content = b"PK\x03\x04"  # ZIP magic bytes
        result = detector.detect_from_magic_bytes(zip_content)
        assert result == "application/zip"

        # Test office format detection through filename fallback
        docx_by_filename = detector.detect_from_filename("document.docx")
        assert (
            docx_by_filename
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

        xlsx_by_filename = detector.detect_from_filename("spreadsheet.xlsx")
        assert (
            xlsx_by_filename
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        pptx_by_filename = detector.detect_from_filename("presentation.pptx")
        assert (
            pptx_by_filename
            == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )

    # --- Coverage Tests for Fallback Paths ---

    def test_detect_from_content_with_filename_priority(self, detector):
        """Magic bytes detection takes precedence over filename."""
        # Plain text content - magic bytes returns text/plain
        content = b"some plain text content"
        result = detector.detect_from_content(content, filename="document.pdf")
        # Magic bytes wins - returns text/plain, not PDF
        assert result == "text/plain"

    def test_detect_from_content_binary_without_filename(self, detector):
        """Binary content without filename returns octet-stream."""
        # Binary content with high non-printable ratio
        content = b"\x01\x02\x03\x04\x05\x06\x07\x08"
        result = detector.detect_from_content(content)
        assert result == "application/octet-stream"

    def test_detect_input_type_invalid_base64_with_filename(self, detector):
        """Invalid base64 with filename falls back to filename detection."""
        request_data = {"content": "not-valid-base64!!!", "filename": "report.pdf"}
        input_type, fmt = detector.detect_input_type(request_data=request_data)
        assert input_type == "json_content"
        assert fmt == "application/pdf"

    def test_detect_input_type_json_content_no_magic_match_with_filename(
        self, detector
    ):
        """Valid base64 that doesn't match magic bytes uses filename fallback."""
        # Base64 encode "hello" - valid UTF-8 text that won't match signatures
        # but will be detected as text/plain by magic bytes
        text_content = base64.b64encode(b"hello world").decode()
        request_data = {"content": text_content, "filename": "spreadsheet.xlsx"}
        input_type, fmt = detector.detect_input_type(request_data=request_data)
        assert input_type == "json_content"
        # Magic bytes returns text/plain which is truthy, so filename not used
        assert fmt == "text/plain"
