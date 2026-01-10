import asyncio
import time
from io import BytesIO
from pathlib import Path
from typing import Optional, Dict, Any, Union

from markitdown import MarkItDown, StreamInfo

from .config import get_logger, get_settings
from ..metadata import MetadataExtractor
from ..models import ConversionResult, ConversionMetadata
from ..security import validate_url

logger = get_logger("core.converter")


class DocumentConverter:
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
        self.ocr_enabled = ocr_enabled
        self.js_rendering = js_rendering
        self.timeout = timeout
        self.max_file_size_mb = max_file_size_mb
        self.extract_images = extract_images
        self.preserve_formatting = preserve_formatting
        self.clean_markdown = clean_markdown

        self._markitdown = MarkItDown()
        self._browser_available = self._check_browser_availability()
        self._metadata_extractor = MetadataExtractor()

    def _check_browser_availability(self) -> bool:
        try:
            import importlib.util

            return importlib.util.find_spec("crawl4ai") is not None
        except ImportError:
            return False

    async def convert_file(
        self, file_path: Union[str, Path], **options
    ) -> ConversionResult:
        start_time = time.time()
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        file_size = path.stat().st_size
        if file_size > self.max_file_size_mb * 1024 * 1024:
            raise ValueError(
                f"File too large: {file_size} bytes (max {self.max_file_size_mb}MB)"
            )

        content = path.read_bytes()
        filename = path.name

        detected_format = self._detect_format(content, filename)

        if detected_format == "application/octet-stream":
            if content.startswith(b"MZ"):
                markdown = f"**Executable file detected**: {filename}\n\nThis appears to be an executable file and cannot be converted to text. Executable files are not supported for conversion."
            else:
                markdown = f"**Binary file detected**: {filename}\n\nThis appears to be a binary file and cannot be converted to text. Binary files are not supported for conversion."
        else:
            markdown = await self._convert_content_async(content, filename, options)

        include_frontmatter = options.get("include_frontmatter", False)
        if include_frontmatter:
            markdown, extracted = self._metadata_extractor.with_frontmatter(
                markdown,
                source=filename,
                source_type=self._get_simple_type(detected_format),
            )
        else:
            extracted = self._metadata_extractor.extract(markdown)

        processing_time = time.time() - start_time

        metadata = ConversionMetadata(
            source_type="file",
            source_size=file_size,
            markdown_size=len(markdown),
            conversion_time_ms=int(processing_time * 1000),
            detected_format=detected_format,
            title=extracted.title,
            estimated_tokens=extracted.estimated_tokens,
            detected_language=extracted.detected_language,
        )

        return ConversionResult(
            success=True,
            markdown=markdown,
            metadata=metadata,
        )

    async def convert_url(self, url: str, **options) -> ConversionResult:
        start_time = time.time()

        # SSRF validation - check URL doesn't target blocked networks
        settings = get_settings()
        validate_url(
            url,
            allow_localhost=settings.allow_localhost,
            allow_private_networks=settings.allow_private_networks,
        )

        self._validate_url(url)

        js_rendering = options.get("js_rendering", self.js_rendering)

        if js_rendering and self._browser_available:
            markdown = await self._crawl_with_browser(url)
            source_size = len(markdown)
        else:
            markdown = await self._convert_url_with_markitdown(url)
            source_size = len(markdown)

        include_frontmatter = options.get("include_frontmatter", False)
        if include_frontmatter:
            markdown, extracted = self._metadata_extractor.with_frontmatter(
                markdown,
                source=url,
                source_type="html",
            )
        else:
            extracted = self._metadata_extractor.extract(markdown)

        processing_time = time.time() - start_time

        metadata = ConversionMetadata(
            source_type="url",
            source_size=source_size,
            markdown_size=len(markdown),
            conversion_time_ms=int(processing_time * 1000),
            detected_format="text/html",
            title=extracted.title,
            estimated_tokens=extracted.estimated_tokens,
            detected_language=extracted.detected_language,
        )

        return ConversionResult(
            success=True,
            markdown=markdown,
            metadata=metadata,
        )

    async def convert_content(
        self, content: bytes, filename: Optional[str] = None, **options
    ) -> ConversionResult:
        start_time = time.time()

        content_size = len(content)
        if content_size > self.max_file_size_mb * 1024 * 1024:
            raise ValueError(
                f"Content too large: {content_size} bytes (max {self.max_file_size_mb}MB)"
            )

        detected_format = self._detect_format(content, filename)
        markdown = await self._convert_content_async(content, filename, options)

        include_frontmatter = options.get("include_frontmatter", False)
        if include_frontmatter:
            markdown, extracted = self._metadata_extractor.with_frontmatter(
                markdown,
                source=filename,
                source_type=self._get_simple_type(detected_format),
            )
        else:
            extracted = self._metadata_extractor.extract(markdown)

        processing_time = time.time() - start_time

        metadata = ConversionMetadata(
            source_type="content",
            source_size=content_size,
            markdown_size=len(markdown),
            conversion_time_ms=int(processing_time * 1000),
            detected_format=detected_format,
            title=extracted.title,
            estimated_tokens=extracted.estimated_tokens,
            detected_language=extracted.detected_language,
        )

        return ConversionResult(
            success=True,
            markdown=markdown,
            metadata=metadata,
        )

    async def convert_text(
        self, text: str, mime_type: str, **options
    ) -> ConversionResult:
        start_time = time.time()

        text_size = len(text)

        if mime_type == "text/markdown":
            markdown = text
        else:
            markdown = await self._convert_text_with_mime_type_async(
                text, mime_type, options
            )

        if self.clean_markdown:
            markdown = self._clean_markdown(markdown)

        include_frontmatter = options.get("include_frontmatter", False)
        if include_frontmatter:
            markdown, extracted = self._metadata_extractor.with_frontmatter(
                markdown,
                source=None,
                source_type=self._get_simple_type(mime_type),
            )
        else:
            extracted = self._metadata_extractor.extract(markdown)

        processing_time = time.time() - start_time

        metadata = ConversionMetadata(
            source_type="text",
            source_size=text_size,
            markdown_size=len(markdown),
            conversion_time_ms=int(processing_time * 1000),
            detected_format=mime_type,
            title=extracted.title,
            estimated_tokens=extracted.estimated_tokens,
            detected_language=extracted.detected_language,
        )

        return ConversionResult(
            success=True,
            markdown=markdown,
            metadata=metadata,
        )

    async def _convert_content_async(
        self,
        content: bytes,
        filename: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._sync_convert_content, content, filename, options
        )

    async def _convert_text_with_mime_type_async(
        self, text: str, mime_type: str, options: Optional[Dict[str, Any]] = None
    ) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._sync_convert_text_with_mime_type, text, mime_type, options
        )

    async def _convert_url_with_markitdown(self, url: str) -> str:
        loop = asyncio.get_event_loop()
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(None, self._sync_convert_url, url),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"URL conversion timed out after {self.timeout}s")

    async def _crawl_with_browser(self, url: str) -> str:
        try:
            from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig
        except ImportError:
            raise ImportError("Crawl4AI not available for browser-based conversion")

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
                    raise Exception(f"Failed to crawl {url}: {result.error_message}")

                return result.markdown or ""
        except Exception as e:
            logger.error("Crawl4AI browser crawling failed for %s: %s", url, e)
            raise Exception(f"Failed to convert URL with browser: {str(e)}")

    def _sync_convert_content(
        self,
        content: bytes,
        filename: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> str:
        stream_info = self._create_stream_info_for_content(filename)

        with BytesIO(content) as stream:
            result = self._markitdown.convert_stream(stream, stream_info=stream_info)
            markdown = result.markdown

            return self._apply_options(markdown, options)

    def _sync_convert_text_with_mime_type(
        self, text: str, mime_type: str, options: Optional[Dict[str, Any]] = None
    ) -> str:
        text_bytes = text.encode("utf-8")
        stream_info = StreamInfo(mimetype=mime_type)

        with BytesIO(text_bytes) as stream:
            result = self._markitdown.convert_stream(stream, stream_info=stream_info)
            markdown = result.markdown

            return self._apply_options(markdown, options)

    def _sync_convert_url(self, url: str) -> str:
        try:
            result = self._markitdown.convert(url)
            return result.markdown
        except Exception as e:
            logger.error("MarkItDown URL conversion failed for %s: %s", url, e)
            raise Exception(f"Failed to convert URL: {str(e)}")

    def _create_stream_info_for_content(
        self, filename: Optional[str]
    ) -> Optional[StreamInfo]:
        if not filename:
            return None

        path = Path(filename)
        return StreamInfo(extension=path.suffix.lower(), filename=filename)

    def _apply_options(self, markdown: str, options: Optional[Dict[str, Any]]) -> str:
        if not options:
            return markdown

        if options.get("clean_markdown", self.clean_markdown):
            markdown = self._clean_markdown(markdown)

        if options.get("max_length") and len(markdown) > options["max_length"]:
            markdown = markdown[: options["max_length"]] + "..."

        return markdown

    def _detect_format(self, content: bytes, filename: Optional[str] = None) -> str:
        format_map = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".html": "text/html",
            ".htm": "text/html",
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".json": "application/json",
            ".xml": "application/xml",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".wav": "audio/wav",
            ".mp3": "audio/mp3",
        }

        if content.startswith(b"%PDF"):
            return "application/pdf"
        elif content.startswith(b"PK"):
            return "application/zip"
        elif content.startswith(b"<"):
            prefix = content[:1024].lower()
            if b"<html" in prefix:
                return "text/html"
            elif b"<?xml" in prefix:
                return "application/xml"
        elif content.startswith(b"\x89PNG"):
            return "image/png"
        elif content.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        elif content.startswith(b"GIF8"):
            return "image/gif"
        elif content.startswith(b"RIFF"):
            return "audio/wav"
        elif content.startswith(b"\xff\xfb") or content.startswith(b"ID3"):
            return "audio/mp3"

        if b"\x00" in content:
            return "application/octet-stream"

        if filename:
            suffix = Path(filename).suffix.lower()
            if suffix in format_map:
                return format_map[suffix]

        try:
            content[:1024].decode("utf-8")
            return "text/plain"
        except UnicodeDecodeError:
            return "application/octet-stream"

    def _validate_url(self, url: str) -> str:
        if not url or not isinstance(url, str):
            raise ValueError("URL must be a non-empty string")

        url = url.strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")

        return url

    def _clean_markdown(self, markdown: str) -> str:
        if not markdown:
            return markdown

        lines = markdown.split("\n")
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            if line:
                cleaned_lines.append(line)
            elif cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")

        while cleaned_lines and cleaned_lines[-1] == "":
            cleaned_lines.pop()

        return "\n".join(cleaned_lines)

    def _get_simple_type(self, mime_type: str) -> str:
        """Convert MIME type to simple type name for frontmatter."""
        type_map = {
            "application/pdf": "pdf",
            "text/html": "html",
            "text/plain": "text",
            "text/markdown": "markdown",
            "application/json": "json",
            "application/xml": "xml",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
            "image/png": "png",
            "image/jpeg": "jpeg",
            "image/gif": "gif",
            "audio/wav": "wav",
            "audio/mp3": "mp3",
        }
        return type_map.get(mime_type, "unknown")
