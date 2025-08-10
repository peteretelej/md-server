import pytest
import uuid
from typing import Dict, Any
from md_server.models import (
    ConversionOptions,
    ConvertRequest,
    ConversionMetadata,
    ConvertResponse,
    ErrorDetails,
    ConvertError,
    ErrorResponse,
    FormatCapabilities,
    FormatsResponse,
    HealthResponse,
)


class TestConversionOptions:
    def test_default_values(self):
        """Test default values for ConversionOptions"""
        options = ConversionOptions()
        
        assert options.js_rendering is None
        assert options.timeout is None
        assert options.extract_images is False
        assert options.preserve_formatting is True
        assert options.ocr_enabled is False
        assert options.max_length is None
        assert options.clean_markdown is False

    def test_custom_values(self):
        """Test custom values for ConversionOptions"""
        options = ConversionOptions(
            js_rendering=True,
            timeout=30,
            extract_images=True,
            preserve_formatting=False,
            ocr_enabled=True,
            max_length=1000,
            clean_markdown=True,
        )
        
        assert options.js_rendering is True
        assert options.timeout == 30
        assert options.extract_images is True
        assert options.preserve_formatting is False
        assert options.ocr_enabled is True
        assert options.max_length == 1000
        assert options.clean_markdown is True


class TestConvertRequest:
    def test_valid_url_request(self):
        """Test valid request with URL"""
        request = ConvertRequest(url="https://example.com")
        
        assert request.url == "https://example.com"
        assert request.content is None
        assert request.text is None

    def test_valid_content_request(self):
        """Test valid request with content"""
        request = ConvertRequest(content="base64content", filename="test.pdf")
        
        assert request.content == "base64content"
        assert request.filename == "test.pdf"
        assert request.url is None
        assert request.text is None

    def test_valid_text_request(self):
        """Test valid request with text"""
        request = ConvertRequest(text="plain text content")
        
        assert request.text == "plain text content"
        assert request.url is None
        assert request.content is None

    def test_no_input_provided(self):
        """Test validation error when no input is provided"""
        with pytest.raises(ValueError, match="One of url, content, or text must be provided"):
            ConvertRequest()

    def test_multiple_inputs_provided(self):
        """Test validation error when multiple inputs are provided"""
        with pytest.raises(ValueError, match="Only one of url, content, or text can be provided"):
            ConvertRequest(url="https://example.com", text="content")

    def test_with_options(self):
        """Test request with options"""
        options = ConversionOptions(js_rendering=True)
        request = ConvertRequest(url="https://example.com", options=options)
        
        assert request.options == options
        assert request.options.js_rendering is True

    def test_with_source_format(self):
        """Test request with source format override"""
        request = ConvertRequest(
            content="base64content",
            filename="test.doc",
            source_format="application/pdf"
        )
        
        assert request.source_format == "application/pdf"


class TestConversionMetadata:
    def test_metadata_creation(self):
        """Test metadata creation with all fields"""
        metadata = ConversionMetadata(
            source_type="pdf",
            source_size=1024,
            markdown_size=2048,
            conversion_time_ms=150,
            detected_format="application/pdf",
            warnings=["Warning 1", "Warning 2"],
        )
        
        assert metadata.source_type == "pdf"
        assert metadata.source_size == 1024
        assert metadata.markdown_size == 2048
        assert metadata.conversion_time_ms == 150
        assert metadata.detected_format == "application/pdf"
        assert metadata.warnings == ["Warning 1", "Warning 2"]

    def test_metadata_with_empty_warnings(self):
        """Test metadata with default empty warnings"""
        metadata = ConversionMetadata(
            source_type="html",
            source_size=512,
            markdown_size=1024,
            conversion_time_ms=75,
            detected_format="text/html",
        )
        
        assert metadata.warnings == []


class TestConvertResponse:
    def test_response_creation(self):
        """Test direct response creation"""
        metadata = ConversionMetadata(
            source_type="pdf",
            source_size=1024,
            markdown_size=2048,
            conversion_time_ms=150,
            detected_format="application/pdf",
        )
        
        response = ConvertResponse(
            success=True,
            markdown="# Test Content",
            metadata=metadata,
            request_id="test-123",
        )
        
        assert response.success is True
        assert response.markdown == "# Test Content"
        assert response.metadata == metadata
        assert response.request_id == "test-123"

    def test_create_success_method(self):
        """Test create_success class method"""
        response = ConvertResponse.create_success(
            markdown="# Test Content",
            source_type="pdf",
            source_size=1024,
            conversion_time_ms=150,
            detected_format="application/pdf",
            warnings=["Warning 1"],
        )
        
        assert response.success is True
        assert response.markdown == "# Test Content"
        assert response.metadata.source_type == "pdf"
        assert response.metadata.source_size == 1024
        assert response.metadata.markdown_size == len("# Test Content".encode("utf-8"))
        assert response.metadata.conversion_time_ms == 150
        assert response.metadata.detected_format == "application/pdf"
        assert response.metadata.warnings == ["Warning 1"]
        assert response.request_id.startswith("req_")

    def test_create_success_without_warnings(self):
        """Test create_success without warnings"""
        response = ConvertResponse.create_success(
            markdown="# Test Content",
            source_type="html",
            source_size=512,
            conversion_time_ms=75,
            detected_format="text/html",
        )
        
        assert response.metadata.warnings == []


class TestErrorDetails:
    def test_error_details_creation(self):
        """Test error details creation"""
        details = ErrorDetails(
            detected_format="unknown/binary",
            supported_formats=["pdf", "docx", "html"],
            magic_bytes="89504e47",
        )
        
        assert details.detected_format == "unknown/binary"
        assert details.supported_formats == ["pdf", "docx", "html"]
        assert details.magic_bytes == "89504e47"

    def test_error_details_defaults(self):
        """Test error details with default None values"""
        details = ErrorDetails()
        
        assert details.detected_format is None
        assert details.supported_formats is None
        assert details.magic_bytes is None


class TestConvertError:
    def test_error_creation(self):
        """Test error creation with all fields"""
        error = ConvertError(
            code="UNSUPPORTED_FORMAT",
            message="File format not supported",
            details={"format": "unknown"},
            suggestions=["Try a different format"],
        )
        
        assert error.code == "UNSUPPORTED_FORMAT"
        assert error.message == "File format not supported"
        assert error.details == {"format": "unknown"}
        assert error.suggestions == ["Try a different format"]

    def test_error_minimal(self):
        """Test error creation with minimal fields"""
        error = ConvertError(
            code="INVALID_INPUT",
            message="Invalid input provided",
        )
        
        assert error.code == "INVALID_INPUT"
        assert error.message == "Invalid input provided"
        assert error.details is None
        assert error.suggestions is None


class TestErrorResponse:
    def test_error_response_creation(self):
        """Test direct error response creation"""
        error = ConvertError(
            code="TEST_ERROR",
            message="Test error message",
        )
        
        response = ErrorResponse(
            error=error,
            request_id="error-123",
        )
        
        assert response.success is False
        assert response.error == error
        assert response.request_id == "error-123"

    def test_create_error_method(self):
        """Test create_error class method"""
        response = ErrorResponse.create_error(
            code="VALIDATION_ERROR",
            message="Input validation failed",
            details={"field": "url"},
            suggestions=["Check URL format"],
        )
        
        assert response.success is False
        assert response.error.code == "VALIDATION_ERROR"
        assert response.error.message == "Input validation failed"
        assert response.error.details == {"field": "url"}
        assert response.error.suggestions == ["Check URL format"]
        assert response.request_id.startswith("req_")

    def test_create_error_minimal(self):
        """Test create_error with minimal parameters"""
        response = ErrorResponse.create_error(
            code="GENERIC_ERROR",
            message="Something went wrong",
        )
        
        assert response.error.details is None
        assert response.error.suggestions is None


class TestFormatCapabilities:
    def test_format_capabilities_creation(self):
        """Test format capabilities creation"""
        capabilities = FormatCapabilities(
            mime_types=["application/pdf", "application/x-pdf"],
            extensions=[".pdf"],
            features=["text_extraction", "metadata"],
            max_size_mb=50,
        )
        
        assert capabilities.mime_types == ["application/pdf", "application/x-pdf"]
        assert capabilities.extensions == [".pdf"]
        assert capabilities.features == ["text_extraction", "metadata"]
        assert capabilities.max_size_mb == 50


class TestFormatsResponse:
    def test_formats_response_creation(self):
        """Test formats response creation"""
        pdf_caps = FormatCapabilities(
            mime_types=["application/pdf"],
            extensions=[".pdf"],
            features=["text_extraction"],
            max_size_mb=50,
        )
        
        response = FormatsResponse(
            formats={"pdf": pdf_caps}
        )
        
        assert "pdf" in response.formats
        assert response.formats["pdf"] == pdf_caps


class TestHealthResponse:
    def test_health_response_creation(self):
        """Test health response creation"""
        response = HealthResponse(
            status="healthy",
            version="1.0.0",
            uptime_seconds=3600,
            conversions_last_hour=42,
        )
        
        assert response.status == "healthy"
        assert response.version == "1.0.0"
        assert response.uptime_seconds == 3600
        assert response.conversions_last_hour == 42

    def test_health_response_default_conversions(self):
        """Test health response with default conversions"""
        response = HealthResponse(
            status="healthy",
            version="1.0.0",
            uptime_seconds=3600,
        )
        
        assert response.conversions_last_hour == 0