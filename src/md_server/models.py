from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import uuid


class ConversionOptions(BaseModel):
    js_rendering: Optional[bool] = Field(
        default=None, description="Use headless browser for JavaScript sites"
    )
    timeout: Optional[int] = Field(default=None, description="Timeout in seconds")
    extract_images: Optional[bool] = Field(
        default=False, description="Extract and link images"
    )
    preserve_formatting: Optional[bool] = Field(
        default=True, description="Preserve complex formatting"
    )
    ocr_enabled: Optional[bool] = Field(
        default=False, description="Enable OCR for images/PDFs"
    )
    max_length: Optional[int] = Field(
        default=None, description="Truncate output for previews"
    )
    clean_markdown: Optional[bool] = Field(
        default=False, description="Normalize/clean markdown output"
    )
    include_frontmatter: Optional[bool] = Field(
        default=False, description="Prepend YAML frontmatter with metadata to output"
    )
    output_format: Optional[str] = Field(
        default=None,
        description="Response format: 'json' (default) or 'markdown' (raw markdown with metadata in headers)",
    )


class ConvertRequest(BaseModel):
    url: Optional[str] = Field(default=None, description="URL to fetch and convert")
    content: Optional[str] = Field(
        default=None, description="Base64 encoded file content"
    )
    text: Optional[str] = Field(default=None, description="Raw text content")
    mime_type: Optional[str] = Field(
        default=None, description="MIME type for text content"
    )
    filename: Optional[str] = Field(
        default=None, description="Original filename for format detection"
    )
    source_format: Optional[str] = Field(
        default=None, description="Explicit source format override"
    )
    options: Optional[ConversionOptions] = Field(
        default=None, description="Processing options"
    )

    def model_post_init(self, __context: Any) -> None:
        input_count = sum(
            1 for field in [self.url, self.content, self.text] if field is not None
        )
        if input_count == 0:
            raise ValueError("One of url, content, or text must be provided")
        if input_count > 1:
            raise ValueError("Only one of url, content, or text can be provided")


class ConversionMetadata(BaseModel):
    source_type: str = Field(description="Type of source content (pdf, html, etc.)")
    source_size: int = Field(description="Size of source content in bytes")
    markdown_size: int = Field(description="Size of converted markdown in bytes")
    conversion_time_ms: int = Field(
        description="Time taken for conversion in milliseconds"
    )
    detected_format: str = Field(description="Detected format/MIME type")
    warnings: List[str] = Field(default_factory=list, description="Conversion warnings")
    title: Optional[str] = Field(default=None, description="Extracted document title")
    estimated_tokens: int = Field(default=0, description="Estimated token count")
    detected_language: Optional[str] = Field(
        default=None, description="ISO 639-1 language code"
    )


class ConversionResult(BaseModel):
    """Result of a document conversion operation from core converter."""

    success: bool = Field(description="Whether conversion was successful")
    markdown: str = Field(description="Converted markdown content")
    metadata: ConversionMetadata = Field(description="Conversion metadata")
    request_id: str = Field(
        default_factory=lambda: f"req_{uuid.uuid4()}",
        description="Unique request identifier",
    )


class ConvertResponse(BaseModel):
    success: bool = Field(description="Whether conversion was successful")
    markdown: str = Field(description="Converted markdown content")
    metadata: ConversionMetadata = Field(description="Conversion metadata")
    request_id: str = Field(description="Unique request identifier")

    @classmethod
    def create_success(
        cls,
        markdown: str,
        source_type: str,
        source_size: int,
        conversion_time_ms: int,
        detected_format: str,
        warnings: Optional[List[str]] = None,
        title: Optional[str] = None,
        estimated_tokens: int = 0,
        detected_language: Optional[str] = None,
    ) -> "ConvertResponse":
        return cls(
            success=True,
            markdown=markdown,
            metadata=ConversionMetadata(
                source_type=source_type,
                source_size=source_size,
                markdown_size=len(markdown.encode("utf-8")),
                conversion_time_ms=conversion_time_ms,
                detected_format=detected_format,
                warnings=warnings or [],
                title=title,
                estimated_tokens=estimated_tokens,
                detected_language=detected_language,
            ),
            request_id=f"req_{uuid.uuid4()}",
        )


class ErrorDetails(BaseModel):
    detected_format: Optional[str] = None
    supported_formats: Optional[List[str]] = None
    magic_bytes: Optional[str] = None


class ConvertError(BaseModel):
    code: str = Field(description="Error code")
    message: str = Field(description="Human readable error message")
    details: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional error details"
    )
    suggestions: Optional[List[str]] = Field(
        default=None, description="Suggested actions"
    )


class ErrorResponse(BaseModel):
    success: bool = Field(default=False, description="Always false for errors")
    error: ConvertError = Field(description="Error information")
    request_id: str = Field(description="Unique request identifier")

    @classmethod
    def create_error(
        cls,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None,
    ) -> "ErrorResponse":
        return cls(
            error=ConvertError(
                code=code, message=message, details=details, suggestions=suggestions
            ),
            request_id=f"req_{uuid.uuid4()}",
        )


# Models for /formats endpoint
class FormatCapabilities(BaseModel):
    mime_types: List[str] = Field(description="Supported MIME types")
    extensions: List[str] = Field(description="Supported file extensions")
    features: List[str] = Field(description="Available features for this format")
    max_size_mb: int = Field(description="Maximum file size in MB")


class SystemCapabilities(BaseModel):
    browser_available: bool = Field(description="Whether browser support is available")


class FormatsResponse(BaseModel):
    formats: Dict[str, FormatCapabilities] = Field(
        description="Supported formats and their capabilities"
    )
    supported_formats: List[str] = Field(description="List of supported format names")
    capabilities: SystemCapabilities = Field(
        description="System capability information"
    )


# Models for /health endpoint
class HealthResponse(BaseModel):
    status: str = Field(description="Health status")
    version: str = Field(description="Application version")
    uptime_seconds: int = Field(description="Server uptime in seconds")
    conversions_last_hour: Optional[int] = Field(
        default=0, description="Number of conversions in the last hour"
    )
