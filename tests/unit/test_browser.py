import pytest
from unittest.mock import patch, AsyncMock
import logging
from md_server.browser import BrowserChecker


class TestBrowserChecker:
    @pytest.mark.asyncio
    async def test_is_available_success(self):
        """Test successful browser availability check"""
        with patch("md_server.browser.AsyncWebCrawler") as mock_crawler:
            mock_instance = AsyncMock()
            mock_crawler.return_value = mock_instance

            result = await BrowserChecker.is_available()

            assert result is True
            mock_crawler.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_available_playwright_error(self):
        """Test browser unavailable due to playwright error"""
        with patch("md_server.browser.AsyncWebCrawler") as mock_crawler:
            mock_crawler.side_effect = Exception("Playwright browser not found")

            result = await BrowserChecker.is_available()

            assert result is False

    @pytest.mark.asyncio
    async def test_is_available_browser_error(self):
        """Test browser unavailable due to browser error"""
        with patch("md_server.browser.AsyncWebCrawler") as mock_crawler:
            mock_crawler.side_effect = Exception("Browser executable not found")

            result = await BrowserChecker.is_available()

            assert result is False

    @pytest.mark.asyncio
    async def test_is_available_chromium_error(self):
        """Test browser unavailable due to chromium error"""
        with patch("md_server.browser.AsyncWebCrawler") as mock_crawler:
            mock_crawler.side_effect = Exception("Chromium download failed")

            result = await BrowserChecker.is_available()

            assert result is False

    @pytest.mark.asyncio
    async def test_is_available_unexpected_error(self):
        """Test unexpected error is re-raised"""
        with patch("md_server.browser.AsyncWebCrawler") as mock_crawler:
            mock_crawler.side_effect = Exception("Network connection failed")

            with pytest.raises(Exception, match="Network connection failed"):
                await BrowserChecker.is_available()

    @pytest.mark.asyncio
    async def test_is_available_case_insensitive_matching(self):
        """Test case insensitive error keyword matching"""
        with patch("md_server.browser.AsyncWebCrawler") as mock_crawler:
            mock_crawler.side_effect = Exception("PLAYWRIGHT not installed")

            result = await BrowserChecker.is_available()

            assert result is False

    def test_log_availability_true(self, caplog):
        """Test logging when browser is available"""
        with caplog.at_level(logging.INFO):
            BrowserChecker.log_availability(True)

        assert "URL Conversion: Using Crawl4AI with Playwright browsers" in caplog.text
        assert "JavaScript support enabled" in caplog.text

    def test_log_availability_false(self, caplog):
        """Test logging when browser is not available"""
        with caplog.at_level(logging.WARNING):
            BrowserChecker.log_availability(False)

        assert (
            "WARNING: URL Conversion: Playwright browsers not available" in caplog.text
        )
        assert "Install Playwright for Crawl4AI" in caplog.text
        assert "peteretelej/md-server" in caplog.text
