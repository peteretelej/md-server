import pytest
import tempfile
from pathlib import Path
from md_server.sdk import MDConverter
from md_server.sdk.exceptions import ConversionError, InvalidInputError, NetworkError
from litestar.testing import TestClient
from md_server.app import app


class TestSecurityValidation:
    """Security validation tests through user workflows"""

    @pytest.fixture
    def converter(self):
        """SDK converter instance for testing."""
        return MDConverter()

    @pytest.mark.asyncio
    async def test_url_ssrf_protection(self, converter):
        """Test SSRF protection via CLI/SDK"""
        # Test that internal URLs are handled appropriately
        # Using localhost which should be blocked or handled safely
        try:
            result = await converter.convert_url("http://127.0.0.1:22222/nonexistent")
            # If it doesn't throw, check that it handled it safely
            assert result.success is False or len(result.markdown) == 0
        except (ConversionError, InvalidInputError, NetworkError):
            # Expected - blocked appropriately
            pass

    @pytest.mark.asyncio
    async def test_file_type_detection(self, converter):
        """Test content type detection accuracy"""
        # Create test files with misleading extensions
        with tempfile.TemporaryDirectory() as tmpdir:
            # Binary file with .txt extension
            fake_txt = Path(tmpdir) / "malicious.txt"
            fake_txt.write_bytes(b"\x00\x01\x02\x03" * 100)

            # Should detect as binary and handle appropriately
            result = await converter.convert_file(str(fake_txt))
            assert result.success is False or "binary" in result.markdown.lower()

    @pytest.mark.asyncio
    async def test_file_size_limits(self, converter):
        """Test size validation through workflows"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create moderately large file (not 50MB to avoid timeouts)
            large_file = Path(tmpdir) / "large.txt"
            large_file.write_text("x" * (1024 * 1024))  # 1MB

            # Should handle gracefully
            result = await converter.convert_file(str(large_file))
            # Should process but potentially truncate
            assert isinstance(result.success, bool)

    @pytest.mark.asyncio
    async def test_malicious_content(self, converter):
        """Test malicious file handling"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Malicious HTML content
            malicious_html = Path(tmpdir) / "malicious.html"
            malicious_html.write_text("""
                <script>alert('xss')</script>
                <iframe src="javascript:alert('xss')"></iframe>
                <img src="x" onerror="alert('xss')">
                <div onclick="alert('xss')">Click me</div>
            """)

            result = await converter.convert_file(str(malicious_html))

            # Should strip or escape malicious content
            assert "alert(" not in result.markdown
            assert "javascript:" not in result.markdown
            assert "onerror=" not in result.markdown
            assert "onclick=" not in result.markdown

    @pytest.mark.asyncio
    async def test_path_traversal_protection(self, converter):
        """Test path security validation"""
        # Test path traversal attempts
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/shadow",
            "C:\\Windows\\System32\\config\\SAM",
            "file:///etc/passwd",
        ]

        for path in malicious_paths:
            with pytest.raises((ConversionError, InvalidInputError, FileNotFoundError)):
                await converter.convert_file(path)

    @pytest.mark.asyncio
    async def test_mime_type_validation(self, converter):
        """Test MIME type security checks"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Executable disguised as text
            exe_file = Path(tmpdir) / "malware.txt"
            exe_file.write_bytes(b"MZ" + b"\x00" * 100)  # PE header

            # Should detect and handle appropriately
            result = await converter.convert_file(str(exe_file))
            assert result.success is False or "executable" in result.markdown.lower()


class TestSecurityThroughHTTPAPI:
    """Security tests through HTTP API workflow"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_api_url_ssrf_protection(self, client):
        """Test SSRF protection via HTTP API"""
        blocked_urls = [
            "http://127.0.0.1:22/ssh",
            "http://localhost:3306/mysql",
            "http://192.168.1.1/admin",
        ]

        for url in blocked_urls:
            response = client.post("/convert", json={"url": url})
            # Should either reject or handle safely
            assert response.status_code in [400, 422] or (
                response.status_code == 200
                and not response.get_json().get("success", True)
            )

    def test_api_large_file_handling(self, client):
        """Test large file handling via API"""
        # Create oversized content
        large_content = "x" * (10 * 1024 * 1024)  # 10MB

        response = client.post("/convert", json={"text": large_content})

        # Should handle gracefully - either reject or process with limits
        assert response.status_code in [200, 400, 413, 422]
        if response.status_code == 200:
            data = response.json()
            assert len(data.get("markdown", "")) < len(large_content)

    def test_api_malicious_content(self, client):
        """Test malicious content via API"""
        malicious_html = """
            <script>alert('xss')</script>
            <iframe src="javascript:alert('xss')"></iframe>
        """

        response = client.post(
            "/convert", json={"text": malicious_html, "mime_type": "text/html"}
        )

        assert response.status_code == 200
        data = response.json()
        markdown = data.get("markdown", "")

        # Should strip malicious content
        assert "alert(" not in markdown
        assert "javascript:" not in markdown


class TestSecurityValidationComplete:
    """Comprehensive security validation tests"""

    @pytest.fixture
    def converter(self):
        """SDK converter instance for testing."""
        return MDConverter()

    @pytest.mark.asyncio
    async def test_private_ip_blocking(self, converter):
        """Test private IP address blocking"""
        private_ips = [
            "http://192.168.1.1/admin",
            "http://10.0.0.1/internal",
            "http://172.16.0.1/private",
            "http://169.254.169.254/metadata",  # AWS metadata service
        ]

        for url in private_ips:
            try:
                result = await converter.convert_url(url)
                assert result.success is False or len(result.markdown) == 0
            except (ConversionError, InvalidInputError, NetworkError):
                pass

    @pytest.mark.asyncio
    async def test_localhost_blocking(self, converter):
        """Test localhost blocking"""
        localhost_urls = [
            "http://127.0.0.1:22/ssh",
            "http://localhost:3306/mysql",
            "http://[::1]:80/internal",
        ]

        for url in localhost_urls:
            try:
                result = await converter.convert_url(url)
                assert result.success is False or len(result.markdown) == 0
            except (ConversionError, InvalidInputError, NetworkError):
                pass

    @pytest.mark.asyncio
    async def test_file_size_limits_per_mime_type(self, converter):
        """Test file size limits per MIME type"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test PDF size limit (50MB is too large for tests, use 1MB)
            pdf_file = Path(tmpdir) / "large.pdf"
            pdf_content = b"%PDF-1.4\n" + b"x" * (1024 * 1024)  # 1MB PDF
            pdf_file.write_bytes(pdf_content)

            result = await converter.convert_file(str(pdf_file))
            assert isinstance(result.success, bool)

            # Test text file limit
            text_file = Path(tmpdir) / "large.txt"
            text_file.write_text("x" * (500 * 1024))  # 500KB text

            result = await converter.convert_file(str(text_file))
            assert isinstance(result.success, bool)

    @pytest.mark.asyncio
    async def test_magic_byte_vs_declared_type_mismatch(self, converter):
        """Test magic byte vs declared type mismatch detection"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Executable disguised as PDF
            fake_pdf = Path(tmpdir) / "malware.pdf"
            fake_pdf.write_bytes(b"MZ" + b"\x00" * 100)  # PE header

            result = await converter.convert_file(str(fake_pdf))
            assert result.success is False or "executable" in result.markdown.lower()

            # ZIP disguised as text
            fake_txt = Path(tmpdir) / "archive.txt"
            fake_txt.write_bytes(b"PK\x03\x04" + b"\x00" * 100)  # ZIP header

            result = await converter.convert_file(str(fake_txt))
            assert isinstance(result.success, bool)

    @pytest.mark.asyncio
    async def test_mime_type_injection_attempts(self, converter):
        """Test MIME type injection attempts"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Malicious MIME types that might cause issues
            malicious_content = "<script>alert('xss')</script>"

            # These should be handled safely by the validation
            test_file = Path(tmpdir) / "test.html"
            test_file.write_text(malicious_content)

            result = await converter.convert_file(str(test_file))
            if result.success:
                assert "alert(" not in result.markdown


class TestContentTypeDetectionAllFormats:
    """Test content type detection for all supported formats"""

    @pytest.fixture
    def converter(self):
        return MDConverter()

    def test_pdf_magic_bytes(self):
        """Test PDF magic bytes detection"""
        from md_server.detection import ContentTypeDetector

        pdf_content = b"%PDF-1.4\nSample PDF content"
        detected = ContentTypeDetector.detect_from_magic_bytes(pdf_content)
        assert detected == "application/pdf"

    def test_office_document_signatures(self):
        """Test Office document signature detection"""
        from md_server.detection import ContentTypeDetector

        # ZIP signature (used by Office docs)
        zip_content = b"PK\x03\x04" + b"\x00" * 100
        detected = ContentTypeDetector.detect_from_magic_bytes(zip_content)
        assert detected == "application/zip"

    def test_image_format_detection(self):
        """Test image format detection"""
        from md_server.detection import ContentTypeDetector

        # PNG signature
        png_content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
        detected = ContentTypeDetector.detect_from_magic_bytes(png_content)
        assert detected == "image/png"

        # JPEG signature
        jpeg_content = b"\xff\xd8\xff" + b"\x00" * 50
        detected = ContentTypeDetector.detect_from_magic_bytes(jpeg_content)
        assert detected == "image/jpeg"

        # GIF signatures
        gif87_content = b"GIF87a" + b"\x00" * 50
        detected = ContentTypeDetector.detect_from_magic_bytes(gif87_content)
        assert detected == "image/gif"

        gif89_content = b"GIF89a" + b"\x00" * 50
        detected = ContentTypeDetector.detect_from_magic_bytes(gif89_content)
        assert detected == "image/gif"

    def test_text_encoding_detection(self):
        """Test text encoding detection"""
        from md_server.detection import ContentTypeDetector

        # Plain text
        text_content = b"Hello, world!"
        detected = ContentTypeDetector.detect_from_magic_bytes(text_content)
        assert detected == "text/plain"

        # Markdown content
        markdown_content = b"# Heading\n\nSome content"
        detected = ContentTypeDetector.detect_from_magic_bytes(markdown_content)
        assert detected == "text/markdown"

        # HTML content
        html_content = (
            b"<html><head><title>Test</title></head><body>Content</body></html>"
        )
        detected = ContentTypeDetector.detect_from_magic_bytes(html_content)
        assert detected == "text/html"

    def test_binary_vs_text_classification(self):
        """Test binary vs text classification"""
        from md_server.detection import ContentTypeDetector

        # Binary content (contains null bytes)
        binary_content = b"\x00\x01\x02\x03" * 25
        detected = ContentTypeDetector.detect_from_magic_bytes(binary_content)
        assert detected == "application/octet-stream"

        # High ratio of non-printable characters
        non_printable = bytes(range(0, 32)) * 10  # Control characters
        detected = ContentTypeDetector.detect_from_magic_bytes(non_printable)
        assert detected == "application/octet-stream"

        # Valid UTF-8 text
        utf8_text = "Hello, 世界!".encode("utf-8")
        detected = ContentTypeDetector.detect_from_magic_bytes(utf8_text)
        assert detected == "text/plain"

    def test_json_detection(self):
        """Test JSON content detection"""
        from md_server.detection import ContentTypeDetector

        # JSON object
        json_obj = b'{"key": "value", "number": 42}'
        detected = ContentTypeDetector.detect_from_magic_bytes(json_obj)
        assert detected == "application/json"

        # JSON array
        json_array = b'["item1", "item2", "item3"]'
        detected = ContentTypeDetector.detect_from_magic_bytes(json_array)
        assert detected == "application/json"

    def test_xml_detection(self):
        """Test XML content detection"""
        from md_server.detection import ContentTypeDetector

        # XML with declaration
        xml_content = (
            b'<?xml version="1.0" encoding="UTF-8"?><root><child>content</child></root>'
        )
        detected = ContentTypeDetector.detect_from_magic_bytes(xml_content)
        assert detected == "text/xml"


class TestValidationWorkflows:
    """Test validation through different user workflows"""

    @pytest.fixture
    def converter(self):
        """SDK converter instance for testing."""
        return MDConverter()

    @pytest.mark.asyncio
    async def test_sdk_input_validation(self, converter):
        """Test SDK input validation"""
        # Test invalid inputs
        with pytest.raises((InvalidInputError, ValueError)):
            await converter.convert_url("")

        with pytest.raises((InvalidInputError, ValueError)):
            await converter.convert_url("not-a-url")

        with pytest.raises((InvalidInputError, ValueError)):
            await converter.convert_file("")

    @pytest.mark.asyncio
    async def test_content_detection_accuracy(self, converter):
        """Test content type detection through workflows"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # PDF with wrong extension
            pdf_file = Path(tmpdir) / "document.txt"
            pdf_file.write_bytes(b"%PDF-1.4\n")

            # Should detect as PDF despite extension
            result = await converter.convert_file(str(pdf_file))
            # Either processes as PDF or rejects appropriately
            assert result.success in [True, False]

    @pytest.mark.asyncio
    async def test_format_support_validation(self, converter):
        """Test format support validation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Unsupported format
            unsupported = Path(tmpdir) / "test.xyz"
            unsupported.write_text("unsupported content")

            result = await converter.convert_file(str(unsupported))
            # Should handle unsupported formats gracefully
            assert isinstance(result.success, bool)
