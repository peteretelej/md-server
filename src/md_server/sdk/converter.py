"""
Main converter class for document to markdown conversion.
"""

import time
from pathlib import Path
from typing import Optional, Union

from markitdown import MarkItDown

from .config import SDKConfig, get_logger
from .exceptions import (
    ConversionError,
    InvalidInputError,
    FileSizeError,
    TimeoutError,
    UnsupportedFormatError,
    NetworkError,
)
from .models import ConversionResult, ConversionMetadata, ConversionOptions
from .sync import SyncConverterMixin, sync_wrapper
from .utils import (
    convert_content_async,
    convert_text_with_mime_type_async,
    detect_format_from_content,
)
from .validators import FileSizeValidator, MimeTypeValidator, ContentValidator
from .url_converter import URLConverter


class MDConverter(SyncConverterMixin):
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
        debug: bool = False,
    ):
        """Initialize converter with configuration."""
        self.options = ConversionOptions(
            ocr_enabled=ocr_enabled,
            js_rendering=js_rendering,
            extract_images=extract_images,
            preserve_formatting=preserve_formatting,
            clean_markdown=clean_markdown,
            timeout=timeout,
            max_file_size_mb=max_file_size_mb,
        )

        self.config = SDKConfig(debug=debug)
        self.config.setup_logging()
        self.logger = get_logger("converter")

        # Initialize MarkItDown instance
        self._markitdown = self._create_markitdown_instance()

        # Initialize URL converter
        self._url_converter = URLConverter(self._markitdown, timeout)

        if debug:
            self.logger.info("MDConverter initialized with options: %s", self.options)

    def _create_markitdown_instance(self) -> MarkItDown:
        """Create MarkItDown instance with options."""
        # Create MarkItDown with configuration based on options
        kwargs = {}

        # Add any MarkItDown-specific options here
        if hasattr(self.options, "extract_images") and self.options.extract_images:
            # MarkItDown doesn't have extract_images option, but we track it for future use
            pass

        return MarkItDown(**kwargs)

    @classmethod
    def remote(cls, endpoint: str, api_key: Optional[str] = None, timeout: int = 30):
        """Create a remote converter client."""
        from .remote import RemoteMDConverter

        return RemoteMDConverter(endpoint, api_key, timeout)

    async def convert_file(
        self, file_path: Union[str, Path], **options
    ) -> ConversionResult:
        """Convert a local file to markdown."""
        start_time = time.time()

        path = Path(file_path)
        if not path.exists():
            raise InvalidInputError(f"File not found: {file_path}")

        file_size = path.stat().st_size

        # Validate file size
        FileSizeValidator.validate_size(
            file_size, max_size_mb=self.options.max_file_size_mb
        )

        self.logger.info("Converting file: %s (%d bytes)", path, file_size)

        content = path.read_bytes()
        detected_format = detect_format_from_content(content, path.name)

        # Validate content type
        ContentValidator.validate_content_type(content, detected_format)

        try:
            # Convert using MarkItDown
            conversion_options = self._build_conversion_options(options)
            markdown = await convert_content_async(
                self._markitdown,
                content,
                filename=path.name,
                options=conversion_options,
            )

            processing_time = time.time() - start_time

            metadata = ConversionMetadata(
                source_type="file",
                source_size=file_size,
                markdown_size=len(markdown.encode()),
                processing_time=processing_time,
                detected_format=detected_format,
            )

            return ConversionResult(markdown=markdown, metadata=metadata)

        except (InvalidInputError, FileSizeError, UnsupportedFormatError):
            # Re-raise SDK exceptions as-is
            raise
        except Exception as e:
            self.logger.error("File conversion failed for %s: %s", path, e)
            raise ConversionError(
                f"Failed to convert file: {str(e)}", {"file_path": str(path)}
            )

    async def convert_url(
        self, url: str, js_rendering: Optional[bool] = None, **options
    ) -> ConversionResult:
        """Convert URL content to markdown."""
        start_time = time.time()

        self.logger.info("Converting URL: %s", url)

        # Use default from options if not specified
        if js_rendering is None:
            js_rendering = self.options.js_rendering

        try:
            markdown = await self._url_converter.convert_url(url, js_rendering)

            processing_time = time.time() - start_time

            metadata = ConversionMetadata(
                source_type="url",
                source_size=len(url),
                markdown_size=len(markdown.encode()),
                processing_time=processing_time,
                detected_format="text/html",
            )

            return ConversionResult(markdown=markdown, metadata=metadata)

        except (InvalidInputError, NetworkError, TimeoutError):
            # Re-raise SDK exceptions as-is
            raise
        except Exception as e:
            self.logger.error("URL conversion failed for %s: %s", url, e)
            raise ConversionError(f"Failed to convert URL: {str(e)}", {"url": url})

    async def convert_content(
        self, content: bytes, filename: Optional[str] = None, **options
    ) -> ConversionResult:
        """Convert binary content to markdown."""
        start_time = time.time()

        content_size = len(content)
        detected_format = detect_format_from_content(content, filename)

        # Validate file size
        FileSizeValidator.validate_size(
            content_size,
            content_type=detected_format,
            max_size_mb=self.options.max_file_size_mb,
        )

        # Validate content type
        ContentValidator.validate_content_type(content, detected_format)

        self.logger.info(
            "Converting content: %d bytes, filename=%s, format=%s",
            content_size,
            filename,
            detected_format,
        )

        try:
            # Convert using MarkItDown
            conversion_options = self._build_conversion_options(options)
            markdown = await convert_content_async(
                self._markitdown, content, filename=filename, options=conversion_options
            )

            processing_time = time.time() - start_time

            metadata = ConversionMetadata(
                source_type="content",
                source_size=content_size,
                markdown_size=len(markdown.encode()),
                processing_time=processing_time,
                detected_format=detected_format,
            )

            return ConversionResult(markdown=markdown, metadata=metadata)

        except (FileSizeError, UnsupportedFormatError):
            # Re-raise SDK exceptions as-is
            raise
        except Exception as e:
            self.logger.error("Content conversion failed: %s", e)
            raise ConversionError(
                f"Failed to convert content: {str(e)}", {"filename": filename}
            )

    async def convert_text(
        self, text: str, mime_type: str, **options
    ) -> ConversionResult:
        """Convert text with MIME type to markdown."""
        start_time = time.time()

        # Validate MIME type
        validated_mime_type = MimeTypeValidator.validate_mime_type(mime_type)

        text_size = len(text.encode())

        # Validate text size
        FileSizeValidator.validate_size(
            text_size,
            content_type=validated_mime_type,
            max_size_mb=self.options.max_file_size_mb,
        )

        self.logger.info(
            "Converting text: %d bytes, mime_type=%s", text_size, validated_mime_type
        )

        try:
            # Convert using MarkItDown
            conversion_options = self._build_conversion_options(options)
            markdown = await convert_text_with_mime_type_async(
                self._markitdown, text, validated_mime_type, options=conversion_options
            )

            processing_time = time.time() - start_time

            metadata = ConversionMetadata(
                source_type="text",
                source_size=text_size,
                markdown_size=len(markdown.encode()),
                processing_time=processing_time,
                detected_format=validated_mime_type,
            )

            return ConversionResult(markdown=markdown, metadata=metadata)

        except (InvalidInputError, FileSizeError):
            # Re-raise SDK exceptions as-is
            raise
        except Exception as e:
            self.logger.error("Text conversion failed: %s", e)
            raise ConversionError(
                f"Failed to convert text: {str(e)}", {"mime_type": validated_mime_type}
            )

    def _build_conversion_options(self, options: dict) -> dict:
        """Build conversion options dictionary."""
        conversion_options = {}

        # Merge SDK options with method-specific options
        if self.options.clean_markdown:
            conversion_options["clean_markdown"] = True

        # Add any additional options passed to the method
        if options:
            conversion_options.update(options)

        return conversion_options

    # Sync API Methods

    def convert_file_sync(
        self, file_path: Union[str, Path], **options
    ) -> ConversionResult:
        """
        Synchronous version of convert_file.

        Convert a local file to markdown synchronously.

        Args:
            file_path: Path to the file to convert
            **options: Additional conversion options

        Returns:
            ConversionResult with markdown content and metadata

        Raises:
            FileNotFoundError: If file doesn't exist
            ConversionError: If conversion fails
        """
        return sync_wrapper(self.convert_file)(file_path, **options)

    def convert_url_sync(
        self, url: str, js_rendering: Optional[bool] = None, **options
    ) -> ConversionResult:
        """
        Synchronous version of convert_url.

        Convert URL content to markdown synchronously.

        Args:
            url: URL to convert
            js_rendering: Enable JavaScript rendering
            **options: Additional conversion options

        Returns:
            ConversionResult with markdown content and metadata

        Raises:
            NetworkError: If URL can't be accessed
            ConversionError: If conversion fails
        """
        return sync_wrapper(self.convert_url)(url, js_rendering=js_rendering, **options)

    def convert_content_sync(
        self, content: bytes, filename: Optional[str] = None, **options
    ) -> ConversionResult:
        """
        Synchronous version of convert_content.

        Convert binary content to markdown synchronously.

        Args:
            content: Binary content to convert
            filename: Optional filename for format detection
            **options: Additional conversion options

        Returns:
            ConversionResult with markdown content and metadata

        Raises:
            FileSizeError: If content exceeds size limits
            UnsupportedFormatError: If format not supported
            ConversionError: If conversion fails
        """
        return sync_wrapper(self.convert_content)(content, filename=filename, **options)

    def convert_text_sync(
        self, text: str, mime_type: str, **options
    ) -> ConversionResult:
        """
        Synchronous version of convert_text.

        Convert text with MIME type to markdown synchronously.

        Args:
            text: Text content to convert
            mime_type: MIME type of the content
            **options: Additional conversion options

        Returns:
            ConversionResult with markdown content and metadata

        Raises:
            InvalidInputError: If text or MIME type invalid
            ConversionError: If conversion fails
        """
        return sync_wrapper(self.convert_text)(text, mime_type, **options)

    # Context Manager Support

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager with cleanup."""
        # Cleanup any resources if needed
        self.logger.debug("MDConverter context manager exited")
        return False  # Don't suppress exceptions

    async def __aenter__(self):
        """Enter async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager with cleanup."""
        # Cleanup any resources if needed
        self.logger.debug("MDConverter async context manager exited")
        return False  # Don't suppress exceptions
