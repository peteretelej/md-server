"""
Utility functions for SDK operations.
"""

import asyncio
from io import BytesIO
from pathlib import Path
from typing import Optional

from markitdown import MarkItDown, StreamInfo

from .config import get_logger

logger = get_logger("utils")


async def convert_content_async(
    converter: MarkItDown,
    content: bytes,
    filename: Optional[str] = None,
    options: Optional[dict] = None,
) -> str:
    """Convert binary content to markdown using MarkItDown asynchronously."""
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
    """Synchronous content conversion."""
    stream_info = None
    if filename:
        path = Path(filename)
        stream_info = StreamInfo(extension=path.suffix.lower(), filename=filename)

    kwargs = {}
    if options:
        pass

    with BytesIO(content) as stream:
        result = converter.convert_stream(stream, stream_info=stream_info, **kwargs)
        markdown = result.markdown

        if options:
            if options.get("clean_markdown", False):
                markdown = clean_markdown(markdown)
            if options.get("max_length") and len(markdown) > options["max_length"]:
                markdown = markdown[: options["max_length"]] + "..."

        return markdown


async def convert_text_with_mime_type_async(
    converter: MarkItDown,
    text: str,
    mime_type: str,
    options: Optional[dict] = None,
) -> str:
    """Convert text with specified MIME type to markdown using MarkItDown asynchronously."""
    if mime_type == "text/markdown":
        return text

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        _sync_convert_text_with_mime_type,
        converter,
        text,
        mime_type,
        options,
    )


def _sync_convert_text_with_mime_type(
    converter: MarkItDown,
    text: str,
    mime_type: str,
    options: Optional[dict] = None,
) -> str:
    """Synchronous text conversion with MIME type."""
    text_bytes = text.encode("utf-8")
    stream_info = StreamInfo(mimetype=mime_type)

    kwargs = {}
    if options:
        pass

    with BytesIO(text_bytes) as stream:
        result = converter.convert_stream(stream, stream_info=stream_info, **kwargs)
        markdown = result.markdown

        if options:
            if options.get("clean_markdown", False):
                markdown = clean_markdown(markdown)
            if options.get("max_length") and len(markdown) > options["max_length"]:
                markdown = markdown[: options["max_length"]] + "..."

        return markdown


def clean_markdown(markdown: str) -> str:
    """Clean and normalize markdown content."""
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


def detect_format_from_content(content: bytes, filename: Optional[str] = None) -> str:
    """Detect file format from content and filename."""
    if filename:
        suffix = Path(filename).suffix.lower()
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
        if suffix in format_map:
            return format_map[suffix]

    # Magic byte detection
    if content.startswith(b"%PDF"):
        return "application/pdf"
    elif content.startswith(b"PK"):
        return "application/zip"
    elif content.startswith(b"<"):
        if b"<html" in content[:1024].lower():
            return "text/html"
        elif b"<?xml" in content[:1024]:
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

    # Try to detect text
    try:
        content[:1024].decode("utf-8")
        return "text/plain"
    except UnicodeDecodeError:
        pass

    return "application/octet-stream"