"""
Comprehensive tests for SDK models and validation.

This file consolidates all model testing including validation, serialization,
edge cases, and data integrity across the SDK data structures.
"""

import pytest
from datetime import datetime
from typing import List, Optional
import json

from md_server.sdk.models import (
    ConversionMetadata, 
    ConversionResult, 
    ConversionOptions
)
# Note: Validation is done in validators.py, not in models
# from md_server.sdk.exceptions import ValidationError


class TestConversionMetadata:
    """Test cases for ConversionMetadata model."""
    
    def test_create_with_required_fields(self):
        """Test creating metadata with all required fields."""
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
        assert metadata.warnings == []  # Default empty list
    
    def test_create_with_warnings(self):
        """Test creating metadata with warnings."""
        warnings = ["OCR quality low", "Some images skipped", "Large file truncated"]
        metadata = ConversionMetadata(
            source_type="pdf",
            source_size=2048,
            markdown_size=1024,
            processing_time=1.2,
            detected_format="application/pdf",
            warnings=warnings
        )
        
        assert metadata.warnings == warnings
        assert len(metadata.warnings) == 3
    
    @pytest.mark.parametrize("source_type", [
        "file", "url", "content", "text", "stream"
    ])
    def test_valid_source_types(self, source_type):
        """Test all valid source types."""
        metadata = ConversionMetadata(
            source_type=source_type,
            source_size=100,
            markdown_size=50,
            processing_time=0.1,
            detected_format="text/plain"
        )
        assert metadata.source_type == source_type
    
    def test_negative_sizes_accepted(self):
        """Test that negative sizes are accepted (validation happens elsewhere)."""
        metadata = ConversionMetadata(
            source_type="file",
            source_size=-1,  # Negative size - model accepts it
            markdown_size=50,
            processing_time=0.1,
            detected_format="text/plain"
        )
        assert metadata.source_size == -1
        
        metadata = ConversionMetadata(
            source_type="file",
            source_size=100,
            markdown_size=-1,  # Negative size - model accepts it
            processing_time=0.1,
            detected_format="text/plain"
        )
        assert metadata.markdown_size == -1
    
    def test_negative_processing_time_accepted(self):
        """Test that negative processing time is accepted (validation happens elsewhere)."""
        metadata = ConversionMetadata(
            source_type="file",
            source_size=100,
            markdown_size=50,
            processing_time=-0.1,  # Negative time - model accepts it
            detected_format="text/plain"
        )
        assert metadata.processing_time == -0.1
    
    def test_empty_detected_format_accepted(self):
        """Test that empty detected format is accepted (validation happens elsewhere)."""
        metadata = ConversionMetadata(
            source_type="file",
            source_size=100,
            markdown_size=50,
            processing_time=0.1,
            detected_format=""  # Empty format - model accepts it
        )
        assert metadata.detected_format == ""
    
    def test_dataclass_fields(self):
        """Test that all expected fields are present."""
        metadata = ConversionMetadata(
            source_type="file",
            source_size=1024,
            markdown_size=512,
            processing_time=0.5,
            detected_format="application/pdf",
            warnings=["Warning 1", "Warning 2"]
        )
        
        # Verify all fields are accessible
        assert hasattr(metadata, 'source_type')
        assert hasattr(metadata, 'source_size')
        assert hasattr(metadata, 'markdown_size')
        assert hasattr(metadata, 'processing_time')
        assert hasattr(metadata, 'detected_format')
        assert hasattr(metadata, 'warnings')


class TestConversionResult:
    """Test cases for ConversionResult model."""
    
    def test_create_successful_result(self):
        """Test creating a successful conversion result."""
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
        assert result.success is True  # Default value
        assert result.request_id.startswith("req_")  # Auto-generated
        assert len(result.request_id) > 20  # Should be substantial UUID
    
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
        assert result.markdown == ""
    
    def test_request_id_uniqueness(self):
        """Test that request IDs are unique when auto-generated."""
        metadata = ConversionMetadata(
            source_type="text",
            source_size=10,
            markdown_size=5,
            processing_time=0.01,
            detected_format="text/plain"
        )
        
        results = []
        for _ in range(100):
            result = ConversionResult(markdown="Test", metadata=metadata)
            results.append(result.request_id)
        
        # All request IDs should be unique
        assert len(set(results)) == 100
        
        # All should have proper format
        for request_id in results:
            assert request_id.startswith("req_")
            assert len(request_id) > 20
    
    def test_result_validation(self):
        """Test validation of result fields."""
        metadata = ConversionMetadata(
            source_type="text",
            source_size=10,
            markdown_size=5,
            processing_time=0.01,
            detected_format="text/plain"
        )
        
        # Valid result
        result = ConversionResult(markdown="# Valid", metadata=metadata)
        assert result.markdown == "# Valid"
        
        # Markdown can be empty for failed conversions
        result = ConversionResult(markdown="", metadata=metadata, success=False)
        assert result.markdown == ""
        assert result.success is False
    
    def test_dataclass_structure(self):
        """Test result dataclass structure."""
        metadata = ConversionMetadata(
            source_type="file",
            source_size=100,
            markdown_size=50,
            processing_time=0.1,
            detected_format="text/html"
        )
        
        result = ConversionResult(
            markdown="# Title\n\nContent",
            metadata=metadata,
            success=True,
            request_id="req_test_123"
        )
        
        # Verify all fields are accessible
        assert hasattr(result, 'markdown')
        assert hasattr(result, 'metadata')
        assert hasattr(result, 'success')
        assert hasattr(result, 'request_id')
        
        assert result.markdown == "# Title\n\nContent"
        assert result.success is True
        assert result.request_id == "req_test_123"


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
    
    def test_extreme_values_accepted(self):
        """Test extreme values are accepted (validation happens elsewhere)."""
        options = ConversionOptions(
            timeout=-1,  # Negative timeout accepted
            max_file_size_mb=0  # Zero size accepted
        )
        
        assert options.timeout == -1
        assert options.max_file_size_mb == 0
        
        # Test very large values
        options = ConversionOptions(
            timeout=3600,  # 1 hour
            max_file_size_mb=1000  # 1GB
        )
        
        assert options.timeout == 3600
        assert options.max_file_size_mb == 1000
    
    def test_dataclass_mutability(self):
        """Test that options are mutable dataclass instances."""
        options = ConversionOptions(timeout=30)
        
        # Should be able to modify fields
        options.timeout = 60
        assert options.timeout == 60



class TestModelEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_markdown_result(self):
        """Test result with empty markdown."""
        metadata = ConversionMetadata(
            source_type="file",
            source_size=100,
            markdown_size=0,  # Empty output
            processing_time=0.1,
            detected_format="application/octet-stream"
        )
        
        result = ConversionResult(
            markdown="",  # Empty markdown
            metadata=metadata,
            success=False  # Failed conversion
        )
        
        assert result.markdown == ""
        assert result.success is False
    
    def test_very_large_metadata_values(self):
        """Test metadata with very large values."""
        metadata = ConversionMetadata(
            source_type="file",
            source_size=1024 * 1024 * 1024,  # 1GB
            markdown_size=100 * 1024 * 1024,  # 100MB
            processing_time=3600.5,  # 1+ hour
            detected_format="application/pdf"
        )
        
        assert metadata.source_size == 1024 * 1024 * 1024
        assert metadata.processing_time == 3600.5
    
    def test_unicode_content_handling(self):
        """Test handling of Unicode content in models."""
        # Unicode in markdown
        result = ConversionResult(
            markdown="# 测试标题\n\n这是中文内容 🚀",
            metadata=ConversionMetadata(
                source_type="text",
                source_size=50,
                markdown_size=30,
                processing_time=0.1,
                detected_format="text/plain"
            )
        )
        
        assert "测试标题" in result.markdown
        assert "🚀" in result.markdown
        
        # Should handle Unicode content correctly
        assert "测试标题" in result.markdown
    
    def test_very_long_warnings_list(self):
        """Test metadata with many warnings."""
        warnings = [f"Warning {i}" for i in range(1000)]
        
        metadata = ConversionMetadata(
            source_type="file",
            source_size=1000,
            markdown_size=500,
            processing_time=2.0,
            detected_format="application/pdf",
            warnings=warnings
        )
        
        assert len(metadata.warnings) == 1000
        assert metadata.warnings[0] == "Warning 0"
        assert metadata.warnings[999] == "Warning 999"
    
    def test_floating_point_precision(self):
        """Test floating point precision in processing time."""
        metadata = ConversionMetadata(
            source_type="text",
            source_size=100,
            markdown_size=50,
            processing_time=0.123456789,  # High precision
            detected_format="text/plain"
        )
        
        # Should preserve reasonable precision
        assert abs(metadata.processing_time - 0.123456789) < 1e-6
    
    def test_model_equality(self):
        """Test model equality comparison."""
        metadata1 = ConversionMetadata(
            source_type="file",
            source_size=100,
            markdown_size=50,
            processing_time=0.1,
            detected_format="text/plain"
        )
        
        metadata2 = ConversionMetadata(
            source_type="file",
            source_size=100,
            markdown_size=50,
            processing_time=0.1,
            detected_format="text/plain"
        )
        
        assert metadata1 == metadata2
        
        # Different values should not be equal
        metadata3 = ConversionMetadata(
            source_type="file",
            source_size=200,  # Different size
            markdown_size=50,
            processing_time=0.1,
            detected_format="text/plain"
        )
        
        assert metadata1 != metadata3