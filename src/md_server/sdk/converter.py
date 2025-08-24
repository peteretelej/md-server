import asyncio
from pathlib import Path
from typing import Optional, Union

from ..core.converter import DocumentConverter
from ..models import ConversionResult


class MDConverter:
    """Simplified local document converter for SDK use."""

    def __init__(
        self,
        ocr_enabled: bool = False,
        js_rendering: bool = False,
        timeout: int = 30,
        max_file_size_mb: int = 50,
        extract_images: bool = False,
        preserve_formatting: bool = False,
        clean_markdown: bool = True,
    ):
        self._converter = DocumentConverter(
            ocr_enabled=ocr_enabled,
            js_rendering=js_rendering,
            timeout=timeout,
            max_file_size_mb=max_file_size_mb,
            extract_images=extract_images,
            preserve_formatting=preserve_formatting,
            clean_markdown=clean_markdown,
        )

    async def convert_file(
        self, file_path: Union[str, Path], **options
    ) -> ConversionResult:
        """Convert a local file to markdown."""
        return await self._converter.convert_file(file_path, **options)

    async def convert_url(self, url: str, **options) -> ConversionResult:
        """Convert URL content to markdown."""
        return await self._converter.convert_url(url, **options)

    async def convert_content(
        self, content: bytes, filename: Optional[str] = None, **options
    ) -> ConversionResult:
        """Convert binary content to markdown."""
        return await self._converter.convert_content(content, filename, **options)

    async def convert_text(
        self, text: str, mime_type: str = "text/plain", **options
    ) -> ConversionResult:
        """Convert text content to markdown."""
        return await self._converter.convert_text(text, mime_type, **options)

    def convert_file_sync(
        self, file_path: Union[str, Path], **options
    ) -> ConversionResult:
        """Synchronous version of convert_file."""
        return asyncio.run(self.convert_file(file_path, **options))

    def convert_url_sync(self, url: str, **options) -> ConversionResult:
        """Synchronous version of convert_url."""
        return asyncio.run(self.convert_url(url, **options))

    def convert_content_sync(
        self, content: bytes, filename: Optional[str] = None, **options
    ) -> ConversionResult:
        """Synchronous version of convert_content."""
        return asyncio.run(self.convert_content(content, filename, **options))

    def convert_text_sync(
        self, text: str, mime_type: str = "text/plain", **options
    ) -> ConversionResult:
        """Synchronous version of convert_text."""
        return asyncio.run(self.convert_text(text, mime_type, **options))

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        pass

    def __enter__(self):
        """Sync context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        pass
