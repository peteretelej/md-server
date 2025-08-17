"""
Pure functions for validation operations.

Functions for input validation, file type detection, and data sanitization
without I/O dependencies.
"""

import mimetypes
import re
from pathlib import Path
from typing import Dict, Any, Set

from ..exceptions import InvalidInputError


def validate_file_path(path: str) -> Path:
    """Validate and normalize file path."""
    if not path or not isinstance(path, str):
        raise InvalidInputError("File path cannot be empty")

    path_obj = Path(path.strip())

    if not path_obj.name:
        raise InvalidInputError("Invalid file path")

    return path_obj


def validate_file_size_limits(
    size: int, content_type: str, limits: Dict[str, int]
) -> None:
    """Validate file size against content-type specific limits."""
    if size < 0:
        raise InvalidInputError("File size cannot be negative")

    if size == 0:
        raise InvalidInputError("File cannot be empty")

    default_limit = limits.get("default", 50 * 1024 * 1024)  # 50MB default

    if content_type.startswith("image/"):
        limit = limits.get("image", 10 * 1024 * 1024)  # 10MB for images
    elif content_type.startswith("video/"):
        limit = limits.get("video", 100 * 1024 * 1024)  # 100MB for videos
    elif content_type == "application/pdf":
        limit = limits.get("pdf", 20 * 1024 * 1024)  # 20MB for PDFs
    else:
        limit = default_limit

    if size > limit:
        raise InvalidInputError(
            f"File too large: {size} bytes exceeds {limit} byte limit for {content_type}"
        )


def validate_remote_file_size(size: int, max_remote_size: int) -> None:
    """Validate remote file size."""
    if size < 0:
        raise InvalidInputError("File size cannot be negative")

    if size == 0:
        raise InvalidInputError("Remote file cannot be empty")

    if size > max_remote_size:
        raise InvalidInputError(
            f"Remote file too large: {size} bytes exceeds {max_remote_size} byte limit"
        )


def detect_file_content_type(content: bytes, filename: str) -> str:
    """Detect file content type from content and filename."""
    if not content:
        return "application/octet-stream"

    # Try to detect from filename extension
    content_type, _ = mimetypes.guess_type(filename)
    if content_type:
        return content_type

    # Basic magic number detection
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    elif content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    elif content.startswith(b"GIF87a") or content.startswith(b"GIF89a"):
        return "image/gif"
    elif content.startswith(b"%PDF"):
        return "application/pdf"
    elif content.startswith(b"PK\x03\x04"):
        # ZIP-based formats
        if filename.endswith((".docx", ".xlsx", ".pptx")):
            return f"application/vnd.openxmlformats-officedocument.{filename.split('.')[-1]}"
        return "application/zip"
    elif content.startswith(b"\xd0\xcf\x11\xe0"):
        # Old Office formats
        if filename.endswith(".doc"):
            return "application/msword"
        elif filename.endswith(".xls"):
            return "application/vnd.ms-excel"
        elif filename.endswith(".ppt"):
            return "application/vnd.ms-powerpoint"
        return "application/octet-stream"

    # Check if it's text
    try:
        content.decode("utf-8")
        if filename.endswith(".html"):
            return "text/html"
        elif filename.endswith(".xml"):
            return "text/xml"
        elif filename.endswith(".json"):
            return "application/json"
        elif filename.endswith(".csv"):
            return "text/csv"
        else:
            return "text/plain"
    except UnicodeDecodeError:
        pass

    return "application/octet-stream"


def validate_conversion_options(
    options: Dict[str, Any], allowed_keys: Set[str]
) -> Dict[str, Any]:
    """Validate and filter conversion options."""
    validated = {}

    for key, value in options.items():
        if key not in allowed_keys:
            continue

        if key in (
            "js_rendering",
            "extract_images",
            "ocr_enabled",
            "preserve_formatting",
            "clean_markdown",
        ):
            if not isinstance(value, bool):
                raise InvalidInputError(f"Option '{key}' must be boolean")
        elif key == "timeout":
            if not isinstance(value, (int, float)) or value <= 0:
                raise InvalidInputError(f"Option '{key}' must be positive number")

        validated[key] = value

    return validated


def sanitize_filename_for_api(filename: str) -> str:
    """Sanitize filename for API transmission."""
    if not filename:
        return "unknown"

    # Remove path components
    filename = Path(filename).name

    # Replace unsafe characters
    safe_chars = re.sub(r"[^\w\-_\.]", "_", filename)

    # Ensure it doesn't start with dot or dash
    if safe_chars.startswith((".", "-")):
        safe_chars = "file_" + safe_chars

    # Limit length
    if len(safe_chars) > 255:
        name, ext = safe_chars.rsplit(".", 1) if "." in safe_chars else (safe_chars, "")
        name = name[:250]
        safe_chars = f"{name}.{ext}" if ext else name

    return safe_chars or "unknown"
