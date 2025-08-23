import pytest
from unittest.mock import patch, AsyncMock
from md_server.browser import BrowserChecker


class TestBrowserAvailabilityDetection:
    """Test browser availability detection scenarios"""

    @pytest.mark.asyncio
    async def test_playwright_import_failure(self):
        """Test behavior when Playwright import fails"""
        with patch("md_server.browser.AsyncWebCrawler", side_effect=ImportError("playwright module not found")):
            result = await BrowserChecker.is_available()
            assert result is False

    @pytest.mark.asyncio 
    async def test_browser_executable_missing(self):
        """Test behavior when browser executable is missing"""
        with patch("md_server.browser.AsyncWebCrawler", side_effect=Exception("Browser executable not found")):
            result = await BrowserChecker.is_available()
            assert result is False

    @pytest.mark.asyncio
    async def test_playwright_browser_error(self):
        """Test behavior when Playwright browser fails"""
        with patch("md_server.browser.AsyncWebCrawler", side_effect=Exception("playwright browser initialization failed")):
            result = await BrowserChecker.is_available()
            assert result is False

    @pytest.mark.asyncio
    async def test_chromium_not_found(self):
        """Test behavior when Chromium browser not found"""
        with patch("md_server.browser.AsyncWebCrawler", side_effect=Exception("chromium binary not available")):
            result = await BrowserChecker.is_available()
            assert result is False

    @pytest.mark.asyncio
    async def test_generic_browser_exception(self):
        """Test behavior with generic browser-related exceptions"""
        with patch("md_server.browser.AsyncWebCrawler", side_effect=Exception("browser setup failed")):
            result = await BrowserChecker.is_available()
            assert result is False

    @pytest.mark.asyncio
    async def test_successful_browser_detection(self):
        """Test successful browser detection"""
        with patch("md_server.browser.AsyncWebCrawler") as mock_crawler_class:
            mock_crawler_class.return_value.__aenter__.return_value = AsyncMock()
            mock_crawler_class.return_value.__aexit__.return_value = None
            
            result = await BrowserChecker.is_available()
            assert result is True

    @pytest.mark.asyncio
    async def test_non_browser_exception_raised(self):
        """Test that non-browser exceptions are re-raised"""
        with patch("md_server.browser.AsyncWebCrawler", side_effect=ValueError("Unexpected error")):
            with pytest.raises(ValueError, match="Unexpected error"):
                await BrowserChecker.is_available()

    @pytest.mark.asyncio
    async def test_browser_config_creation(self):
        """Test browser configuration is created correctly"""
        with patch("md_server.browser.BrowserConfig") as mock_config:
            with patch("md_server.browser.AsyncWebCrawler") as mock_crawler_class:
                mock_crawler_class.return_value.__aenter__.return_value = AsyncMock()
                mock_crawler_class.return_value.__aexit__.return_value = None
                
                await BrowserChecker.is_available()
                
                mock_config.assert_called_once_with(
                    browser_type="chromium",
                    headless=True,
                    verbose=False,
                )

    @pytest.mark.asyncio
    async def test_context_manager_usage(self):
        """Test that AsyncWebCrawler is used as context manager"""
        with patch("md_server.browser.AsyncWebCrawler") as mock_crawler_class:
            mock_enter = AsyncMock(return_value=AsyncMock())
            mock_exit = AsyncMock(return_value=None)
            mock_crawler_class.return_value.__aenter__ = mock_enter
            mock_crawler_class.return_value.__aexit__ = mock_exit
            
            result = await BrowserChecker.is_available()
            
            assert result is True
            mock_enter.assert_called_once()
            mock_exit.assert_called_once()

    @pytest.mark.asyncio
    async def test_exception_error_string_matching(self):
        """Test exception error string matching logic"""
        # Test each keyword that triggers browser unavailability
        keywords = ["playwright", "browser", "executable", "chromium"]
        
        for keyword in keywords:
            error_msg = f"Error: {keyword} failed to initialize"
            with patch("md_server.browser.AsyncWebCrawler", side_effect=Exception(error_msg)):
                result = await BrowserChecker.is_available()
                assert result is False, f"Should return False for error containing '{keyword}'"
        
        # Test case insensitive matching
        with patch("md_server.browser.AsyncWebCrawler", side_effect=Exception("BROWSER NOT FOUND")):
            result = await BrowserChecker.is_available()
            assert result is False

    @pytest.mark.asyncio
    async def test_context_manager_exception_during_exit(self):
        """Test behavior when context manager exit fails"""
        with patch("md_server.browser.AsyncWebCrawler") as mock_crawler_class:
            mock_crawler_class.return_value.__aenter__.return_value = AsyncMock()
            mock_crawler_class.return_value.__aexit__.side_effect = Exception("browser cleanup failed")
            
            result = await BrowserChecker.is_available()
            assert result is False