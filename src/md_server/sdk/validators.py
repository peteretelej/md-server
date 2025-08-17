"""
Validation utilities for SDK operations.
"""

from urllib.parse import urlparse
from typing import Optional

from .exceptions import InvalidInputError, FileSizeError, UnsupportedFormatError


class URLValidator:
    """URL validation for document conversion."""

    @classmethod
    def validate_url(cls, url: str) -> str:
        """Validate URL format for document conversion."""
        if not url or not url.strip():
            raise InvalidInputError("URL cannot be empty")

        url = url.strip()
        parsed = urlparse(url)

        if not parsed.scheme or not parsed.netloc:
            raise InvalidInputError("Invalid URL format")

        if parsed.scheme.lower() not in ["http", "https"]:
            raise InvalidInputError("Only HTTP/HTTPS URLs allowed")

        return url


class FileSizeValidator:
    """File size validation by content type."""

    DEFAULT_MAX_SIZE = 50 * 1024 * 1024  # 50MB

    FORMAT_LIMITS = {
        "application/pdf": 50 * 1024 * 1024,  # 50MB for PDFs
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": 25
        * 1024
        * 1024,  # 25MB for DOCX
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": 25
        * 1024
        * 1024,  # 25MB for PPTX
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": 25
        * 1024
        * 1024,  # 25MB for XLSX
        "text/plain": 10 * 1024 * 1024,  # 10MB for text
        "text/html": 10 * 1024 * 1024,  # 10MB for HTML
        "text/markdown": 10 * 1024 * 1024,  # 10MB for markdown
        "application/json": 5 * 1024 * 1024,  # 5MB for JSON
        "image/png": 20 * 1024 * 1024,  # 20MB for images
        "image/jpeg": 20 * 1024 * 1024,  # 20MB for images
        "image/jpg": 20 * 1024 * 1024,  # 20MB for images
    }

    @classmethod
    def validate_size(
        cls,
        content_size: int,
        content_type: Optional[str] = None,
        max_size_mb: Optional[int] = None,
    ) -> None:
        """Validate content size against limits."""
        if content_size <= 0:
            return

        # Use custom limit if provided
        if max_size_mb:
            limit = max_size_mb * 1024 * 1024
        else:
            limit = cls.FORMAT_LIMITS.get(content_type or "", cls.DEFAULT_MAX_SIZE)

        if content_size > limit:
            limit_mb = limit / (1024 * 1024)
            actual_mb = content_size / (1024 * 1024)
            raise FileSizeError(
                f"File size {actual_mb:.1f}MB exceeds limit of {limit_mb:.0f}MB for {content_type or 'this format'}",
                {
                    "file_size": content_size,
                    "limit": limit,
                    "content_type": content_type,
                },
            )


class MimeTypeValidator:
    """MIME type validation for text content."""

    @classmethod
    def validate_mime_type(cls, mime_type: str) -> str:
        """Validate MIME type format and security."""
        if not mime_type:
            raise InvalidInputError("MIME type cannot be empty")

        if len(mime_type) > 100:
            raise InvalidInputError("MIME type too long (max 100 characters)")

        if "/" not in mime_type:
            raise InvalidInputError("MIME type must contain '/' separator")

        if mime_type.count("/") != 1:
            raise InvalidInputError("MIME type must contain exactly one '/' separator")

        if ".." in mime_type or "\\" in mime_type:
            raise InvalidInputError("Invalid characters in MIME type")

        return mime_type.strip().lower()


class ContentValidator:
    """Content validation using magic bytes."""

    MAGIC_BYTES = {
        b"\x25\x50\x44\x46": "application/pdf",  # PDF
        b"\x50\x4b\x03\x04": "application/zip",  # ZIP (includes DOCX, XLSX, PPTX)
        b"\x50\x4b\x05\x06": "application/zip",  # Empty ZIP
        b"\x50\x4b\x07\x08": "application/zip",  # ZIP
        b"\x89\x50\x4e\x47": "image/png",  # PNG
        b"\xff\xd8\xff": "image/jpeg",  # JPEG
        b"\x47\x49\x46\x38": "image/gif",  # GIF
        b"\x52\x49\x46\x46": "audio/wav",  # WAV (RIFF)
        b"\x49\x44\x33": "audio/mp3",  # MP3 with ID3
        b"\xff\xfb": "audio/mp3",  # MP3
        b"\x3c\x3f\x78\x6d\x6c": "application/xml",  # XML <?xml
        b"\x3c\x68\x74\x6d\x6c": "text/html",  # HTML <html
        b"\x3c\x21\x44\x4f\x43\x54\x59\x50\x45": "text/html",  # HTML <!DOCTYPE
    }

    @classmethod
    def detect_content_type(cls, content: bytes) -> str:
        """Detect content type from magic bytes."""
        if not content:
            return "application/octet-stream"

        for magic, content_type in cls.MAGIC_BYTES.items():
            if content.startswith(magic):
                return content_type

        try:
            content[:1024].decode("utf-8")
            return "text/plain"
        except UnicodeDecodeError:
            pass

        return "application/octet-stream"

    @classmethod
    def validate_content_type(
        cls, content: bytes, declared_type: Optional[str] = None
    ) -> str:
        """Validate that declared content type matches detected type."""
        detected_type = cls.detect_content_type(content)

        if not declared_type:
            return detected_type

        # Handle Office documents (ZIP-based)
        if detected_type == "application/zip" and declared_type in [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ]:
            return declared_type

        if detected_type == "application/octet-stream":
            return declared_type

        # For text types, be more permissive as detection can be inaccurate
        if declared_type.startswith("text/") and detected_type == "text/plain":
            return declared_type

        # Strict matching for security-sensitive binary types only
        security_sensitive = ["application/pdf", "image/png", "image/jpeg"]
        if declared_type in security_sensitive and detected_type != declared_type:
            raise UnsupportedFormatError(
                f"Content type mismatch: declared {declared_type} but detected {detected_type}",
                {"declared": declared_type, "detected": detected_type},
            )

        return declared_type
