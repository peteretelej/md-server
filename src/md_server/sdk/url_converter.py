"""
URL conversion functionality for the SDK.
"""

import asyncio
from typing import Optional

from markitdown import MarkItDown

from .config import get_logger
from .exceptions import NetworkError
from .validators import URLValidator

logger = get_logger("url_converter")


class URLConverter:
    """URL to markdown converter with MarkItDown and optional browser support."""

    def __init__(self, markitdown_instance: MarkItDown, timeout: int = 30):
        self.markitdown_instance = markitdown_instance
        self.timeout = timeout
        self._browser_available = self._check_browser_availability()

    def _check_browser_availability(self) -> bool:
        """Check if browser support (Crawl4AI) is available."""
        try:
            import importlib.util

            available = importlib.util.find_spec("crawl4ai") is not None
            if not available:
                logger.debug(
                    "Crawl4AI not available, using MarkItDown for URL conversion"
                )
            return available
        except ImportError:
            logger.debug("Crawl4AI not available, using MarkItDown for URL conversion")
            return False

    async def convert_url(self, url: str, js_rendering: Optional[bool] = None) -> str:
        """Convert URL to markdown with browser or MarkItDown fallback."""
        validated_url = URLValidator.validate_url(url)

        logger.info(
            "Converting URL: %s (browser_available=%s, js_rendering=%s)",
            validated_url,
            self._browser_available,
            js_rendering,
        )

        if self._browser_available and js_rendering:
            try:
                return await self._crawl_with_browser(validated_url)
            except Exception as e:
                logger.warning(
                    "Browser crawling failed, falling back to MarkItDown: %s", e
                )

        return await self._convert_with_markitdown(validated_url)

    async def _crawl_with_browser(self, url: str) -> str:
        """Browser-based crawling with Crawl4AI."""
        try:
            from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig
        except ImportError:
            raise NetworkError("Crawl4AI not available for browser-based conversion")

        browser_config = BrowserConfig(
            browser_type="chromium",
            headless=True,
            verbose=False,
        )

        run_config = CrawlerRunConfig(
            page_timeout=self.timeout * 1000,
            cache_mode="bypass",
            remove_overlay_elements=True,
            word_count_threshold=10,
        )

        try:
            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url, config=run_config)

                if not result.success:
                    raise NetworkError(f"Failed to crawl {url}: {result.error_message}")

                return result.markdown or ""
        except Exception as e:
            logger.error("Crawl4AI browser crawling failed for %s: %s", url, e)
            raise NetworkError(f"Failed to convert URL with browser: {str(e)}")

    async def _convert_with_markitdown(self, url: str) -> str:
        """Fallback URL conversion using MarkItDown."""
        loop = asyncio.get_event_loop()

        try:
            return await asyncio.wait_for(
                loop.run_in_executor(None, self._sync_convert_url_with_markitdown, url),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError:
            raise NetworkError(f"URL conversion timed out after {self.timeout}s")

    def _sync_convert_url_with_markitdown(self, url: str) -> str:
        """Synchronous MarkItDown URL conversion."""
        try:
            result = self.markitdown_instance.convert(url)
            return result.markdown
        except Exception as e:
            logger.error("MarkItDown URL conversion failed for %s: %s", url, e)
            raise NetworkError(f"Failed to convert URL: {str(e)}")
