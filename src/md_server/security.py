from urllib.parse import urlparse


class URLValidator:
    """Basic URL validation for document conversion"""

    @classmethod
    def validate_url(cls, url: str) -> str:
        """Validate URL format for document conversion"""
        parsed = urlparse(url.strip())

        if not parsed.scheme or not parsed.netloc:
            raise ValueError("Invalid URL format")

        if parsed.scheme.lower() not in ["http", "https"]:
            raise ValueError("Only HTTP/HTTPS URLs allowed")

        return url


class FileSizeValidator:
    """File size validation by content type"""

    # Default size limits in bytes (50MB general, specific limits for types)
    DEFAULT_MAX_SIZE = 50 * 1024 * 1024

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
    def validate_size(cls, content_size: int, content_type: str = None) -> None:
        """Validate content size against limits"""
        if content_size <= 0:
            return

        # Get limit for specific content type or use default
        limit = cls.FORMAT_LIMITS.get(content_type, cls.DEFAULT_MAX_SIZE)

        if content_size > limit:
            limit_mb = limit / (1024 * 1024)
            actual_mb = content_size / (1024 * 1024)
            raise ValueError(
                f"File size {actual_mb:.1f}MB exceeds limit of {limit_mb:.0f}MB for {content_type or 'this format'}"
            )


class ContentValidator:
    """Content validation using magic bytes"""

    # Common file signatures (magic bytes)
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
        """Detect content type from magic bytes"""
        if not content:
            return "application/octet-stream"

        # Check against known magic bytes
        for magic, content_type in cls.MAGIC_BYTES.items():
            if content.startswith(magic):
                return content_type

        # Check for text content (UTF-8)
        try:
            content[:1024].decode("utf-8")
            return "text/plain"
        except UnicodeDecodeError:
            pass

        return "application/octet-stream"

    @classmethod
    def validate_content_type(cls, content: bytes, declared_type: str = None) -> str:
        """Validate that declared content type matches detected type"""
        detected_type = cls.detect_content_type(content)

        # If no declared type, return detected
        if not declared_type:
            return detected_type

        # Handle Office documents (ZIP-based)
        if detected_type == "application/zip" and declared_type in [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ]:
            # Accept Office docs as ZIP-based
            return declared_type

        # Handle generic cases
        if detected_type == "application/octet-stream":
            # Can't detect, trust declared type
            return declared_type

        # Strict matching for security-sensitive types
        security_sensitive = ["application/pdf", "text/html", "image/png", "image/jpeg"]
        if declared_type in security_sensitive and detected_type != declared_type:
            raise ValueError(
                f"Content type mismatch: declared {declared_type} but detected {detected_type}"
            )

        return declared_type
