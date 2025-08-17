"""
Local document converter using MarkItDown with pure function architecture.

This module provides the LocalMDConverter class that follows the "Pure Functions + Thin Wrappers"
pattern for local document conversion using the MarkItDown library.
"""

import time
from pathlib import Path
from typing import Optional, Union
from markitdown import MarkItDown

from .config import SDKConfig, get_logger
from .models import ConversionResult, ConversionOptions
from .sync import SyncConverterMixin
from .exceptions import ConversionError
from .utils import (
    convert_content_async,
    convert_text_with_mime_type_async,
    detect_format_from_content,
)
from .validators import FileSizeValidator, MimeTypeValidator, ContentValidator
from .url_converter import URLConverter

from .core.local_converter import (
    validate_local_file_input,
    validate_local_content_input,
    validate_local_text_input,
    build_conversion_options,
    create_conversion_metadata,
    create_conversion_result,
    classify_conversion_error,
    extract_url_options,
    validate_conversion_response,
)


class LocalMDConverter(SyncConverterMixin):
    """
    Local document converter using MarkItDown with clean architecture.

    This class provides local document conversion capabilities using the MarkItDown
    library. It follows the "Pure Functions + Thin Wrappers" pattern where all
    business logic is extracted into testable pure functions.

    Examples:
        Basic usage:
        >>> converter = LocalMDConverter()
        >>> result = await converter.convert_file("document.pdf")
        >>> print(result.markdown)

        With configuration:
        >>> converter = LocalMDConverter(
        ...     ocr_enabled=True,
        ...     js_rendering=True,
        ...     timeout=60
        ... )
    """

    def __init__(
        self,
        ocr_enabled: bool = False,
        js_rendering: bool = False,
        timeout: int = 30,
        max_file_size_mb: int = 50,
        extract_images: bool = False,
        preserve_formatting: bool = False,
        clean_markdown: bool = True,
        debug: bool = False,
    ):
        """
        Initialize local converter with configuration.

        Args:
            ocr_enabled: Enable OCR for scanned PDFs and images
            js_rendering: Use headless browser for JavaScript-heavy web pages
            timeout: Maximum time in seconds for conversion operations
            max_file_size_mb: Maximum file size in MB (default 50MB)
            extract_images: Extract and reference embedded images
            preserve_formatting: Preserve complex formatting in output
            clean_markdown: Clean and normalize markdown output
            debug: Enable debug logging
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
        self._config = self.config  # Alias for test compatibility
        self.config.setup_logging()
        self.logger = get_logger("local_converter")

        # Initialize MarkItDown instance
        self._markitdown = self._create_markitdown_instance()

        # Initialize URL converter
        self._url_converter = URLConverter(self._markitdown, timeout)

        if debug:
            self.logger.info(
                "LocalMDConverter initialized with options: %s", self.options
            )

    def _create_markitdown_instance(self) -> MarkItDown:
        """Create MarkItDown instance with options."""
        kwargs = {}

        # Add any MarkItDown-specific options here
        # Note: MarkItDown doesn't currently support many options,
        # but we prepare for future capabilities

        return MarkItDown(**kwargs)

    @classmethod
    def remote(cls, endpoint: str, api_key: Optional[str] = None, timeout: int = 30):
        """
        Create a remote converter instance.

        This is a convenience method to create a RemoteMDConverter instance
        with the same interface as the local converter.

        Args:
            endpoint: Remote md-server API endpoint
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds

        Returns:
            RemoteMDConverter instance configured for the endpoint
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
            InvalidInputError: If file path is invalid or file doesn't exist
            FileSizeError: If file exceeds size limits
            UnsupportedFormatError: If file format is not supported
            ConversionError: If conversion fails
        """
        start_time = time.time()
        path = Path(file_path)

        try:
            # Use pure functions for validation and processing
            content, file_size, filename = validate_local_file_input(
                path, self.options.max_file_size_mb
            )

            self.logger.info("Converting file: %s (%d bytes)", path, file_size)

            # Detect format using existing utility
            detected_format = detect_format_from_content(content, filename)

            # Validate content type
            ContentValidator.validate_content_type(content, detected_format)

            # Handle binary content specially
            if detected_format == "application/octet-stream":
                # Check for specific binary types
                if content.startswith(b"MZ"):
                    markdown = f"**Executable file detected**: {filename or 'Unknown file'}\n\nThis appears to be an executable file and cannot be converted to text. Executable files are not supported for conversion."
                else:
                    markdown = f"**Binary file detected**: {filename or 'Unknown file'}\n\nThis appears to be a binary file and cannot be converted to text. Binary files are not supported for conversion."
            else:
                # Build conversion options using pure function
                sdk_options = self.options.__dict__
                conversion_options = build_conversion_options(sdk_options, options)

                # Execute conversion (I/O operation)
                markdown = await convert_content_async(
                    self._markitdown,
                    content,
                    filename=filename,
                    options=conversion_options,
                )

            # Validate and clean response
            markdown = validate_conversion_response(markdown)

            # Calculate metrics
            processing_time = time.time() - start_time

            # Create metadata using pure function
            metadata = create_conversion_metadata(
                source_type="file",
                source_size=file_size,
                markdown_content=markdown,
                processing_time=processing_time,
                detected_format=detected_format,
            )

            # Create result using pure function
            return create_conversion_result(markdown, metadata)

        except (ConversionError,):
            # Re-raise SDK exceptions as-is
            raise
        except Exception as e:
            self.logger.error("File conversion failed for %s: %s", path, e)
            # Use pure function for error classification
            context = {
                "file_path": str(path),
                "file_size": file_size if "file_size" in locals() else 0,
            }
            raise classify_conversion_error(e, context)

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
            js_rendering: Override global js_rendering setting for this request
            **options: Additional conversion options to override defaults

        Returns:
            ConversionResult containing markdown content and metadata

        Raises:
            InvalidInputError: If URL is invalid
            NetworkError: If URL cannot be accessed
            ConversionError: If conversion fails
        """
        start_time = time.time()

        try:
            # Extract URL-specific options using pure function
            js_override, remaining_options = extract_url_options(options.copy())

            # Use override or fall back to instance setting
            use_js_rendering = js_override if js_override is not None else js_rendering
            if use_js_rendering is None:
                use_js_rendering = self.options.js_rendering

            self.logger.info(
                "Converting URL: %s (js_rendering=%s)", url, use_js_rendering
            )

            # Use existing URL converter (this handles validation and fetching)
            result = await self._url_converter.convert_url(
                url, js_rendering=use_js_rendering, **remaining_options
            )

            # Update processing time
            processing_time = time.time() - start_time

            # Update metadata with actual processing time
            updated_metadata = create_conversion_metadata(
                source_type="url",
                source_size=result.metadata.source_size,
                markdown_content=result.markdown,
                processing_time=processing_time,
                detected_format=result.metadata.detected_format,
                warnings=result.metadata.warnings,
            )

            return create_conversion_result(result.markdown, updated_metadata)

        except (ConversionError,):
            # Re-raise SDK exceptions as-is
            raise
        except Exception as e:
            self.logger.error("URL conversion failed for %s: %s", url, e)
            # Use pure function for error classification
            context = {
                "url": url,
                "js_rendering": use_js_rendering
                if "use_js_rendering" in locals()
                else False,
            }
            raise classify_conversion_error(e, context)

    async def convert_content(
        self, content: bytes, filename: Optional[str] = None, **options
    ) -> ConversionResult:
        """
        Convert binary content to markdown.

        Converts the provided binary content to markdown. The format is
        automatically detected from the content and optional filename.

        Args:
            content: Binary content to convert
            filename: Optional filename for format detection hint
            **options: Additional conversion options to override defaults

        Returns:
            ConversionResult containing markdown content and metadata

        Raises:
            InvalidInputError: If content is invalid
            FileSizeError: If content exceeds size limits
            UnsupportedFormatError: If format is not supported
            ConversionError: If conversion fails
        """
        start_time = time.time()

        try:
            # Use pure functions for validation
            validated_content, content_size, safe_filename = (
                validate_local_content_input(content, filename)
            )

            # Validate file size using existing validator
            FileSizeValidator.validate_size(
                content_size, max_size_mb=self.options.max_file_size_mb
            )

            self.logger.info(
                "Converting content: %s (%d bytes)", safe_filename, content_size
            )

            # Detect format using existing utility
            detected_format = detect_format_from_content(
                validated_content, safe_filename
            )

            # Validate content type
            ContentValidator.validate_content_type(validated_content, detected_format)

            # Build conversion options using pure function
            sdk_options = self.options.__dict__
            conversion_options = build_conversion_options(sdk_options, options)

            # Execute conversion (I/O operation)
            markdown = await convert_content_async(
                self._markitdown,
                validated_content,
                filename=safe_filename,
                options=conversion_options,
            )

            # Validate and clean response
            markdown = validate_conversion_response(markdown)

            # Calculate metrics
            processing_time = time.time() - start_time

            # Create metadata using pure function
            metadata = create_conversion_metadata(
                source_type="content",
                source_size=content_size,
                markdown_content=markdown,
                processing_time=processing_time,
                detected_format=detected_format,
            )

            # Create result using pure function
            return create_conversion_result(markdown, metadata)

        except (ConversionError,):
            # Re-raise SDK exceptions as-is
            raise
        except Exception as e:
            self.logger.error("Content conversion failed: %s", e)
            # Use pure function for error classification
            context = {
                "content_size": content_size
                if "content_size" in locals()
                else len(content),
                "filename": filename or "unknown",
            }
            raise classify_conversion_error(e, context)

    async def convert_text(
        self, text: str, mime_type: str, **options
    ) -> ConversionResult:
        """
        Convert text content to markdown.

        Converts the provided text content with the specified MIME type to markdown.
        Useful for converting structured text formats like HTML, XML, CSV, etc.

        Args:
            text: Text content to convert
            mime_type: MIME type of the content (e.g., 'text/html', 'text/xml')
            **options: Additional conversion options to override defaults

        Returns:
            ConversionResult containing markdown content and metadata

        Raises:
            InvalidInputError: If text or MIME type is invalid
            ConversionError: If conversion fails
        """
        start_time = time.time()

        try:
            # Use pure functions for validation
            validated_text, text_size, validated_mime_type = validate_local_text_input(
                text, mime_type
            )

            # Validate MIME type using existing validator
            MimeTypeValidator.validate_mime_type(validated_mime_type)

            self.logger.info(
                "Converting text: %s (%d bytes)", validated_mime_type, text_size
            )

            # Build conversion options using pure function
            sdk_options = self.options.__dict__
            conversion_options = build_conversion_options(sdk_options, options)

            # Execute conversion (I/O operation)
            markdown = await convert_text_with_mime_type_async(
                self._markitdown,
                validated_text,
                validated_mime_type,
                options=conversion_options,
            )

            # Validate and clean response
            markdown = validate_conversion_response(markdown)

            # Calculate metrics
            processing_time = time.time() - start_time

            # Create metadata using pure function
            metadata = create_conversion_metadata(
                source_type="text",
                source_size=text_size,
                markdown_content=markdown,
                processing_time=processing_time,
                detected_format=validated_mime_type,
            )

            # Create result using pure function
            return create_conversion_result(markdown, metadata)

        except (ConversionError,):
            # Re-raise SDK exceptions as-is
            raise
        except Exception as e:
            self.logger.error("Text conversion failed: %s", e)
            # Use pure function for error classification
            context = {
                "text_size": text_size if "text_size" in locals() else len(text),
                "mime_type": mime_type,
            }
            raise classify_conversion_error(e, context)

    # Context manager support
    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Cleanup if needed
        pass

    def __enter__(self):
        """Sync context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        # Cleanup if needed
        pass
