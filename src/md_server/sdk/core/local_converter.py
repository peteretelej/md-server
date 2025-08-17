"""
Pure functions for local document conversion.

Functions for processing local files, content, and text using MarkItDown
without I/O dependencies.
"""

import time
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

from ..models import ConversionResult, ConversionMetadata
from ..exceptions import (
    ConversionError,
    InvalidInputError,
    FileSizeError,
    UnsupportedFormatError,
)


def validate_local_file_input(
    file_path: Path, max_size_mb: int
) -> Tuple[bytes, int, str]:
    """
    Validate and read local file for conversion.

    Args:
        file_path: Path object to validate and read
        max_size_mb: Maximum allowed file size in MB

    Returns:
        Tuple of (file_content, file_size, filename)

    Raises:
        InvalidInputError: If file doesn't exist or is invalid
        FileSizeError: If file exceeds size limits
    """
    if not file_path.exists():
        raise InvalidInputError(f"File not found: {file_path}")

    if not file_path.is_file():
        raise InvalidInputError(f"Path is not a file: {file_path}")

    file_size = file_path.stat().st_size
    max_size_bytes = max_size_mb * 1024 * 1024

    if file_size > max_size_bytes:
        raise FileSizeError(
            f"File size {file_size} bytes exceeds limit of {max_size_bytes} bytes"
        )

    if file_size == 0:
        raise InvalidInputError(f"File is empty: {file_path}")

    try:
        content = file_path.read_bytes()
    except PermissionError as e:
        raise InvalidInputError(f"Permission denied reading file: {file_path}") from e
    except OSError as e:
        raise InvalidInputError(f"Error reading file: {file_path}") from e

    return content, file_size, file_path.name


def validate_local_content_input(
    content: bytes, filename: Optional[str] = None
) -> Tuple[bytes, int, str]:
    """
    Validate content for local conversion.

    Args:
        content: Binary content to validate
        filename: Optional filename for format detection

    Returns:
        Tuple of (content, size, filename)

    Raises:
        InvalidInputError: If content is invalid
    """
    if not isinstance(content, bytes):
        raise InvalidInputError("Content must be bytes")

    if len(content) == 0:
        raise InvalidInputError("Content cannot be empty")

    # Use provided filename or default
    safe_filename = filename if filename else "unknown"

    return content, len(content), safe_filename


def validate_local_text_input(text: str, mime_type: str) -> Tuple[str, int, str]:
    """
    Validate text input for local conversion.

    Args:
        text: Text content to validate
        mime_type: MIME type of the text

    Returns:
        Tuple of (text, size, mime_type)

    Raises:
        InvalidInputError: If text or MIME type is invalid
    """
    if not isinstance(text, str):
        raise InvalidInputError("Text must be a string")

    if not text or not text.strip():
        raise InvalidInputError("Text cannot be empty")

    if not mime_type or not isinstance(mime_type, str):
        raise InvalidInputError("MIME type must be a non-empty string")

    # Basic MIME type validation
    if "/" not in mime_type:
        raise InvalidInputError("MIME type must contain '/' separator")

    return text.strip(), len(text.encode()), mime_type.strip()


def build_conversion_options(
    sdk_options: Dict[str, Any], method_options: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Build MarkItDown conversion options from SDK options.

    Args:
        sdk_options: SDK-level conversion options
        method_options: Method-specific override options

    Returns:
        Dictionary of options for MarkItDown conversion
    """
    conversion_options = {}

    # Map SDK options to MarkItDown options
    if sdk_options.get("clean_markdown", False):
        conversion_options["clean_markdown"] = True

    if sdk_options.get("extract_images", False):
        # MarkItDown doesn't have extract_images, but we track it
        conversion_options["extract_images"] = True

    if sdk_options.get("preserve_formatting", False):
        conversion_options["preserve_formatting"] = True

    # Add method-specific overrides
    if method_options:
        conversion_options.update(method_options)

    return conversion_options


def create_conversion_metadata(
    source_type: str,
    source_size: int,
    markdown_content: str,
    processing_time: float,
    detected_format: str,
    warnings: Optional[list] = None,
) -> ConversionMetadata:
    """
    Create conversion metadata from processing results.

    Args:
        source_type: Type of source (file, content, text, url)
        source_size: Size of source in bytes
        markdown_content: Generated markdown content
        processing_time: Time taken for conversion in seconds
        detected_format: Detected format of the source
        warnings: Optional list of warning messages

    Returns:
        ConversionMetadata object
    """
    return ConversionMetadata(
        source_type=source_type,
        source_size=source_size,
        markdown_size=len(markdown_content.encode()),
        processing_time=processing_time,
        detected_format=detected_format,
        warnings=warnings or [],
    )


def create_conversion_result(
    markdown_content: str,
    metadata: ConversionMetadata,
    request_id: Optional[str] = None,
) -> ConversionResult:
    """
    Create final conversion result.

    Args:
        markdown_content: Generated markdown content
        metadata: Conversion metadata
        request_id: Optional request ID for tracking

    Returns:
        ConversionResult object
    """
    return ConversionResult(
        markdown=markdown_content,
        metadata=metadata,
        success=True,
        request_id=request_id or f"local_{int(time.time() * 1000)}",
    )


def classify_conversion_error(
    exception: Exception, context: Dict[str, Any]
) -> Exception:
    """
    Classify and map conversion errors to appropriate SDK exceptions.

    Args:
        exception: Original exception from MarkItDown or other components
        context: Context information for error details

    Returns:
        Appropriate SDK exception
    """
    error_msg = str(exception).lower()

    # Check for known MarkItDown errors
    if "timeout" in error_msg or "time" in error_msg:
        return ConversionError(f"Conversion timed out: {str(exception)}", context)

    if "memory" in error_msg or "size" in error_msg:
        return ConversionError(f"Memory or size error: {str(exception)}", context)

    if "format" in error_msg or "unsupported" in error_msg:
        return UnsupportedFormatError(f"Unsupported format: {str(exception)}", context)

    if "permission" in error_msg or "access" in error_msg:
        return InvalidInputError(f"Access error: {str(exception)}", context)

    # Default to ConversionError
    return ConversionError(f"Conversion failed: {str(exception)}", context)


def extract_url_options(
    options: Dict[str, Any],
) -> Tuple[Optional[bool], Dict[str, Any]]:
    """
    Extract URL-specific options from general options.

    Args:
        options: Dictionary of conversion options

    Returns:
        Tuple of (js_rendering_override, remaining_options)
    """
    # Extract js_rendering if specified
    js_rendering = options.pop("js_rendering", None)

    # Return remaining options
    return js_rendering, options


def merge_conversion_options(
    default_options: Dict[str, Any], override_options: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Merge default options with override options.

    Args:
        default_options: Default SDK options
        override_options: Method-specific override options

    Returns:
        Merged options dictionary
    """
    merged = default_options.copy()

    # Add overrides, preserving the original types where possible
    for key, value in override_options.items():
        if value is not None:
            merged[key] = value

    return merged


def validate_conversion_response(markdown_result: str) -> str:
    """
    Validate and clean conversion response.

    Args:
        markdown_result: Raw markdown result from MarkItDown

    Returns:
        Validated and cleaned markdown content

    Raises:
        ConversionError: If result is invalid
    """
    if not isinstance(markdown_result, str):
        raise ConversionError("Conversion result must be a string")

    # MarkItDown can return empty strings for some inputs
    if not markdown_result:
        return ""

    # Basic cleanup - remove excessive whitespace while preserving structure
    lines = markdown_result.split("\n")
    cleaned_lines = []

    for line in lines:
        # Preserve line structure but clean up excessive spaces
        cleaned_line = " ".join(line.split())
        cleaned_lines.append(cleaned_line)

    return "\n".join(cleaned_lines)


def calculate_processing_metrics(
    start_time: float, end_time: float
) -> Dict[str, float]:
    """
    Calculate processing performance metrics.

    Args:
        start_time: Start timestamp
        end_time: End timestamp

    Returns:
        Dictionary with performance metrics
    """
    processing_time = end_time - start_time

    return {
        "processing_time": processing_time,
        "start_time": start_time,
        "end_time": end_time,
    }
