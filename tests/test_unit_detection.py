import pytest
from md_server.detection import ContentTypeDetector
import tempfile
from pathlib import Path


class TestContentTypeDetector:
    """Unit tests for ContentTypeDetector"""

    def test_all_magic_bytes(self):
        """Test each entry in MAGIC_BYTES"""
        test_cases = [
            (b"%PDF-1.4\n", "application/pdf"),
            (b"PK\x03\x04", "application/zip"), 
            (b"\x89PNG\r\n\x1a\n", "image/png"),
            (b"\xff\xd8\xff", "image/jpeg"),
            (b"GIF87a", "image/gif"),
            (b"GIF89a", "image/gif"),
            (b"RIFF", "audio/wav"),
            (b"ID3", "audio/mpeg"),
            (b"\x00\x00\x00 ftypmp4", "video/mp4"),
            (b"<html", "text/html"),
            (b"<!DOCTYPE html", "text/html"),
            (b"<?xml", "text/xml"),
            (b'{"key": "value"}', "application/json"),
            (b'["item1", "item2"]', "application/json"),
        ]
        
        for content, expected_type in test_cases:
            detected = ContentTypeDetector.detect_from_magic_bytes(content + b"\x00" * 50)
            assert detected == expected_type, f"Failed for {content[:10]}: expected {expected_type}, got {detected}"

    def test_office_detection(self):
        """Test DOCX, XLSX, PPTX as ZIP files"""
        # ZIP signature that Office documents use
        zip_content = b"PK\x03\x04" + b"\x00" * 100
        detected = ContentTypeDetector.detect_from_magic_bytes(zip_content)
        assert detected == "application/zip"
        
        # The _detect_office_format method currently returns generic zip
        # but in a full implementation would parse ZIP structure
        office_type = ContentTypeDetector._detect_office_format(zip_content)
        assert office_type == "application/zip"

    def test_text_detection(self):
        """Test UTF-8, ASCII, binary detection"""
        # Plain ASCII text
        ascii_text = b"Hello, world! This is plain text."
        detected = ContentTypeDetector.detect_from_magic_bytes(ascii_text)
        assert detected == "text/plain"
        
        # UTF-8 with unicode characters
        utf8_text = "Hello, 世界! 🌍".encode('utf-8')
        detected = ContentTypeDetector.detect_from_magic_bytes(utf8_text)
        assert detected == "text/plain"
        
        # Markdown-like text
        markdown_text = b"# Heading\n\n* List item\n* Another item"
        detected = ContentTypeDetector.detect_from_magic_bytes(markdown_text)
        assert detected == "text/markdown"
        
        # Text with asterisk prefix
        asterisk_text = b"* This looks like markdown"
        detected = ContentTypeDetector.detect_from_magic_bytes(asterisk_text)
        assert detected == "text/markdown"
        
        # Binary content with null bytes
        binary_content = b"\x00\x01\x02\x03" * 25
        detected = ContentTypeDetector.detect_from_magic_bytes(binary_content)
        assert detected == "application/octet-stream"
        
        # High ratio of non-printable characters
        non_printable = bytes(range(1, 32)) * 10  # Control characters (avoiding null)
        detected = ContentTypeDetector.detect_from_magic_bytes(non_printable)
        assert detected == "application/octet-stream"
        
        # Invalid UTF-8 sequence
        invalid_utf8 = b"\xff\xfe\x00\x00" + b"\x80" * 50
        detected = ContentTypeDetector.detect_from_magic_bytes(invalid_utf8)
        assert detected == "application/octet-stream"

    def test_html_detection_patterns(self):
        """Test HTML detection patterns"""
        html_patterns = [
            b"<html><head><title>Test</title></head>",
            b"<!DOCTYPE html><html><body>",
            b"<HTML><HEAD><TITLE>Test</TITLE></HEAD>",  # Case insensitive
            b"<!doctype html><html>",  # Case insensitive DOCTYPE
        ]
        
        for pattern in html_patterns:
            content = pattern + b" more content here" + b"\x00" * 50
            detected = ContentTypeDetector.detect_from_magic_bytes(content)
            assert detected == "text/html", f"Failed for pattern: {pattern}"

    def test_edge_cases(self):
        """Test edge cases"""
        # Empty content
        detected = ContentTypeDetector.detect_from_magic_bytes(b"")
        assert detected == "text/plain"
        
        # Very short content
        detected = ContentTypeDetector.detect_from_magic_bytes(b"a")
        assert detected == "text/plain"
        
        # Content that starts with whitespace
        detected = ContentTypeDetector.detect_from_magic_bytes(b"   <html>")
        assert detected == "text/html"  # HTML pattern found in first 512 bytes
        
        # Content with HTML in middle
        mixed_content = b"Some text before <html><body>HTML content</body></html>"
        detected = ContentTypeDetector.detect_from_magic_bytes(mixed_content)
        assert detected == "text/html"  # Should find HTML in first 512 bytes

    def test_filename_detection(self):
        """Test filename-based detection"""
        test_cases = [
            ("document.pdf", "application/pdf"),
            ("presentation.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
            ("spreadsheet.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            ("document.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            ("page.html", "text/html"),
            ("page.htm", "text/html"),
            ("readme.txt", "text/plain"),
            ("readme.md", "text/markdown"),
            ("data.json", "application/json"),
            ("config.xml", "application/xml"),
            ("image.png", "image/png"),
            ("photo.jpg", "image/jpeg"),
            ("photo.jpeg", "image/jpeg"),
            ("animation.gif", "image/gif"),
            ("unknown.xyz", "chemical/x-xyz"),  # mimetypes may have this
            ("", None),  # Empty filename
            (None, None),  # None filename
        ]
        
        for filename, expected in test_cases:
            detected = ContentTypeDetector.detect_from_filename(filename)
            assert detected == expected, f"Failed for {filename}: expected {expected}, got {detected}"

    def test_content_type_header_detection(self):
        """Test Content-Type header parsing"""
        test_cases = [
            ("text/html; charset=utf-8", "text/html"),
            ("application/pdf", "application/pdf"),
            ("text/plain; charset=iso-8859-1", "text/plain"),
            ("image/jpeg; quality=85", "image/jpeg"),
            ("application/json; charset=utf-8; boundary=something", "application/json"),
            ("", None),
            (None, None),
            ("invalid", "invalid"),  # Invalid but returns as-is
        ]
        
        for content_type, expected in test_cases:
            detected = ContentTypeDetector.detect_from_content_type_header(content_type)
            assert detected == expected, f"Failed for {content_type}: expected {expected}, got {detected}"

    def test_input_type_detection(self):
        """Test input type detection logic"""
        # JSON with URL
        input_type, format_type = ContentTypeDetector.detect_input_type(
            request_data={"url": "https://example.com"}
        )
        assert input_type == "json_url"
        assert format_type == "text/url"
        
        # JSON with base64 content
        pdf_content = b"%PDF-1.4\nSample"
        import base64
        encoded = base64.b64encode(pdf_content).decode()
        input_type, format_type = ContentTypeDetector.detect_input_type(
            request_data={"content": encoded}
        )
        assert input_type == "json_content"
        assert format_type == "application/pdf"
        
        # JSON with text and mime_type
        input_type, format_type = ContentTypeDetector.detect_input_type(
            request_data={"text": "# Heading", "mime_type": "text/markdown"}
        )
        assert input_type == "json_text_typed"
        assert format_type == "text/markdown"
        
        # JSON with text only
        input_type, format_type = ContentTypeDetector.detect_input_type(
            request_data={"text": "Some text"}
        )
        assert input_type == "json_text"
        assert format_type == "text/markdown"
        
        # Binary upload with filename (multipart)
        input_type, format_type = ContentTypeDetector.detect_input_type(
            content=b"%PDF-1.4\nSample",
            filename="document.pdf",
            content_type="application/pdf"
        )
        assert input_type == "multipart"
        assert format_type == "application/pdf"
        
        # Binary upload without filename
        input_type, format_type = ContentTypeDetector.detect_input_type(
            content=b"%PDF-1.4\nSample",
            content_type="application/pdf"
        )
        assert input_type == "binary"
        assert format_type == "application/pdf"

    def test_source_type_mapping(self):
        """Test MIME to source type conversion"""
        mappings = [
            ("application/pdf", "pdf"),
            ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx"),
            ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"),
            ("application/vnd.openxmlformats-officedocument.presentationml.presentation", "pptx"),
            ("text/html", "html"),
            ("text/plain", "text"),
            ("text/markdown", "markdown"),
            ("application/json", "json"),
            ("text/url", "url"),
            ("image/png", "image"),
            ("image/jpeg", "image"),
            ("audio/mpeg", "audio"),
            ("video/mp4", "video"),
            ("unknown/type", "unknown"),
        ]
        
        for mime_type, expected_source in mappings:
            source = ContentTypeDetector.get_source_type(mime_type)
            assert source == expected_source, f"Failed for {mime_type}: expected {expected_source}, got {source}"

    def test_supported_format_check(self):
        """Test supported format validation"""
        supported = [
            "application/pdf",
            "text/html",
            "text/plain",
            "text/markdown",
            "application/json",
            "image/png",
            "image/jpeg",
        ]
        
        unsupported = [
            "application/x-rar",
            "video/x-msvideo",
            "application/x-executable",
            "unknown/format",
        ]
        
        for format_type in supported:
            assert ContentTypeDetector.is_supported_format(format_type), f"{format_type} should be supported"
            
        for format_type in unsupported:
            assert not ContentTypeDetector.is_supported_format(format_type), f"{format_type} should not be supported"

    def test_supported_formats_metadata(self):
        """Test supported formats metadata structure"""
        formats = ContentTypeDetector.get_supported_formats()
        
        # Check that we have expected format categories
        expected_categories = ["pdf", "docx", "xlsx", "pptx", "html", "markdown", "text", "json", "xml", "images"]
        
        for category in expected_categories:
            assert category in formats, f"Missing format category: {category}"
            
            # Check required fields
            format_info = formats[category]
            assert "mime_types" in format_info
            assert "extensions" in format_info
            assert "features" in format_info
            assert "max_size_mb" in format_info
            
            assert isinstance(format_info["mime_types"], list)
            assert isinstance(format_info["extensions"], list)
            assert isinstance(format_info["features"], list)
            assert isinstance(format_info["max_size_mb"], (int, float))
            assert format_info["max_size_mb"] > 0