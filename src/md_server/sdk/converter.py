"""
Main converter class for document to markdown conversion.
"""

import time
from pathlib import Path
from typing import Optional, Union

from .config import SDKConfig, get_logger
from .exceptions import ConversionError, InvalidInputError, FileSizeError
from .models import ConversionResult, ConversionMetadata, ConversionOptions


class MDConverter:
    """Main converter class for document to markdown conversion."""
    
    def __init__(
        self,
        ocr_enabled: bool = False,
        js_rendering: bool = False,
        timeout: int = 30,
        max_file_size_mb: int = 50,
        extract_images: bool = False,
        preserve_formatting: bool = True,
        clean_markdown: bool = False,
        debug: bool = False
    ):
        """Initialize converter with configuration."""
        self.options = ConversionOptions(
            ocr_enabled=ocr_enabled,
            js_rendering=js_rendering,
            extract_images=extract_images,
            preserve_formatting=preserve_formatting,
            clean_markdown=clean_markdown,
            timeout=timeout,
            max_file_size_mb=max_file_size_mb
        )
        
        self.config = SDKConfig(debug=debug)
        self.config.setup_logging()
        self.logger = get_logger("converter")
        
        if debug:
            self.logger.info("MDConverter initialized with options: %s", self.options)
    
    @classmethod
    def remote(
        cls,
        endpoint: str,
        api_key: Optional[str] = None,
        timeout: int = 30
    ) -> "RemoteMDConverter":
        """Create a remote converter client."""
        from .remote import RemoteMDConverter
        return RemoteMDConverter(endpoint, api_key, timeout)
    
    async def convert_file(
        self, 
        file_path: Union[str, Path],
        **options
    ) -> ConversionResult:
        """Convert a local file to markdown."""
        start_time = time.time()
        
        path = Path(file_path)
        if not path.exists():
            raise InvalidInputError(f"File not found: {file_path}")
        
        file_size = path.stat().st_size
        max_size_bytes = self.options.max_file_size_mb * 1024 * 1024
        
        if file_size > max_size_bytes:
            raise FileSizeError(
                f"File size {file_size} exceeds limit {max_size_bytes}",
                {"file_size": file_size, "limit": max_size_bytes}
            )
        
        self.logger.info("Converting file: %s (%d bytes)", path, file_size)
        
        content = path.read_bytes()
        
        # For Phase 1, just return a placeholder result
        # Phase 2 will implement actual conversion logic
        markdown = f"# {path.name}\n\nPlaceholder conversion for {path.name}"
        
        processing_time = time.time() - start_time
        
        metadata = ConversionMetadata(
            source_type="file",
            source_size=file_size,
            markdown_size=len(markdown.encode()),
            processing_time=processing_time,
            detected_format=self._detect_format(content, path.name)
        )
        
        return ConversionResult(markdown=markdown, metadata=metadata)
    
    async def convert_url(
        self,
        url: str,
        js_rendering: Optional[bool] = None,
        **options
    ) -> ConversionResult:
        """Convert URL content to markdown."""
        start_time = time.time()
        
        self.logger.info("Converting URL: %s", url)
        
        # Placeholder implementation for Phase 1
        markdown = f"# URL Content\n\nPlaceholder conversion for {url}"
        
        processing_time = time.time() - start_time
        
        metadata = ConversionMetadata(
            source_type="url",
            source_size=len(url),
            markdown_size=len(markdown.encode()),
            processing_time=processing_time,
            detected_format="text/html"
        )
        
        return ConversionResult(markdown=markdown, metadata=metadata)
    
    async def convert_content(
        self,
        content: bytes,
        filename: Optional[str] = None,
        **options
    ) -> ConversionResult:
        """Convert binary content to markdown."""
        start_time = time.time()
        
        content_size = len(content)
        max_size_bytes = self.options.max_file_size_mb * 1024 * 1024
        
        if content_size > max_size_bytes:
            raise FileSizeError(
                f"Content size {content_size} exceeds limit {max_size_bytes}",
                {"content_size": content_size, "limit": max_size_bytes}
            )
        
        self.logger.info("Converting content: %d bytes, filename=%s", content_size, filename)
        
        # Placeholder implementation for Phase 1
        markdown = f"# Binary Content\n\nPlaceholder conversion for {filename or 'unnamed'}"
        
        processing_time = time.time() - start_time
        
        metadata = ConversionMetadata(
            source_type="content",
            source_size=content_size,
            markdown_size=len(markdown.encode()),
            processing_time=processing_time,
            detected_format=self._detect_format(content, filename)
        )
        
        return ConversionResult(markdown=markdown, metadata=metadata)
    
    async def convert_text(
        self,
        text: str,
        mime_type: str,
        **options
    ) -> ConversionResult:
        """Convert text with MIME type to markdown."""
        start_time = time.time()
        
        text_size = len(text.encode())
        
        self.logger.info("Converting text: %d bytes, mime_type=%s", text_size, mime_type)
        
        # Placeholder implementation for Phase 1
        markdown = f"# Text Content\n\nPlaceholder conversion for {mime_type} text"
        
        processing_time = time.time() - start_time
        
        metadata = ConversionMetadata(
            source_type="text",
            source_size=text_size,
            markdown_size=len(markdown.encode()),
            processing_time=processing_time,
            detected_format=mime_type
        )
        
        return ConversionResult(markdown=markdown, metadata=metadata)
    
    def _detect_format(self, content: bytes, filename: Optional[str] = None) -> str:
        """Detect file format from content and filename."""
        if filename:
            suffix = Path(filename).suffix.lower()
            format_map = {
                ".pdf": "application/pdf",
                ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ".html": "text/html",
                ".txt": "text/plain",
                ".md": "text/markdown",
            }
            if suffix in format_map:
                return format_map[suffix]
        
        # Basic magic byte detection
        if content.startswith(b"%PDF"):
            return "application/pdf"
        elif content.startswith(b"PK"):
            return "application/zip"
        elif content.startswith(b"<"):
            return "text/html"
        
        return "application/octet-stream"