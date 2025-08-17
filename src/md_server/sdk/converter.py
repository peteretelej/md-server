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
    """
    Main converter class for document to markdown conversion.

    This class provides both local and remote conversion capabilities for various
    document formats including PDFs, Word documents, web pages, and text content.

    Examples:
        Basic usage:
        >>> converter = MDConverter()
        >>> result = await converter.convert_file("document.pdf")
        >>> print(result.markdown)

        With configuration:
        >>> converter = MDConverter(
        ...     ocr_enabled=True,
        ...     js_rendering=True,
        ...     timeout=60
        ... )

        Remote conversion:
        >>> remote = MDConverter.remote(
        ...     endpoint="https://api.example.com",
        ...     api_key="your-key"
        ... )
    """

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
        """
        Initialize converter with configuration.

        Args:
            ocr_enabled: Enable OCR for scanned PDFs and images
            js_rendering: Use headless browser for JavaScript-heavy web pages
            timeout: Maximum time in seconds for conversion operations
            max_file_size_mb: Maximum file size in MB (default 50MB)
            extract_images: Extract and reference embedded images
            preserve_formatting: Preserve complex formatting in output
            clean_markdown: Clean and normalize markdown output
            debug: Enable debug logging

        Example:
            >>> converter = MDConverter(
            ...     ocr_enabled=True,
            ...     js_rendering=True,
            ...     timeout=60,
            ...     max_file_size_mb=100
            ... )
        """
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
        """
        Create a remote converter client.

        Connect to a remote md-server instance for conversion operations.
        Useful for distributed architectures or when you don't want to
        install conversion dependencies locally.

        Args:
            endpoint: Base URL of the remote md-server instance
            api_key: Optional API key for authentication
            timeout: HTTP request timeout in seconds

        Returns:
            RemoteMDConverter instance configured for the endpoint

        Example:
            >>> converter = MDConverter.remote(
            ...     endpoint="https://api.example.com",
            ...     api_key="your-secret-key",
            ...     timeout=30
            ... )
            >>> result = await converter.convert_file("document.pdf")
        """
        from .remote import RemoteMDConverter

        return RemoteMDConverter(endpoint, api_key, timeout)

    async def convert_file(
        self, file_path: Union[str, Path], **options
    ) -> ConversionResult:
        """
        Convert a local file to markdown.

        Supports various document formats including PDF, DOCX, XLSX, PPTX,
        images (with OCR), and many others. The format is automatically
        detected from file content and extension.

        Args:
            file_path: Path to the file to convert (str or Path object)
            **options: Additional conversion options to override defaults

        Returns:
            ConversionResult containing markdown content and metadata

        Raises:
            InvalidInputError: If file doesn't exist or path is invalid
            FileSizeError: If file exceeds configured size limits
            UnsupportedFormatError: If file format is not supported
            ConversionError: If conversion process fails

        Example:
            >>> result = await converter.convert_file("/path/to/document.pdf")
            >>> print(result.markdown)
            >>> print(f"Processed {result.metadata.source_size} bytes")
        """
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
        """
        Convert URL content to markdown.

        Fetches content from the specified URL and converts it to markdown.
        Can handle both static HTML pages and JavaScript-heavy single-page
        applications when js_rendering is enabled.

        Args:
            url: URL to fetch and convert
            js_rendering: Override global js_rendering setting for this request.
                         If True, uses headless browser for JavaScript execution
            **options: Additional conversion options to override defaults

        Returns:
            ConversionResult containing markdown content and metadata

        Raises:
            InvalidInputError: If URL format is invalid
            NetworkError: If URL cannot be accessed or times out
            TimeoutError: If conversion exceeds configured timeout
            ConversionError: If conversion process fails

        Example:
            >>> # Static page conversion
            >>> result = await converter.convert_url("https://example.com")
            
            >>> # JavaScript-heavy page
            >>> result = await converter.convert_url(
            ...     "https://spa.example.com",
            ...     js_rendering=True
            ... )
        """
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
        """
        Convert binary content to markdown.

        Converts raw binary data to markdown. The format is automatically
        detected using magic bytes and the optional filename. Useful for
        processing content from memory, APIs, or network streams.

        Args:
            content: Binary content to convert
            filename: Optional filename for format detection hints.
                     Should include file extension for best results
            **options: Additional conversion options to override defaults

        Returns:
            ConversionResult containing markdown content and metadata

        Raises:
            FileSizeError: If content exceeds configured size limits
            UnsupportedFormatError: If content format is not supported
            ConversionError: If conversion process fails

        Example:
            >>> with open("document.pdf", "rb") as f:
            ...     content = f.read()
            >>> result = await converter.convert_content(
            ...     content, 
            ...     filename="document.pdf"
            ... )
            
            >>> # From API response
            >>> response = requests.get("https://example.com/file.docx")
            >>> result = await converter.convert_content(
            ...     response.content,
            ...     filename="downloaded.docx"
            ... )
        """
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
        """
        Convert text with MIME type to markdown.

        Converts text content with a specified MIME type to markdown.
        Useful for processing HTML, XML, JSON, CSV, or other text-based
        formats where you know the content type.

        Args:
            text: Text content to convert
            mime_type: MIME type of the content (e.g., "text/html", "text/xml")
            **options: Additional conversion options to override defaults

        Returns:
            ConversionResult containing markdown content and metadata

        Raises:
            InvalidInputError: If text is empty or MIME type is invalid
            FileSizeError: If text exceeds configured size limits
            ConversionError: If conversion process fails

        Example:
            >>> # Convert HTML
            >>> html = "<h1>Title</h1><p>Content</p>"
            >>> result = await converter.convert_text(html, "text/html")
            
            >>> # Convert XML
            >>> xml = "<?xml version='1.0'?><root><item>Data</item></root>"
            >>> result = await converter.convert_text(xml, "text/xml")
            
            >>> # Convert CSV
            >>> csv_data = "name,age\nJohn,30\nJane,25"
            >>> result = await converter.convert_text(csv_data, "text/csv")
        """
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
