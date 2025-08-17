"""
Data models for conversion results and metadata.
"""

from dataclasses import dataclass, field
from typing import List
import uuid


@dataclass
class ConversionMetadata:
    """
    Metadata about the conversion process.

    Contains information about the source document, conversion performance,
    and any warnings that occurred during processing.

    Attributes:
        source_type: Type of source input ("file", "url", "content", "text")
        source_size: Size of the source input in bytes
        markdown_size: Size of the generated markdown in bytes
        processing_time: Time taken for conversion in seconds
        detected_format: MIME type or format detected from input
        warnings: List of non-fatal warnings during conversion

    Example:
        >>> metadata = result.metadata
        >>> print(f"Converted {metadata.source_size} bytes to {metadata.markdown_size} chars")
        >>> print(f"Processing took {metadata.processing_time:.2f} seconds")
    """

    source_type: str
    source_size: int
    markdown_size: int
    processing_time: float
    detected_format: str
    warnings: List[str] = field(default_factory=list)


@dataclass
class ConversionResult:
    """
    Result of a document conversion operation.

    Contains the converted markdown content along with metadata about
    the conversion process. This is the primary return type for all
    conversion methods.

    Attributes:
        markdown: The converted markdown content as a string
        metadata: ConversionMetadata with processing information
        success: Whether the conversion completed successfully (always True)
        request_id: Unique identifier for this conversion request

    Example:
        >>> result = await converter.convert_file("document.pdf")
        >>> print(result.markdown)
        >>> print(f"Request ID: {result.request_id}")
        >>> print(f"Format: {result.metadata.detected_format}")
    """

    markdown: str
    metadata: ConversionMetadata
    success: bool = True
    request_id: str = field(default_factory=lambda: f"req_{uuid.uuid4()}")


@dataclass
class ConversionOptions:
    """
    Options for document conversion.

    Configuration options that control how documents are processed
    and converted to markdown. These options can be set globally
    when creating a converter or overridden per conversion.

    Attributes:
        ocr_enabled: Enable OCR for scanned PDFs and images
        js_rendering: Use headless browser for JavaScript-heavy pages
        extract_images: Extract and reference embedded images
        preserve_formatting: Preserve complex formatting in output
        clean_markdown: Clean and normalize markdown output
        timeout: Maximum time in seconds for conversion operations
        max_file_size_mb: Maximum file size in MB

    Example:
        >>> options = ConversionOptions(
        ...     ocr_enabled=True,
        ...     js_rendering=True,
        ...     timeout=60
        ... )
        >>> converter = MDConverter(**options.__dict__)
    """

    ocr_enabled: bool = False
    js_rendering: bool = False
    extract_images: bool = False
    preserve_formatting: bool = True
    clean_markdown: bool = False
    timeout: int = 30
    max_file_size_mb: int = 50
