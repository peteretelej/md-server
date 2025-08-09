import asyncio
import logging
from typing import Optional
from pathlib import Path
from io import BytesIO
from urllib.parse import urlparse

from markitdown import MarkItDown, StreamInfo
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig

from .core.config import Settings


class ConversionError(Exception):
    """Exception raised when conversion fails"""
    pass


def validate_url(url: str) -> str:
    """Validate and sanitize URL input"""
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("Invalid URL format")
    if parsed.scheme not in ["http", "https"]:
        raise ValueError("Only HTTP/HTTPS URLs allowed")
    return url


class UrlConverter:
    """Crawl4AI-based URL to markdown converter with proper resource management"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
    
    async def convert_url(self, url: str, enable_js: Optional[bool] = None) -> str:
        """Convert URL to markdown with proper resource cleanup"""
        validate_url(url)
        
        if not self.settings.crawl4ai_enabled:
            return await self._fallback_convert_url(url)
        
        enable_js = enable_js if enable_js is not None else self.settings.crawl4ai_js_rendering
        
        browser_config = BrowserConfig(
            browser_type="chromium",
            headless=True,
            proxy=self.settings.http_proxy,
            user_agent=self.settings.crawl4ai_user_agent,
            verbose=self.settings.debug
        )
        
        run_config = CrawlerRunConfig(
            page_timeout=self.settings.crawl4ai_timeout * 1000,
            cache_mode="bypass",
            remove_overlay_elements=True,
            word_count_threshold=10
        )
        
        try:
            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url, config=run_config)
                
                if not result.success:
                    logging.warning(f"Crawl4AI failed for {url}: {result.error_message}, falling back to MarkItDown")
                    return await self._fallback_convert_url(url)
                
                return result.markdown or ""
                
        except Exception as e:
            logging.warning(f"Crawl4AI conversion failed for {url}: {e}, falling back to MarkItDown")
            return await self._fallback_convert_url(url)
    
    async def _fallback_convert_url(self, url: str) -> str:
        """Fallback to MarkItDown for URL conversion"""
        try:
            converter = MarkItDown()
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, converter.convert, url)
            return result.markdown
        except Exception as e:
            logging.error(f"Both Crawl4AI and MarkItDown failed for {url}: {e}")
            raise ConversionError(f"Failed to convert URL: {str(e)}")


async def convert_content(
    converter: MarkItDown, content: bytes, filename: Optional[str] = None
) -> str:
    """Convert binary content to markdown using MarkItDown"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _sync_convert_content, converter, content, filename
    )


async def convert_url(converter: MarkItDown, url: str) -> str:
    """Convert URL content to markdown using MarkItDown (deprecated, use UrlConverter)"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_convert_url, converter, url)


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


def _sync_convert_url(converter: MarkItDown, url: str) -> str:
    """Synchronous URL conversion"""
    result = converter.convert(url)
    return result.markdown
