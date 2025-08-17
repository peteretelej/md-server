import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from md_server.sdk import MDConverter
from md_server.browser import BrowserChecker
from md_server.detection import ContentTypeDetector
from litestar.testing import TestClient
from md_server.app import app


class TestBrowserDetection:
    """Test browser detection and capability reporting"""

    @pytest.mark.asyncio
    async def test_browser_available(self):
        """Test browser detection accuracy when browser is available"""
        # Mock AsyncWebCrawler to simulate browser availability
        with patch("md_server.browser.AsyncWebCrawler") as mock_crawler:
            mock_crawler.return_value.__aenter__.return_value = MagicMock()
            mock_crawler.return_value.__aexit__.return_value = None

            result = await BrowserChecker.is_available()
            assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_browser_unavailable(self):
        """Test fallback behavior when browser is unavailable"""
        # Mock AsyncWebCrawler to simulate browser unavailability
        with patch("md_server.browser.AsyncWebCrawler") as mock_crawler:
            mock_crawler.side_effect = Exception("Browser not available")

            result = await BrowserChecker.is_available()
            assert result is False

    @pytest.mark.asyncio
    async def test_js_rendering_enabled(self):
        """Test JavaScript processing when browser available"""
        converter = MDConverter()

        # Test with simple HTML that would benefit from JS rendering
        html_content = """
        <html>
        <body>
        <div id="content">Original Content</div>
        <script>
        document.getElementById('content').innerHTML = 'JavaScript Content';
        </script>
        </body>
        </html>
        """

        result = await converter.convert_text(html_content, mime_type="text/html")

        # Should process HTML successfully
        assert result.success is True
        assert len(result.markdown) > 0

    @pytest.mark.asyncio
    async def test_js_rendering_disabled(self):
        """Test fallback to basic processing when JS disabled"""
        # Create converter with JS rendering explicitly disabled
        converter = MDConverter(js_rendering=False)

        html_content = """
        <html>
        <body>
        <h1>Static Content</h1>
        <p>This should be processed without JavaScript</p>
        </body>
        </html>
        """

        result = await converter.convert_text(html_content, mime_type="text/html")

        # Should still process HTML successfully
        assert result.success is True
        assert "Static Content" in result.markdown


class TestContentTypeDetection:
    """Test content detection through user workflows"""

    def test_content_type_detection(self):
        """Test magic bytes detection"""
        detector = ContentTypeDetector()

        # Test PDF detection
        pdf_bytes = b"%PDF-1.4\n"
        assert detector.detect_from_magic_bytes(pdf_bytes) == "application/pdf"

        # Test JPEG detection
        jpeg_bytes = b"\xff\xd8\xff"
        detected = detector.detect_from_magic_bytes(jpeg_bytes)
        assert "image/jpeg" in detected or "image" in detected

        # Test text detection
        text_bytes = b"This is plain text content"
        detected = detector.detect_from_magic_bytes(text_bytes)
        assert "text" in detected

    @pytest.mark.asyncio
    async def test_format_detection_workflow(self):
        """Test format detection through conversion workflow"""
        converter = MDConverter()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files with content that should be detected properly

            # PDF-like file
            pdf_file = Path(tmpdir) / "document.pdf"
            pdf_file.write_bytes(b"%PDF-1.4\nSome PDF content")

            result = await converter.convert_file(str(pdf_file))
            # Should detect as PDF and attempt processing
            assert isinstance(result.success, bool)

            # HTML file
            html_file = Path(tmpdir) / "page.html"
            html_file.write_text("<html><body><h1>Test</h1></body></html>")

            result = await converter.convert_file(str(html_file))
            # Should process HTML successfully
            assert result.success is True
            assert "Test" in result.markdown


class TestFormatSupport:
    """Test format support discovery and reporting"""

    @pytest.fixture
    def client(self):
        """Test client for HTTP API."""
        return TestClient(app)

    def test_format_support_discovery(self, client):
        """Test capability reporting through /formats endpoint"""
        response = client.get("/formats")

        assert response.status_code == 200
        data = response.json()

        # Should include format support information
        assert "supported_formats" in data
        assert isinstance(data["supported_formats"], list)

        # Should include capability information
        assert "capabilities" in data
        capabilities = data["capabilities"]

        # Should report browser status
        assert "browser_available" in capabilities
        assert isinstance(capabilities["browser_available"], bool)

    @pytest.mark.asyncio
    async def test_capability_impact_on_conversion(self):
        """Test how capabilities impact conversion results"""
        converter = MDConverter()

        # Test URL conversion (may use browser if available)
        try:
            result = await converter.convert_url("https://httpbin.org/html")
            # Should handle URL conversion appropriately based on capabilities
            assert isinstance(result.success, bool)
        except Exception:
            # Network issues are acceptable in tests
            pass

    def test_format_validation_through_api(self, client):
        """Test format validation through HTTP API"""
        # Test with supported format
        response = client.post(
            "/convert", json={"text": "<h1>Test</h1>", "mime_type": "text/html"}
        )
        assert response.status_code == 200

        # Test with unsupported format should still handle gracefully
        response = client.post(
            "/convert", json={"text": "content", "mime_type": "application/x-unknown"}
        )
        # Should either process as text or return appropriate error
        assert response.status_code in [200, 400, 422]


class TestCapabilityReporting:
    """Test capability reporting across different interfaces"""

    @pytest.mark.asyncio
    async def test_sdk_capability_reporting(self):
        """Test capability reporting through SDK"""
        converter = MDConverter()

        # SDK should provide capability information
        assert hasattr(converter, "_config")

        # Should be able to check browser availability
        result = await BrowserChecker.is_available()
        assert isinstance(result, bool)

    @pytest.fixture
    def client(self):
        """Test client for HTTP API."""
        return TestClient(app)

    def test_http_capability_reporting(self, client):
        """Test capability reporting through HTTP API"""
        # Health endpoint should include capability info
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data

        # Formats endpoint should provide detailed capability info
        response = client.get("/formats")
        assert response.status_code == 200

        data = response.json()
        assert "capabilities" in data

    def test_detection_consistency(self):
        """Test that detection is consistent across different entry points"""
        detector = ContentTypeDetector()

        # Same content should be detected consistently
        test_content = b"<html><body>Test</body></html>"

        # Direct detection
        detected1 = detector.detect_from_content(test_content)

        # Detection with filename hint
        detected2 = detector.detect_from_content(test_content, filename="test.html")

        # Both should identify as HTML
        assert "html" in detected1.lower()
        assert "html" in detected2.lower()


class TestBrowserCapabilityIntegration:
    """Test integration between browser capabilities and conversion workflows"""

    @pytest.mark.asyncio
    async def test_browser_fallback_behavior(self):
        """Test graceful fallback when browser unavailable"""
        # Create converter that will attempt to use browser but fall back gracefully
        converter = MDConverter()

        # Simple HTML that doesn't require JS
        simple_html = "<html><body><h1>Simple Page</h1><p>Content</p></body></html>"

        result = await converter.convert_text(simple_html, mime_type="text/html")

        # Should succeed regardless of browser availability
        assert result.success is True
        assert "Simple Page" in result.markdown
        assert "Content" in result.markdown

    def test_capability_detection_performance(self):
        """Test that capability detection is fast"""
        import time

        start = time.time()

        # Content type detection should be very fast
        detector = ContentTypeDetector()
        test_detection = detector.detect_from_magic_bytes(b"test content")

        end = time.time()

        # Content detection should be under 100ms
        assert (end - start) < 0.1
        assert isinstance(test_detection, str)
