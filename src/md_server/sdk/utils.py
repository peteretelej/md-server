"""
Utility functions for SDK operations.
"""

import asyncio
from io import BytesIO
from pathlib import Path
from typing import Optional, Dict, Any

from markitdown import MarkItDown, StreamInfo

from .config import get_logger

logger = get_logger("utils")


class FormatDetector:
    """Detects file formats from content and filename."""

    def __init__(self):
        self._format_map = {
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

    def detect(self, content: bytes, filename: Optional[str] = None) -> str:
        """Detect file format from content and filename."""
        # Check for binary content first to prevent extension-based misidentification
        magic_result = self._detect_from_magic_bytes(content)
        if magic_result == "application/octet-stream":
            return magic_result

        return (
            self._detect_from_filename(filename)
            or magic_result
            or self._detect_from_text_analysis(content)
            or "application/octet-stream"
        )

    def _detect_from_filename(self, filename: Optional[str]) -> Optional[str]:
        """Detect format from filename extension."""
        if not filename:
            return None

        suffix = Path(filename).suffix.lower()
        return self._format_map.get(suffix)

    def _detect_from_magic_bytes(self, content: bytes) -> Optional[str]:
        """Detect format from magic bytes at start of content."""
        # Check for specific formats first before generic binary detection
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

        # Check for binary content indicators after known formats
        if b"\x00" in content:
            return "application/octet-stream"

        return None

    def _detect_from_text_analysis(self, content: bytes) -> Optional[str]:
        """Try to detect if content is text."""
        try:
            content[:1024].decode("utf-8")
            return "text/plain"
        except UnicodeDecodeError:
            return None


class MarkdownCleaner:
    """Cleans and normalizes markdown content."""

    def clean(self, markdown: str) -> str:
        """Clean and normalize markdown content."""
        if not markdown:
            return markdown

        lines = markdown.split("\n")
        cleaned_lines = self._remove_empty_lines(lines)
        cleaned_lines = self._normalize_whitespace(cleaned_lines)

        return "\n".join(cleaned_lines)

    def _remove_empty_lines(self, lines: list[str]) -> list[str]:
        """Remove excessive empty lines while preserving structure."""
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            if line:
                cleaned_lines.append(line)
            elif cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")

        while cleaned_lines and cleaned_lines[-1] == "":
            cleaned_lines.pop()

        return cleaned_lines

    def _normalize_whitespace(self, lines: list[str]) -> list[str]:
        """Normalize whitespace in lines."""
        return lines


class AsyncConverter:
    """Handles async conversion operations."""

    def __init__(self):
        self._markdown_cleaner = MarkdownCleaner()

    async def convert_content(
        self,
        converter: MarkItDown,
        content: bytes,
        filename: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Convert binary content to markdown using MarkItDown asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._sync_convert_content, converter, content, filename, options
        )

    async def convert_text_with_mime_type(
        self,
        converter: MarkItDown,
        text: str,
        mime_type: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Convert text with specified MIME type to markdown using MarkItDown asynchronously."""
        if mime_type == "text/markdown":
            return text

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._sync_convert_text_with_mime_type,
            converter,
            text,
            mime_type,
            options,
        )

    def _sync_convert_content(
        self,
        converter: MarkItDown,
        content: bytes,
        filename: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Synchronous content conversion."""
        stream_info = self._create_stream_info_for_content(filename)

        with BytesIO(content) as stream:
            result = converter.convert_stream(stream, stream_info=stream_info)
            markdown = result.markdown

            return self._apply_options(markdown, options)

    def _sync_convert_text_with_mime_type(
        self,
        converter: MarkItDown,
        text: str,
        mime_type: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Synchronous text conversion with MIME type."""
        text_bytes = text.encode("utf-8")
        stream_info = StreamInfo(mimetype=mime_type)

        with BytesIO(text_bytes) as stream:
            result = converter.convert_stream(stream, stream_info=stream_info)
            markdown = result.markdown

            return self._apply_options(markdown, options)

    def _create_stream_info_for_content(
        self, filename: Optional[str]
    ) -> Optional[StreamInfo]:
        """Create StreamInfo from filename."""
        if not filename:
            return None

        path = Path(filename)
        return StreamInfo(extension=path.suffix.lower(), filename=filename)

    def _apply_options(self, markdown: str, options: Optional[Dict[str, Any]]) -> str:
        """Apply post-processing options to markdown."""
        if not options:
            return markdown

        if options.get("clean_markdown", False):
            markdown = self._markdown_cleaner.clean(markdown)

        if options.get("max_length") and len(markdown) > options["max_length"]:
            markdown = markdown[: options["max_length"]] + "..."

        return markdown


# Module-level instances for backward compatibility
_format_detector = FormatDetector()
_async_converter = AsyncConverter()
_markdown_cleaner = MarkdownCleaner()


async def convert_content_async(
    converter: MarkItDown,
    content: bytes,
    filename: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None,
) -> str:
    """Convert binary content to markdown using MarkItDown asynchronously."""
    return await _async_converter.convert_content(converter, content, filename, options)


async def convert_text_with_mime_type_async(
    converter: MarkItDown,
    text: str,
    mime_type: str,
    options: Optional[Dict[str, Any]] = None,
) -> str:
    """Convert text with specified MIME type to markdown using MarkItDown asynchronously."""
    return await _async_converter.convert_text_with_mime_type(
        converter, text, mime_type, options
    )


def clean_markdown(markdown: str) -> str:
    """Clean and normalize markdown content."""
    return _markdown_cleaner.clean(markdown)


def detect_format_from_content(content: bytes, filename: Optional[str] = None) -> str:
    """Detect file format from content and filename."""
    return _format_detector.detect(content, filename)
