"""
Unit tests for MDConverter core functionality.
"""

import pytest
import tempfile
from pathlib import Path

from md_server.sdk import MDConverter, ConversionResult, ConversionMetadata
from md_server.sdk.exceptions import InvalidInputError, FileSizeError


class TestMDConverter:
    """Test cases for MDConverter class."""
    
    def test_init_with_defaults(self):
        """Test converter initialization with default values."""
        converter = MDConverter()
        
        assert converter.options.ocr_enabled is False
        assert converter.options.js_rendering is False
        assert converter.options.timeout == 30
        assert converter.options.max_file_size_mb == 50
        assert converter.options.extract_images is False
        assert converter.options.preserve_formatting is True
        assert converter.options.clean_markdown is False
    
    def test_init_with_custom_options(self):
        """Test converter initialization with custom options."""
        converter = MDConverter(
            ocr_enabled=True,
            js_rendering=True,
            timeout=60,
            max_file_size_mb=100,
            extract_images=True,
            preserve_formatting=False,
            clean_markdown=True,
            debug=True
        )
        
        assert converter.options.ocr_enabled is True
        assert converter.options.js_rendering is True
        assert converter.options.timeout == 60
        assert converter.options.max_file_size_mb == 100
        assert converter.options.extract_images is True
        assert converter.options.preserve_formatting is False
        assert converter.options.clean_markdown is True
    
    @pytest.mark.asyncio
    async def test_convert_file_success(self):
        """Test successful file conversion."""
        converter = MDConverter()
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test content")
            temp_path = Path(f.name)
        
        try:
            result = await converter.convert_file(temp_path)
            
            assert isinstance(result, ConversionResult)
            assert result.success is True
            assert result.request_id.startswith("req_")
            assert "Test content" in result.markdown
            assert isinstance(result.metadata, ConversionMetadata)
            assert result.metadata.source_type == "file"
            assert result.metadata.source_size > 0
            assert result.metadata.markdown_size > 0
            assert result.metadata.processing_time >= 0
        finally:
            temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_convert_file_not_found(self):
        """Test file conversion with non-existent file."""
        converter = MDConverter()
        
        with pytest.raises(InvalidInputError) as exc_info:
            await converter.convert_file("/nonexistent/file.txt")
        
        assert "File not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_convert_file_size_limit(self):
        """Test file conversion with size limit exceeded."""
        converter = MDConverter(max_file_size_mb=0.001)  # 1KB limit
        
        # Create a file larger than the limit
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("x" * 2048)  # 2KB file
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(FileSizeError) as exc_info:
                await converter.convert_file(temp_path)
            
            assert "exceeds limit" in str(exc_info.value)
        finally:
            temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_convert_url(self):
        """Test URL conversion."""
        converter = MDConverter()
        
        result = await converter.convert_url("https://example.com")
        
        assert isinstance(result, ConversionResult)
        assert result.success is True
        assert result.markdown  # Should have some content
        assert result.metadata.source_type == "url"
        assert result.metadata.detected_format == "text/html"
    
    @pytest.mark.asyncio
    async def test_convert_content(self):
        """Test content conversion."""
        converter = MDConverter()
        
        content = b"Test binary content"
        result = await converter.convert_content(content, filename="test.txt")
        
        assert isinstance(result, ConversionResult)
        assert result.success is True
        assert result.markdown  # Should have some content
        assert result.metadata.source_type == "content"
        assert result.metadata.source_size == len(content)
    
    @pytest.mark.asyncio
    async def test_convert_content_size_limit(self):
        """Test content conversion with size limit exceeded."""
        converter = MDConverter(max_file_size_mb=0.001)  # 1KB limit
        
        content = b"x" * 2048  # 2KB content
        
        with pytest.raises(FileSizeError):
            await converter.convert_content(content)
    
    @pytest.mark.asyncio
    async def test_convert_text(self):
        """Test text conversion."""
        converter = MDConverter()
        
        text = "<h1>Test HTML</h1><p>Content</p>"
        result = await converter.convert_text(text, "text/html")
        
        assert isinstance(result, ConversionResult)
        assert result.success is True
        assert result.markdown  # Should have some content
        assert result.metadata.source_type == "text"
        assert result.metadata.detected_format == "text/html"
    
