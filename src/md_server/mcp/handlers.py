"""MCP tool handlers - business logic separated from MCP server wiring."""

import mimetypes
import os
from typing import Union

from .models import MCPSuccessResponse, MCPErrorResponse, MCPMetadata
from .errors import (
    timeout_error,
    connection_error,
    invalid_url_error,
    content_empty_error,
    conversion_error,
    unsupported_format_error,
    file_too_large_error,
)
from ..core.converter import DocumentConverter

# Image extensions that should trigger OCR
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".tiff", ".bmp"}

# Minimum word count to consider content as valid
MIN_WORD_COUNT = 5


async def handle_read_url(
    converter: DocumentConverter,
    url: str,
    render_js: bool = False,
) -> Union[MCPSuccessResponse, MCPErrorResponse]:
    """
    Handle read_url tool call.

    Args:
        converter: DocumentConverter instance
        url: URL to fetch and convert
        render_js: Whether to render JavaScript before extraction

    Returns:
        MCPSuccessResponse on success, MCPErrorResponse on failure
    """
    # Validate URL format
    if not url.startswith(("http://", "https://")):
        return invalid_url_error(url)

    try:
        result = await converter.convert_url(
            url,
            js_rendering=render_js,
            include_frontmatter=True,  # Always extract metadata
        )

        word_count = len(result.markdown.split())

        # Check for minimal/empty content
        if word_count < MIN_WORD_COUNT:
            return content_empty_error(url, tried_js=render_js)

        return MCPSuccessResponse(
            title=result.metadata.title or _extract_title_from_url(url),
            content=result.markdown,
            source=url,
            word_count=word_count,
            metadata=MCPMetadata(
                description=None,  # Could be extracted from meta tags
                language=result.metadata.detected_language,
            ),
        )

    except TimeoutError:
        return timeout_error("URL fetch", converter.timeout)
    except ConnectionError as e:
        return connection_error(url, str(e))
    except ValueError as e:
        # SSRF validation errors, invalid URLs, etc.
        error_msg = str(e)
        if "blocked" in error_msg.lower() or "ssrf" in error_msg.lower():
            return connection_error(url, "URL is blocked for security reasons")
        return conversion_error(error_msg)
    except Exception as e:
        return conversion_error(str(e))


async def handle_read_file(
    converter: DocumentConverter,
    content: bytes,
    filename: str,
) -> Union[MCPSuccessResponse, MCPErrorResponse]:
    """
    Handle read_file tool call.

    Args:
        converter: DocumentConverter instance
        content: File content as bytes
        filename: Original filename with extension

    Returns:
        MCPSuccessResponse on success, MCPErrorResponse on failure
    """
    ext = os.path.splitext(filename)[1].lower()
    is_image = ext in IMAGE_EXTENSIONS

    # Check file size
    size_mb = len(content) / (1024 * 1024)
    if size_mb > converter.max_file_size_mb:
        return file_too_large_error(size_mb, converter.max_file_size_mb)

    try:
        result = await converter.convert_content(
            content,
            filename=filename,
            include_frontmatter=True,
            ocr_enabled=is_image,  # Auto-enable OCR for images
        )

        word_count = len(result.markdown.split())
        mime_type, _ = mimetypes.guess_type(filename)

        return MCPSuccessResponse(
            title=result.metadata.title or filename,
            content=result.markdown,
            source=filename,
            word_count=word_count,
            metadata=MCPMetadata(
                pages=None,  # Could be extracted for PDFs
                format=mime_type or result.metadata.detected_format,
                ocr_applied=is_image,
                language=result.metadata.detected_language,
            ),
        )

    except ValueError as e:
        error_msg = str(e).lower()
        if "unsupported" in error_msg or "format" in error_msg:
            return unsupported_format_error(ext)
        if "too large" in error_msg:
            return file_too_large_error(size_mb, converter.max_file_size_mb)
        return conversion_error(str(e))
    except TimeoutError:
        return timeout_error("File conversion", converter.timeout)
    except Exception as e:
        return conversion_error(str(e))


def _extract_title_from_url(url: str) -> str:
    """Extract a reasonable title from a URL."""
    from urllib.parse import urlparse

    parsed = urlparse(url)

    # Try to get something meaningful from the path
    path = parsed.path.rstrip("/")
    if path:
        # Get last path segment
        last_segment = path.split("/")[-1]
        if last_segment:
            # Remove common file extensions
            for ext in [".html", ".htm", ".php", ".asp", ".aspx"]:
                if last_segment.endswith(ext):
                    last_segment = last_segment[: -len(ext)]
            # Convert hyphens/underscores to spaces and title case
            title = last_segment.replace("-", " ").replace("_", " ").title()
            return title

    # Fall back to domain
    return parsed.netloc or url
