import mimetypes
import base64
from typing import Optional, Dict, Tuple
from pathlib import Path


class ContentTypeDetector:
    # Magic byte signatures for common file types
    MAGIC_BYTES = {
        b"%PDF-": "application/pdf",
        b"PK\x03\x04": "application/zip",  # Also covers docx, xlsx, pptx
        b"\x89PNG\r\n\x1a\n": "image/png",
        b"\xff\xd8\xff": "image/jpeg",
        b"GIF87a": "image/gif",
        b"GIF89a": "image/gif",
        b"RIFF": "audio/wav",
        b"ID3": "audio/mpeg",
        b"\x00\x00\x00 ftypmp4": "video/mp4",
        b"<html": "text/html",
        b"<!DOCTYPE html": "text/html",
        b"<?xml": "text/xml",
        b"{": "application/json",
        b"[": "application/json",
    }

    # Office document specific detection within ZIP files
    OFFICE_SIGNATURES = {
        "word/document.xml": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xl/workbook.xml": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "ppt/presentation.xml": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }

    @classmethod
    def detect_from_content_type_header(
        cls, content_type: Optional[str]
    ) -> Optional[str]:
        if not content_type:
            return None

        # Remove charset and other parameters
        mime_type = content_type.split(";")[0].strip().lower()
        return mime_type if mime_type else None

    @classmethod
    def detect_from_filename(cls, filename: Optional[str]) -> Optional[str]:
        if not filename:
            return None

        path = Path(filename)
        mime_type, _ = mimetypes.guess_type(path.name)
        return mime_type

    @classmethod
    def detect_from_magic_bytes(cls, content: bytes) -> Optional[str]:
        if not content:
            return "text/plain"  # Empty content defaults to text/plain

        # Check for exact matches first
        for signature, mime_type in cls.MAGIC_BYTES.items():
            if content.startswith(signature):
                # Special handling for ZIP-based Office formats
                if mime_type == "application/zip":
                    return cls._detect_office_format(content)
                return mime_type

        # Check for HTML patterns anywhere in first 512 bytes
        header = content[:512].lower()
        if b"<html" in header or b"<!doctype html" in header:
            return "text/html"

        # Check if it's likely text
        try:
            text = content.decode("utf-8")

            # Check for binary content indicators
            if b"\x00" in content:  # Null bytes are strong indicator of binary
                return "application/octet-stream"

            # Check for high ratio of non-printable characters
            non_printable_count = sum(
                1 for byte in content if byte < 32 and byte not in [9, 10, 13]
            )
            if len(content) > 0 and non_printable_count / len(content) > 0.3:
                return "application/octet-stream"

            if text.strip().startswith("#") or text.strip().startswith("*"):
                return "text/markdown"
            return "text/plain"
        except UnicodeDecodeError:
            return "application/octet-stream"

        return None

    @classmethod
    def detect_from_content(
        cls, content: bytes, filename: Optional[str] = None
    ) -> Optional[str]:
        # Try magic bytes detection first
        magic_result = cls.detect_from_magic_bytes(content)
        if magic_result:
            return magic_result

        # Fall back to filename detection if provided
        if filename:
            return cls.detect_from_filename(filename)

        return None

    @classmethod
    def _detect_office_format(cls, content: bytes) -> str:
        # This is a simplified detection - in a full implementation,
        # you would parse the ZIP structure to look for specific files
        # For now, return generic zip type
        return "application/zip"

    @classmethod
    def detect_input_type(
        cls,
        content_type: Optional[str] = None,
        filename: Optional[str] = None,
        content: Optional[bytes] = None,
        request_data: Optional[Dict] = None,
    ) -> Tuple[str, str]:
        # If we have JSON request data, determine JSON input type
        if request_data:
            if "url" in request_data:
                return "json_url", "text/url"
            elif "content" in request_data:
                # Try to detect format from base64 content
                try:
                    decoded = base64.b64decode(request_data["content"])
                    detected_format = cls.detect_from_magic_bytes(decoded)
                    if detected_format:
                        return "json_content", detected_format
                except Exception:
                    pass

                # Fallback to filename detection
                if "filename" in request_data:
                    detected_format = cls.detect_from_filename(request_data["filename"])
                    if detected_format:
                        return "json_content", detected_format

                return "json_content", "application/octet-stream"
            elif "text" in request_data:
                if "mime_type" in request_data:
                    return "json_text_typed", request_data["mime_type"]
                return "json_text", "text/markdown"

        # Binary upload detection
        if content and not request_data:
            # Check if this looks like multipart (has filename)
            if filename:
                input_type = "multipart"
            else:
                input_type = "binary"

            # Detect format from multiple sources in priority order
            detected_format = (
                cls.detect_from_content_type_header(content_type)
                or cls.detect_from_filename(filename)
                or cls.detect_from_magic_bytes(content)
                or "application/octet-stream"
            )

            return input_type, detected_format

        return "unknown", "application/octet-stream"

    @classmethod
    def get_source_type(cls, mime_type: str) -> str:
        mime_to_source = {
            "application/pdf": "pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
            "text/html": "html",
            "text/plain": "text",
            "text/markdown": "markdown",
            "application/json": "json",
            "text/url": "url",
            "image/png": "image",
            "image/jpeg": "image",
            "image/gif": "image",
            "audio/mpeg": "audio",
            "audio/wav": "audio",
            "video/mp4": "video",
        }
        return mime_to_source.get(mime_type, "unknown")

    @classmethod
    def is_supported_format(cls, mime_type: str) -> bool:
        supported_formats = [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "text/html",
            "text/plain",
            "text/markdown",
            "application/json",
            "text/url",
            "image/png",
            "image/jpeg",
            "image/gif",
            "text/xml",
            "application/xml",
        ]
        return mime_type in supported_formats

    @classmethod
    def get_supported_formats(cls) -> dict:
        return {
            "pdf": {
                "mime_types": ["application/pdf"],
                "extensions": [".pdf"],
                "features": ["ocr", "extract_images", "preserve_formatting"],
                "max_size_mb": 50,
            },
            "docx": {
                "mime_types": [
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                ],
                "extensions": [".docx"],
                "features": ["extract_images", "preserve_formatting"],
                "max_size_mb": 25,
            },
            "xlsx": {
                "mime_types": [
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ],
                "extensions": [".xlsx"],
                "features": ["preserve_formatting"],
                "max_size_mb": 25,
            },
            "pptx": {
                "mime_types": [
                    "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                ],
                "extensions": [".pptx"],
                "features": ["extract_images", "preserve_formatting"],
                "max_size_mb": 25,
            },
            "html": {
                "mime_types": ["text/html"],
                "extensions": [".html", ".htm"],
                "features": ["js_rendering", "extract_images"],
                "max_size_mb": 10,
            },
            "markdown": {
                "mime_types": ["text/markdown", "text/x-markdown"],
                "extensions": [".md", ".markdown"],
                "features": ["clean_markdown"],
                "max_size_mb": 5,
            },
            "text": {
                "mime_types": ["text/plain"],
                "extensions": [".txt"],
                "features": ["clean_markdown"],
                "max_size_mb": 5,
            },
            "json": {
                "mime_types": ["application/json"],
                "extensions": [".json"],
                "features": [],
                "max_size_mb": 5,
            },
            "xml": {
                "mime_types": ["text/xml", "application/xml"],
                "extensions": [".xml"],
                "features": [],
                "max_size_mb": 5,
            },
            "images": {
                "mime_types": ["image/png", "image/jpeg", "image/gif"],
                "extensions": [".png", ".jpg", ".jpeg", ".gif"],
                "features": ["ocr"],
                "max_size_mb": 10,
            },
        }
