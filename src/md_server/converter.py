import asyncio
import logging
from typing import Optional
from pathlib import Path
from io import BytesIO

from markitdown import MarkItDown, StreamInfo
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig

from .core.config import Settings
from .security import URLValidator


def validate_url(url: str) -> str:
    """Validate URL input for document conversion"""
    return URLValidator.validate_url(url)


class UrlConverter:
    """URL to markdown converter with Crawl4AI and MarkItDown fallback"""

    def __init__(
        self,
        settings: Settings,
        browser_available: bool,
        markitdown_instance: MarkItDown,
    ):
        self.settings = settings
        self.browser_available = browser_available
        self.markitdown_instance = markitdown_instance

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
            result = self.markitdown_instance.convert(url)
            return result.markdown
        except Exception as e:
            logging.error(f"MarkItDown URL conversion failed for {url}: {e}")
            raise ValueError(f"Failed to convert URL: {str(e)}")


def create_converter_with_options(
    base_converter: MarkItDown, options: Optional[dict] = None
) -> MarkItDown:
    """Create a MarkItDown converter with specific options"""
    if not options:
        return base_converter

    # For now, we'll use the base converter since most options are constructor-level
    # In a full implementation, you might create new instances with different configurations
    return base_converter


async def convert_content(
    converter: MarkItDown,
    content: bytes,
    filename: Optional[str] = None,
    options: Optional[dict] = None,
) -> str:
    """Convert binary content to markdown using MarkItDown"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _sync_convert_content, converter, content, filename, options
    )


def _sync_convert_content(
    converter: MarkItDown,
    content: bytes,
    filename: Optional[str] = None,
    options: Optional[dict] = None,
) -> str:
    """Synchronous content conversion"""
    stream_info = None
    if filename:
        path = Path(filename)
        stream_info = StreamInfo(extension=path.suffix.lower(), filename=filename)

    # Apply conversion options
    kwargs = {}
    if options:
        # These options don't need to be passed to convert_stream as they're handled in MarkItDown constructor
        # We'll just apply basic processing options here
        pass

    with BytesIO(content) as stream:
        result = converter.convert_stream(stream, stream_info=stream_info, **kwargs)
        markdown = result.markdown

        # Apply post-processing options
        if options:
            if options.get("clean_markdown", False):
                markdown = _clean_markdown(markdown)
            if options.get("max_length") and len(markdown) > options["max_length"]:
                markdown = markdown[: options["max_length"]] + "..."

        return markdown


def _clean_markdown(markdown: str) -> str:
    """Clean and normalize markdown content"""
    if not markdown:
        return markdown

    # Basic cleaning operations
    lines = markdown.split("\n")
    cleaned_lines = []

    for line in lines:
        # Remove excessive whitespace
        line = line.strip()
        if line:
            cleaned_lines.append(line)
        elif cleaned_lines and cleaned_lines[-1] != "":
            # Keep single empty lines between content
            cleaned_lines.append("")

    # Remove trailing empty lines
    while cleaned_lines and cleaned_lines[-1] == "":
        cleaned_lines.pop()

    return "\n".join(cleaned_lines)
