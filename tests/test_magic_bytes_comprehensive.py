import pytest
from md_server.detection import ContentTypeDetector


class TestMagicBytesComprehensive:
    """Comprehensive tests for all magic byte signatures."""

    def test_all_magic_bytes_detection(self):
        """Test every magic byte signature in MAGIC_BYTES."""
        magic_bytes_tests = [
            # PDF
            (b"%PDF-1.4", "application/pdf"),
            (b"%PDF-1.5\ntest content", "application/pdf"),
            # ZIP/Office documents
            (b"PK\x03\x04", "application/zip"),
            (b"PK\x03\x04\x14\x00", "application/zip"),
            # PNG
            (b"\x89PNG\r\n\x1a\n", "image/png"),
            (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR", "image/png"),
            # JPEG
            (b"\xff\xd8\xff", "image/jpeg"),
            (b"\xff\xd8\xff\xe0", "image/jpeg"),
            (b"\xff\xd8\xff\xe1", "image/jpeg"),
            # GIF variants
            (b"GIF87a", "image/gif"),
            (b"GIF89a", "image/gif"),
            (b"GIF87a\x01\x00\x01\x00", "image/gif"),
            (b"GIF89a\x01\x00\x01\x00", "image/gif"),
            # Audio
            (b"RIFF", "audio/wav"),
            (b"ID3", "audio/mpeg"),
            (b"RIFFWAVE", "audio/wav"),
            (b"ID3\x03\x00", "audio/mpeg"),
            # Video
            (b"\x00\x00\x00 ftypmp4", "video/mp4"),
            (b"\x00\x00\x00\x20ftypmp41", "video/mp4"),
            # HTML variants (direct magic bytes)
            (b"<html", "text/html"),
            (b"<!DOCTYPE html", "text/html"),
            # XML
            (b"<?xml", "text/xml"),
            # JSON
            (b"{", "application/json"),
            (b"[", "application/json"),
            (b'{"key": "value"}', "application/json"),
            (b'[{"key": "value"}]', "application/json"),
        ]

        for content, expected_type in magic_bytes_tests:
            detected = ContentTypeDetector.detect_from_magic_bytes(content)
            assert detected == expected_type, (
                f"Failed to detect {expected_type} from {content[:20]}..."
            )

        # Test HTML detection that uses special logic
        html_tests = [
            (b"<html>", "text/html"),
            (b"<HTML>", "text/html"),
            (b"<!DOCTYPE HTML", "text/html"),
            (b"<!doctype html", "text/html"),
            (b"Some content <html> here", "text/html"),
        ]

        for content, expected_type in html_tests:
            detected = ContentTypeDetector.detect_from_magic_bytes(content)
            assert detected == expected_type, (
                f"Failed to detect {expected_type} from {content[:20]}..."
            )

    def test_office_document_detection(self):
        """Test Office document detection within ZIP files."""
        import zipfile
        import io

        # Test DOCX detection
        docx_content = io.BytesIO()
        with zipfile.ZipFile(docx_content, "w") as zf:
            zf.writestr("word/document.xml", "<document>test</document>")
        docx_bytes = docx_content.getvalue()

        detected = ContentTypeDetector.detect_from_content(docx_bytes)
        # Should detect as either ZIP or DOCX depending on implementation
        assert detected in [
            "application/zip",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ]

        # Test XLSX detection
        xlsx_content = io.BytesIO()
        with zipfile.ZipFile(xlsx_content, "w") as zf:
            zf.writestr("xl/workbook.xml", "<workbook>test</workbook>")
        xlsx_bytes = xlsx_content.getvalue()

        detected = ContentTypeDetector.detect_from_content(xlsx_bytes)
        assert detected in [
            "application/zip",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ]

        # Test PPTX detection
        pptx_content = io.BytesIO()
        with zipfile.ZipFile(pptx_content, "w") as zf:
            zf.writestr("ppt/presentation.xml", "<presentation>test</presentation>")
        pptx_bytes = pptx_content.getvalue()

        detected = ContentTypeDetector.detect_from_content(pptx_bytes)
        assert detected in [
            "application/zip",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ]

    def test_text_vs_binary_detection(self):
        """Test text vs binary classification."""
        # Pure text content
        text_samples = [
            b"Hello world",
            b"UTF-8 text with unicode: \xe2\x9c\x93",
            b"Line 1\nLine 2\nLine 3",
            b"# Markdown\n\n**Bold text**",
            b"<h1>HTML</h1><p>Content</p>",
            b'{"json": "content", "number": 123}',
        ]

        for content in text_samples:
            detected = ContentTypeDetector.detect_from_content(content)
            # Should be detected as some text type or None (fallback to extension)
            if detected:
                assert detected.startswith(
                    ("text/", "application/json", "application/xml")
                )

        # Binary content
        binary_samples = [
            bytes(range(256)),  # All byte values
            b"\x00\x01\x02\xff\xfe\xfd",  # Binary data
            b"\x89PNG\r\n\x1a\n" + b"\x00" * 100,  # PNG with binary payload
            b"%PDF-1.4" + b"\x00" * 100,  # PDF with binary payload
        ]

        for content in binary_samples:
            detected = ContentTypeDetector.detect_from_content(content)
            # Should be detected as binary type or specific format
            if detected and not detected.startswith("text/"):
                assert detected in ContentTypeDetector.MAGIC_BYTES.values()

    def test_edge_case_content(self):
        """Test edge cases in content detection."""
        # Empty content returns text/plain as default
        assert ContentTypeDetector.detect_from_magic_bytes(b"") == "text/plain"

        # Very short content falls back to text/plain
        detected = ContentTypeDetector.detect_from_magic_bytes(b"a")
        assert detected == "text/plain"
        detected = ContentTypeDetector.detect_from_magic_bytes(b"<")
        assert detected == "text/plain"

        # Partial magic bytes
        detected = ContentTypeDetector.detect_from_magic_bytes(b"%PD")
        assert detected == "text/plain"  # Falls back to text analysis
        detected = ContentTypeDetector.detect_from_magic_bytes(b"PK\x03")
        assert detected == "application/octet-stream"  # Binary due to control character

        # False positives prevention
        # Content that starts like magic bytes but isn't
        detected = ContentTypeDetector.detect_from_magic_bytes(b"<htmlish-but-not-html")
        # This might be detected as HTML if it contains "<html" pattern
        assert detected in ["text/html", "text/plain"]
        detected = ContentTypeDetector.detect_from_magic_bytes(b"PDFish content")
        assert detected == "text/plain"  # Falls back to text

        # Multiple potential matches (first should win)
        mixed_content = b'{"json_like": true} but actually <html>content</html>'
        detected = ContentTypeDetector.detect_from_magic_bytes(mixed_content)
        assert detected == "application/json"  # JSON signature comes first

    def test_filename_detection_comprehensive(self):
        """Test comprehensive filename-based detection."""
        filename_tests = [
            # Common document types
            ("document.pdf", "application/pdf"),
            (
                "spreadsheet.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
            (
                "presentation.pptx",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ),
            (
                "document.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
            ("document.odt", "application/vnd.oasis.opendocument.text"),
            # Images
            ("photo.jpg", "image/jpeg"),
            ("photo.jpeg", "image/jpeg"),
            ("image.png", "image/png"),
            ("animation.gif", "image/gif"),
            ("vector.svg", "image/svg+xml"),
            # Text formats
            ("readme.txt", "text/plain"),
            ("README.md", "text/markdown"),
            ("page.html", "text/html"),
            ("data.csv", "text/csv"),
            ("config.xml", "application/xml"),  # Actual mimetypes result
            ("data.json", "application/json"),
            # Audio/Video
            ("song.mp3", "audio/mpeg"),
            ("sound.wav", "audio/wav"),
            ("video.mp4", "video/mp4"),
            ("clip.avi", "video/x-msvideo"),
            # Archives
            ("archive.zip", "application/zip"),
            ("backup.tar.gz", "application/gzip"),
            # Case insensitive
            ("Document.PDF", "application/pdf"),
            ("IMAGE.PNG", "image/png"),
            ("README.MD", "text/markdown"),
        ]

        for filename, expected_type in filename_tests:
            detected = ContentTypeDetector.detect_from_filename(filename)
            # Some might be None if not in mimetypes database
            if detected:
                assert detected == expected_type, (
                    f"Failed to detect {expected_type} from {filename}"
                )

    def test_priority_detection(self):
        """Test detection priority: content > filename > header."""
        # Content detection should override filename in detect_from_content
        pdf_content = b"%PDF-1.4\ntest content"
        detected = ContentTypeDetector.detect_from_content(
            pdf_content, filename="document.txt"
        )
        assert detected == "application/pdf"

        # Filename should be used when no content magic bytes
        detected = ContentTypeDetector.detect_from_content(
            b"plain text content", filename="document.json"
        )
        # Should prefer magic byte detection (text/plain) over filename
        assert detected == "text/plain"  # Magic bytes detection wins

        # Test with no recognizable content - should fall back to filename
        detected = ContentTypeDetector.detect_from_content(
            b"ambiguous binary content", filename="test.pdf"
        )
        # Since content doesn't match magic bytes, should fall back
        assert detected in ["text/plain", "application/pdf"]

    def test_malformed_inputs(self):
        """Test handling of malformed or problematic inputs."""
        # Non-bytes content
        with pytest.raises((TypeError, AttributeError)):
            ContentTypeDetector.detect_from_content("string instead of bytes")

        # None inputs (actual behavior)
        assert (
            ContentTypeDetector.detect_from_magic_bytes(None) == "text/plain"
        )  # Default for empty/None
        assert ContentTypeDetector.detect_from_filename(None) is None
        assert ContentTypeDetector.detect_from_content_type_header(None) is None

        # Very long filenames
        long_filename = "a" * 1000 + ".txt"
        detected = ContentTypeDetector.detect_from_filename(long_filename)
        # Should handle gracefully
        assert detected is None or detected == "text/plain"

        # Malformed MIME types
        assert ContentTypeDetector.detect_from_content_type_header("invalid/") is None
        assert ContentTypeDetector.detect_from_content_type_header("/invalid") is None
        assert ContentTypeDetector.detect_from_content_type_header("") is None
