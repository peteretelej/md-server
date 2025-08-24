import pytest
from unittest.mock import patch, AsyncMock

from md_server.core.browser import BrowserChecker


class TestBrowserChecker:
    @pytest.mark.asyncio
    async def test_is_available_success(self):
        with patch("md_server.core.browser.AsyncWebCrawler") as mock_crawler:
            mock_crawler.return_value.__aenter__ = AsyncMock()
            mock_crawler.return_value.__aexit__ = AsyncMock()

            result = await BrowserChecker.is_available()
            assert result is True

    @pytest.mark.asyncio
    async def test_is_available_playwright_error(self):
        with patch("md_server.core.browser.AsyncWebCrawler") as mock_crawler:
            mock_crawler.side_effect = Exception("playwright executable not found")

            result = await BrowserChecker.is_available()
            assert result is False

    @pytest.mark.asyncio
    async def test_is_available_browser_error(self):
        with patch("md_server.core.browser.AsyncWebCrawler") as mock_crawler:
            mock_crawler.side_effect = Exception("browser not found")

            result = await BrowserChecker.is_available()
            assert result is False

    @pytest.mark.asyncio
    async def test_is_available_chromium_error(self):
        with patch("md_server.core.browser.AsyncWebCrawler") as mock_crawler:
            mock_crawler.side_effect = Exception("chromium executable missing")

            result = await BrowserChecker.is_available()
            assert result is False

    @pytest.mark.asyncio
    async def test_is_available_generic_error_raises(self):
        with patch("md_server.core.browser.AsyncWebCrawler") as mock_crawler:
            mock_crawler.side_effect = Exception("some other error")

            with pytest.raises(Exception, match="some other error"):
                await BrowserChecker.is_available()

    def test_log_availability_available(self):
        with patch("md_server.core.browser.logging.info") as mock_info:
            BrowserChecker.log_availability(True)
            mock_info.assert_called_once()
            args = mock_info.call_args[0]
            assert "Crawl4AI with Playwright browsers" in args[0]

    def test_log_availability_unavailable(self):
        with patch("md_server.core.browser.logging.warning") as mock_warning:
            BrowserChecker.log_availability(False)
            mock_warning.assert_called_once()
            args = mock_warning.call_args[0]
            assert "WARNING" in args[0]
            assert "MarkItDown for basic URL conversions" in args[0]
