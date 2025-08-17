"""
Unit tests for SDK models.
"""

import pytest
from md_server.sdk.models import ConversionMetadata, ConversionResult, ConversionOptions


class TestConversionMetadata:
    """Test cases for ConversionMetadata model."""
    
    def test_create_with_required_fields(self):
        """Test creating metadata with required fields."""
        metadata = ConversionMetadata(
            source_type="file",
            source_size=1024,
            markdown_size=512,
            processing_time=0.5,
            detected_format="application/pdf"
        )
        
        assert metadata.source_type == "file"
        assert metadata.source_size == 1024
        assert metadata.markdown_size == 512
        assert metadata.processing_time == 0.5
        assert metadata.detected_format == "application/pdf"
        assert metadata.warnings == []
    
    def test_create_with_warnings(self):
        """Test creating metadata with warnings."""
        warnings = ["OCR quality low", "Some images skipped"]
        metadata = ConversionMetadata(
            source_type="pdf",
            source_size=2048,
            markdown_size=1024,
            processing_time=1.2,
            detected_format="application/pdf",
            warnings=warnings
        )
        
        assert metadata.warnings == warnings


class TestConversionResult:
    """Test cases for ConversionResult model."""
    
    def test_create_result(self):
        """Test creating a conversion result."""
        metadata = ConversionMetadata(
            source_type="file",
            source_size=1024,
            markdown_size=512,
            processing_time=0.5,
            detected_format="text/plain"
        )
        
        result = ConversionResult(
            markdown="# Test\n\nContent",
            metadata=metadata
        )
        
        assert result.markdown == "# Test\n\nContent"
        assert result.metadata == metadata
        assert result.success is True
        assert result.request_id.startswith("req_")
    
    def test_create_failed_result(self):
        """Test creating a failed conversion result."""
        metadata = ConversionMetadata(
            source_type="file",
            source_size=1024,
            markdown_size=0,
            processing_time=0.1,
            detected_format="application/octet-stream"
        )
        
        result = ConversionResult(
            markdown="",
            metadata=metadata,
            success=False,
            request_id="req_custom_id"
        )
        
        assert result.success is False
        assert result.request_id == "req_custom_id"


class TestConversionOptions:
    """Test cases for ConversionOptions model."""
    
    def test_create_with_defaults(self):
        """Test creating options with default values."""
        options = ConversionOptions()
        
        assert options.ocr_enabled is False
        assert options.js_rendering is False
        assert options.extract_images is False
        assert options.preserve_formatting is True
        assert options.clean_markdown is False
        assert options.timeout == 30
        assert options.max_file_size_mb == 50
    
    def test_create_with_custom_values(self):
        """Test creating options with custom values."""
        options = ConversionOptions(
            ocr_enabled=True,
            js_rendering=True,
            extract_images=True,
            preserve_formatting=False,
            clean_markdown=True,
            timeout=60,
            max_file_size_mb=100
        )
        
        assert options.ocr_enabled is True
        assert options.js_rendering is True
        assert options.extract_images is True
        assert options.preserve_formatting is False
        assert options.clean_markdown is True
        assert options.timeout == 60
        assert options.max_file_size_mb == 100