import logging
from crawl4ai import AsyncWebCrawler, BrowserConfig


class BrowserChecker:
    """Browser availability detection for Crawl4AI/Playwright"""

    @staticmethod
    async def is_available() -> bool:
        """Check if Playwright browsers are available"""
        try:
            browser_config = BrowserConfig(
                browser_type="chromium",
                headless=True,
                verbose=False,
            )

            async with AsyncWebCrawler(config=browser_config):
                pass
            return True
        except Exception as e:
            error_str = str(e)
            if any(
                keyword in error_str.lower()
                for keyword in ["playwright", "browser", "executable", "chromium"]
            ):
                return False
            raise

    @staticmethod
    def log_availability(available: bool) -> None:
        """Log browser availability status"""
        if available:
            logging.info(
                "URL Conversion: Using Crawl4AI with Playwright browsers (JavaScript support enabled)"
            )
        else:
            logging.warning(
                "WARNING: URL Conversion: Playwright browsers not available, using MarkItDown for basic URL conversions. Install Playwright for Crawl4AI with Javascript support. Please see https://github.com/peteretelej/md-server?tab=readme-ov-file#enhanced-url-conversion-optional"
            )
