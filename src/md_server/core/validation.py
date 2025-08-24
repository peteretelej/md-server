from urllib.parse import urlparse
from typing import Optional


class ValidationError(Exception):
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message)
        self.details = details or {}


class URLValidator:
    @classmethod
    def validate_url(cls, url: str) -> str:
        if not url or not url.strip():
            raise ValidationError("URL cannot be empty")

        url = url.strip()
        parsed = urlparse(url)

        if not parsed.scheme:
            raise ValidationError("Invalid URL format")

        if parsed.scheme.lower() not in ["http", "https"]:
            raise ValidationError("Only HTTP/HTTPS URLs allowed")

        if not parsed.netloc:
            raise ValidationError("Invalid URL format")

        return url


class FileSizeValidator:
    DEFAULT_MAX_SIZE = 50 * 1024 * 1024  # 50MB default

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
        if content_size <= 0:
            return

        # Use custom limit if provided, otherwise use format-specific limit
        if max_size_mb:
            limit = max_size_mb * 1024 * 1024
        else:
            limit = cls.FORMAT_LIMITS.get(content_type or "", cls.DEFAULT_MAX_SIZE)

        if content_size > limit:
            limit_mb = limit / (1024 * 1024)
            actual_mb = content_size / (1024 * 1024)
            raise ValidationError(
                f"File size {actual_mb:.1f}MB exceeds limit of {limit_mb:.0f}MB for {content_type or 'this format'}",
                {
                    "file_size": content_size,
                    "limit": limit,
                    "content_type": content_type,
                },
            )


class MimeTypeValidator:
    @classmethod
    def validate_mime_type(cls, mime_type: str) -> str:
        if not mime_type:
            raise ValidationError("MIME type cannot be empty")

        if len(mime_type) > 100:
            raise ValidationError("MIME type too long (max 100 characters)")

        if "/" not in mime_type:
            raise ValidationError("MIME type must contain '/' separator")

        if ".." in mime_type or "\\" in mime_type:
            raise ValidationError("Invalid characters in MIME type")

        if mime_type.count("/") != 1:
            raise ValidationError("MIME type must contain exactly one '/' separator")

        return mime_type.strip().lower()


class ContentValidator:
    # Magic byte signatures for file type detection
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
        detected_type = cls.detect_content_type(content)

        if not declared_type:
            return detected_type

        # Handle Office documents (ZIP-based formats)
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
            raise ValidationError(
                f"Content type mismatch: declared {declared_type} but detected {detected_type}",
                {"declared": declared_type, "detected": detected_type},
            )

        return declared_type
