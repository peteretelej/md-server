"""
URL conversion functionality for the SDK.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Optional, List

from markitdown import MarkItDown

from .config import get_logger
from .exceptions import NetworkError
from .validators import URLValidator

logger = get_logger("url_converter")


class BrowserDetector:
    """Detects browser availability for URL conversion."""

    def __init__(self):
        self._browser_available = self._check_browser_availability()

    def is_available(self) -> bool:
        """Check if browser support is available."""
        return self._browser_available

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


class ConversionStrategy(ABC):
    """Abstract base class for URL conversion strategies."""

    @abstractmethod
    async def convert(self, url: str) -> str:
        """Convert URL to markdown."""
        pass

    @abstractmethod
    def can_handle(self, url: str, js_rendering: Optional[bool] = None) -> bool:
        """Check if this strategy can handle the URL."""
        pass


class BrowserStrategy(ConversionStrategy):
    """Browser-based URL conversion strategy using Crawl4AI."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    async def convert(self, url: str) -> str:
        """Convert URL using browser rendering."""
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

    def can_handle(self, url: str, js_rendering: Optional[bool] = None) -> bool:
        """Check if browser strategy can handle this request."""
        return js_rendering is True


class FallbackStrategy(ConversionStrategy):
    """Fallback URL conversion strategy using MarkItDown."""

    def __init__(self, markitdown_instance: MarkItDown, timeout: int = 30):
        self.markitdown_instance = markitdown_instance
        self.timeout = timeout

    async def convert(self, url: str) -> str:
        """Convert URL using MarkItDown fallback."""
        loop = asyncio.get_event_loop()

        try:
            return await asyncio.wait_for(
                loop.run_in_executor(None, self._sync_convert_url, url),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError:
            raise NetworkError(f"URL conversion timed out after {self.timeout}s")

    def can_handle(self, url: str, js_rendering: Optional[bool] = None) -> bool:
        """Fallback strategy can always handle URLs."""
        return True

    def _sync_convert_url(self, url: str) -> str:
        """Synchronous MarkItDown URL conversion."""
        try:
            result = self.markitdown_instance.convert(url)
            return result.markdown
        except Exception as e:
            logger.error("MarkItDown URL conversion failed for %s: %s", url, e)
            raise NetworkError(f"Failed to convert URL: {str(e)}")


class StrategyManager:
    """Manages conversion strategy selection and execution."""

    def __init__(self, strategies: List[ConversionStrategy]):
        self.strategies = strategies

    async def convert_url(self, url: str, js_rendering: Optional[bool] = None) -> str:
        """Convert URL using the first available strategy."""
        for strategy in self.strategies:
            if strategy.can_handle(url, js_rendering):
                try:
                    return await strategy.convert(url)
                except Exception as e:
                    logger.warning(
                        "Strategy %s failed for %s: %s",
                        strategy.__class__.__name__,
                        url,
                        e,
                    )
                    continue

        raise NetworkError(f"All conversion strategies failed for {url}")


class URLConverter:
    """URL to markdown converter with MarkItDown and optional browser support."""

    def __init__(self, markitdown_instance: MarkItDown, timeout: int = 30):
        self.markitdown_instance = markitdown_instance
        self.timeout = timeout
        self._browser_detector = BrowserDetector()
        self._strategy_manager = self._create_strategy_manager()

    def _create_strategy_manager(self) -> StrategyManager:
        """Create strategy manager with available strategies."""
        strategies = []

        # Add browser strategy if available
        if self._browser_detector.is_available():
            strategies.append(BrowserStrategy(timeout=self.timeout))

        # Always add fallback strategy
        strategies.append(
            FallbackStrategy(self.markitdown_instance, timeout=self.timeout)
        )

        return StrategyManager(strategies)

    async def convert_url(self, url: str, js_rendering: Optional[bool] = None) -> str:
        """Convert URL to markdown with browser or MarkItDown fallback."""
        validated_url = URLValidator.validate_url(url)

        logger.info(
            "Converting URL: %s (browser_available=%s, js_rendering=%s)",
            validated_url,
            self._browser_detector.is_available(),
            js_rendering,
        )

        return await self._strategy_manager.convert_url(validated_url, js_rendering)

    # Backward compatibility properties
    @property
    def _browser_available(self) -> bool:
        """Backward compatibility property."""
        return self._browser_detector.is_available()

    async def _crawl_with_browser(self, url: str) -> str:
        """Backward compatibility method - delegates to browser strategy."""
        browser_strategy = BrowserStrategy(timeout=self.timeout)
        return await browser_strategy.convert(url)

    async def _convert_with_markitdown(self, url: str) -> str:
        """Backward compatibility method - delegates to fallback strategy."""
        fallback_strategy = FallbackStrategy(
            self.markitdown_instance, timeout=self.timeout
        )
        return await fallback_strategy.convert(url)
