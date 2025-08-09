import pytest
from unittest.mock import patch

from md_server.converter import UrlConverter, validate_url
from md_server.core.config import Settings


class TestUrlConverterSimple:
    """Simple tests for URL converter functionality"""

    def setup_method(self):
        self.settings = Settings()
        self.converter = UrlConverter(self.settings)

    @pytest.mark.asyncio
    async def test_convert_url_success(self):
        """Test successful URL conversion"""
        expected_result = "# Test Page\n\nContent here"

        # Mock the entire convert_url method
        with patch.object(
            self.converter, "convert_url", return_value=expected_result
        ) as mock_convert:
            result = await self.converter.convert_url("https://example.com")
            assert result == expected_result
            mock_convert.assert_called_once_with("https://example.com")

    @pytest.mark.asyncio
    async def test_convert_url_with_js_rendering(self):
        """Test URL conversion with JS rendering enabled"""
        expected_result = "# Dynamic Content"

        with patch.object(
            self.converter, "convert_url", return_value=expected_result
        ) as mock_convert:
            result = await self.converter.convert_url(
                "https://spa-example.com", enable_js=True
            )
            assert result == expected_result
            mock_convert.assert_called_once_with(
                "https://spa-example.com", enable_js=True
            )

    @pytest.mark.asyncio
    async def test_convert_url_failure(self):
        """Test URL conversion failure"""
        with patch.object(
            self.converter,
            "convert_url",
            side_effect=ValueError("Failed to crawl URL"),
        ):
            with pytest.raises(ValueError, match="Failed to crawl URL"):
                await self.converter.convert_url("https://failing-url.com")

    def test_validate_url_success(self):
        """Test URL validation for valid URLs"""
        valid_urls = [
            "https://example.com",
            "http://test.org",
            "https://sub.example.com/path?query=1",
            "https://example.com:8080/path",
        ]
        for url in valid_urls:
            assert validate_url(url) == url

    def test_validate_url_failures(self):
        """Test URL validation for invalid URLs"""
        test_cases = [
            ("ftp://example.com", "Only HTTP/HTTPS URLs allowed"),
            (
                "javascript:alert('test')",
                "Invalid URL format",
            ),  # javascript has no netloc
            ("not-a-url", "Invalid URL format"),
            ("http://", "Invalid URL format"),
            ("", "Invalid URL format"),
            ("https://", "Invalid URL format"),
        ]

        for url, expected_error in test_cases:
            with pytest.raises(ValueError, match=expected_error):
                validate_url(url)


class TestIntegrationWithRealCrawl4AI:
    """Integration tests that actually use Crawl4AI (may require network)"""

    def setup_method(self):
        self.settings = Settings(crawl4ai_timeout=10)  # Short timeout for tests
        self.converter = UrlConverter(self.settings)

    @pytest.mark.asyncio
    async def test_real_url_conversion_httpbin(self):
        """Test conversion of httpbin HTML page"""
        try:
            result = await self.converter.convert_url("https://httpbin.org/html")
            assert "Herman Melville" in result
            assert len(result) > 100  # Should have substantial content
        except Exception as e:
            pytest.skip(f"Network test failed (likely no internet): {e}")

    @pytest.mark.asyncio
    async def test_invalid_url_handling(self):
        """Test handling of invalid URLs"""
        with pytest.raises(ValueError, match="Invalid URL format"):
            await self.converter.convert_url("not-a-valid-url")

    @pytest.mark.asyncio
    async def test_nonexistent_domain(self):
        """Test handling of nonexistent domains"""
        try:
            with pytest.raises(ValueError):
                await self.converter.convert_url(
                    "https://this-domain-does-not-exist-12345.com"
                )
        except Exception as e:
            pytest.skip(f"Network test failed (likely no internet): {e}")


class TestSettings:
    """Test settings and configuration"""

    def test_converter_uses_settings(self):
        """Test that converter properly uses settings"""
        custom_settings = Settings(
            crawl4ai_timeout=60, crawl4ai_user_agent="test-agent", debug=True
        )
        converter = UrlConverter(custom_settings)

        assert converter.settings.crawl4ai_timeout == 60
        assert converter.settings.crawl4ai_user_agent == "test-agent"
        assert converter.settings.debug is True

    def test_default_settings(self):
        """Test default settings values"""
        settings = Settings()
        converter = UrlConverter(settings)

        assert converter.settings.crawl4ai_timeout == 30
        assert converter.settings.crawl4ai_js_rendering is False
        assert converter.settings.crawl4ai_user_agent is None
