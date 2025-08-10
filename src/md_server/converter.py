import asyncio
import logging
from typing import Optional
from pathlib import Path
from io import BytesIO

from markitdown import MarkItDown, StreamInfo
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig

from .core.config import Settings
from .security import SSRFProtection


async def check_browser_availability() -> bool:
    """Check if Playwright browsers are available at startup"""
    try:
        browser_config = BrowserConfig(
            browser_type="chromium",
            headless=True,
            verbose=False,
        )

        # Quick test to see if browser can initialize
        async with AsyncWebCrawler(config=browser_config):
            # Don't actually crawl anything, just test initialization
            pass
        return True
    except Exception as e:
        error_str = str(e)
        if any(
            keyword in error_str.lower()
            for keyword in ["playwright", "browser", "executable", "chromium"]
        ):
            return False
        # Re-raise unexpected errors
        raise


def validate_url(url: str) -> str:
    """Validate and sanitize URL input with SSRF protection"""
    return SSRFProtection.validate_url(url)


class UrlConverter:
    """URL to markdown converter with Crawl4AI and MarkItDown fallback"""

    def __init__(self, settings: Settings, browser_available: bool):
        self.settings = settings
        self.browser_available = browser_available

    async def convert_url(self, url: str, enable_js: Optional[bool] = None) -> str:
        """Convert URL to markdown with browser or MarkItDown fallback"""
        validate_url(url)

        if self.browser_available:
            enable_js = (
                enable_js
                if enable_js is not None
                else self.settings.crawl4ai_js_rendering
            )
            return await self._crawl_with_browser(url, enable_js)
        else:
            # Fallback to MarkItDown URL conversion
            return await self._convert_with_markitdown(url)

    async def _crawl_with_browser(self, url: str, enable_js: bool) -> str:
        """Browser-based crawling with Playwright"""
        browser_config_kwargs = {
            "browser_type": "chromium",
            "headless": True,
            "proxy": self.settings.http_proxy,
            "verbose": self.settings.debug,
        }

        if self.settings.crawl4ai_user_agent:
            browser_config_kwargs["user_agent"] = self.settings.crawl4ai_user_agent

        browser_config = BrowserConfig(**browser_config_kwargs)

        run_config = CrawlerRunConfig(
            page_timeout=self.settings.crawl4ai_timeout * 1000,
            cache_mode="bypass",
            remove_overlay_elements=True,
            word_count_threshold=10,
        )

        try:
            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url, config=run_config)

                if not result.success:
                    raise ValueError(f"Failed to crawl {url}: {result.error_message}")

                return result.markdown or ""
        except Exception as e:
            logging.error(f"Crawl4AI browser crawling failed for {url}: {e}")
            raise ValueError(f"Failed to convert URL with browser: {str(e)}")

    async def _convert_with_markitdown(self, url: str) -> str:
        """Fallback URL conversion using MarkItDown"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._sync_convert_url_with_markitdown, url
        )

    def _sync_convert_url_with_markitdown(self, url: str) -> str:
        """Synchronous MarkItDown URL conversion"""
        try:
            # Use the existing MarkItDown instance from dependency injection
            from .app import provide_converter

            converter = provide_converter()
            result = converter.convert(url)
            return result.markdown
        except Exception as e:
            logging.error(f"MarkItDown URL conversion failed for {url}: {e}")
            raise ValueError(f"Failed to convert URL: {str(e)}")


async def convert_content(
    converter: MarkItDown, content: bytes, filename: Optional[str] = None
) -> str:
    """Convert binary content to markdown using MarkItDown"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _sync_convert_content, converter, content, filename
    )


def _sync_convert_content(
    converter: MarkItDown, content: bytes, filename: Optional[str] = None
) -> str:
    """Synchronous content conversion"""
    stream_info = None
    if filename:
        path = Path(filename)
        stream_info = StreamInfo(extension=path.suffix.lower(), filename=filename)

    with BytesIO(content) as stream:
        result = converter.convert_stream(stream, stream_info=stream_info)
        return result.markdown
