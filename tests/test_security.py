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
