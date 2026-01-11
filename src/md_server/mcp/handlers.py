"""MCP tool handlers - business logic separated from MCP server wiring."""

import mimetypes
import os
from typing import Optional, Union

from .models import MCPSuccessResponse, MCPErrorResponse, MCPMetadata
from .errors import (
    timeout_error,
    connection_error,
    not_found_error,
    access_denied_error,
    server_error,
    invalid_url_error,
    content_empty_error,
    conversion_error,
    unsupported_format_error,
    file_too_large_error,
)
from ..core.converter import DocumentConverter
from ..core.errors import (
    NotFoundError,
    AccessDeniedError,
    ServerError,
    URLTimeoutError,
    URLConnectionError,
    HTTPFetchError,
    ConversionError,
)

# Image extensions that should trigger OCR
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".tiff", ".bmp"}

# Minimum word count to consider content as valid
MIN_WORD_COUNT = 5


async def handle_read_url(
    converter: DocumentConverter,
    url: str,
    render_js: bool = False,
    max_length: Optional[int] = None,
    max_tokens: Optional[int] = None,
    timeout: Optional[int] = None,
    include_frontmatter: bool = True,
    output_format: str = "markdown",
) -> Union[str, MCPSuccessResponse, MCPErrorResponse]:
    """
    Handle read_url tool call.

    Args:
        converter: DocumentConverter instance
        url: URL to fetch and convert
        render_js: Whether to render JavaScript before extraction
        max_length: Maximum characters to return (truncates if exceeded)
        max_tokens: Maximum tokens to return (uses tiktoken cl100k_base encoding)
        timeout: Timeout in seconds for conversion (uses converter default if None)
        include_frontmatter: Include YAML frontmatter with metadata
        output_format: Output format - "markdown" (default) or "json"

    Returns:
        Raw markdown string when output_format="markdown",
        MCPSuccessResponse when output_format="json",
        MCPErrorResponse on failure (always JSON)
    """
    # Validate URL format
    if not url.startswith(("http://", "https://")):
        return invalid_url_error(url)

    try:
        # Build options dict, only include timeout if explicitly set
        options: dict = {
            "js_rendering": render_js,
            "include_frontmatter": include_frontmatter,
        }
        if max_length is not None:
            options["max_length"] = max_length
        if max_tokens is not None:
            options["max_tokens"] = max_tokens
        if timeout is not None:
            options["timeout"] = timeout

        result = await converter.convert_url(url, **options)

        word_count = len(result.markdown.split())

        # Check for minimal/empty content
        if word_count < MIN_WORD_COUNT:
            return content_empty_error(url, tried_js=render_js)

        # Return raw markdown by default
        if output_format == "markdown":
            return result.markdown

        # Return structured JSON response
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

    except NotFoundError as e:
        return not_found_error(e.url)
    except AccessDeniedError as e:
        return access_denied_error(e.url, e.status_code)
    except ServerError as e:
        return server_error(e.url, e.status_code)
    except URLTimeoutError as e:
        return timeout_error("URL fetch", e.timeout)
    except URLConnectionError as e:
        return connection_error(e.url, e.reason)
    except HTTPFetchError as e:
        return conversion_error(str(e))
    except ConversionError as e:
        return conversion_error(str(e))
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
    max_length: Optional[int] = None,
    max_tokens: Optional[int] = None,
    timeout: Optional[int] = None,
    include_frontmatter: bool = True,
    output_format: str = "markdown",
) -> Union[str, MCPSuccessResponse, MCPErrorResponse]:
    """
    Handle read_file tool call.

    Args:
        converter: DocumentConverter instance
        content: File content as bytes
        filename: Original filename with extension
        max_length: Maximum characters to return (truncates if exceeded)
        max_tokens: Maximum tokens to return (uses tiktoken cl100k_base encoding)
        timeout: Timeout in seconds for conversion (uses converter default if None)
        include_frontmatter: Include YAML frontmatter with metadata
        output_format: Output format - "markdown" (default) or "json"

    Returns:
        Raw markdown string when output_format="markdown",
        MCPSuccessResponse when output_format="json",
        MCPErrorResponse on failure (always JSON)
    """
    ext = os.path.splitext(filename)[1].lower()
    is_image = ext in IMAGE_EXTENSIONS

    # Check file size
    size_mb = len(content) / (1024 * 1024)
    if size_mb > converter.max_file_size_mb:
        return file_too_large_error(size_mb, converter.max_file_size_mb)

    try:
        # Build options dict
        options: dict = {
            "include_frontmatter": include_frontmatter,
            "ocr_enabled": is_image,  # Auto-enable OCR for images
        }
        if max_length is not None:
            options["max_length"] = max_length
        if max_tokens is not None:
            options["max_tokens"] = max_tokens
        if timeout is not None:
            options["timeout"] = timeout

        result = await converter.convert_content(content, filename=filename, **options)

        # Return raw markdown by default
        if output_format == "markdown":
            return result.markdown

        # Return structured JSON response
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
