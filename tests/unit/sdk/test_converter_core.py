"""
Comprehensive tests for MDConverter core functionality.

This file consolidates testing for the core SDK converter, covering all conversion
methods with both unit and integration testing approaches.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from md_server.sdk import MDConverter, ConversionResult, ConversionMetadata
from md_server.sdk.exceptions import InvalidInputError, FileSizeError, ConversionError


class TestMDConverterCore:
    """Comprehensive converter tests with integration coverage."""
    
    @pytest.fixture
    def md_converter(self):
        """Standard converter instance for testing."""
        return MDConverter(timeout=10, max_file_size_mb=1)
    
    @pytest.fixture  
    def mock_converter(self):
        """Converter with mocked dependencies for unit testing."""
        return MDConverter()
    
    def test_converter_initialization(self):
        """Test converter initialization with various options."""
        # Default options
        converter = MDConverter()
        assert converter.options.ocr_enabled is False
        assert converter.options.js_rendering is False
        assert converter.options.timeout == 30
        assert converter.options.max_file_size_mb == 50
        assert converter.options.extract_images is False
        assert converter.options.preserve_formatting is True
        assert converter.options.clean_markdown is False
        
        # Custom options
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

    @pytest.mark.parametrize("method_name,input_data,expected_source_type", [
        ("convert_file", "test.pdf", "file"),
        ("convert_url", "https://example.com", "url"),
        ("convert_content", b"PDF data", "content"),
        ("convert_text", ("Hello World", "text/plain"), "text"),
    ])
    async def test_all_methods_return_conversion_result(self, md_converter, method_name, input_data, expected_source_type):
        """Parametrized test covering all conversion methods."""
        method = getattr(md_converter, method_name)
        
        # Mock the underlying converters
        with patch('md_server.sdk.utils.convert_content_async', return_value="# Mocked Content"), \
             patch.object(md_converter._url_converter, 'convert_url', return_value="# Mocked URL Content"):
            
            # Handle different input formats
            if method_name == "convert_file":
                # Create temporary file for file conversion
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                    f.write("Test content")
                    temp_path = Path(f.name)
                
                try:
                    result = await method(temp_path)
                finally:
                    temp_path.unlink()
                    
            elif method_name == "convert_text":
                result = await method(input_data[0], input_data[1])
            else:
                result = await method(input_data)
            
            # Verify result structure
            assert isinstance(result, ConversionResult)
            assert result.success is True
            assert result.request_id.startswith("req_")
            assert isinstance(result.metadata, ConversionMetadata)
            assert result.metadata.source_type == expected_source_type
            assert result.metadata.processing_time >= 0
            assert result.metadata.source_size >= 0
            assert result.metadata.markdown_size >= 0

    async def test_file_conversion_integration(self, md_converter, sample_files):
        """Test file conversion with real sample files."""
        for file_type, file_path in sample_files.items():
            if not file_path.exists():
                continue
                
            result = await md_converter.convert_file(file_path)
            
            assert result.success is True
            assert len(result.markdown) > 0
            assert result.metadata.source_type == "file"
            assert result.metadata.source_size > 0
            assert result.metadata.markdown_size > 0
            assert result.metadata.processing_time > 0
            
            # Verify format detection based on file extension
            if file_type == "pdf":
                assert "pdf" in result.metadata.detected_format.lower()
            elif file_type == "html":
                assert "html" in result.metadata.detected_format.lower()

    @pytest.mark.parametrize("file_type,content,expected_format", [
        ("html", b'<h1>Title</h1><p>Content</p>', "text/html"),
        ("text", b'Plain text content', "text/plain"),
        ("pdf", b'%PDF-1.4\nFake PDF content', "application/pdf"),
        ("docx", b'PK\x03\x04\nFake DOCX content', "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ("png", b'\x89PNG\r\n\x1a\nFake PNG', "image/png"),
        ("jpg", b'\xff\xd8\xff\nFake JPEG', "image/jpeg"),
    ])
    async def test_content_format_detection(self, md_converter, file_type, content, expected_format):
        """Test content format detection with various file types."""
        result = await md_converter.convert_content(content, filename=f"test.{file_type}")
        
        assert result.success is True
        assert result.metadata.detected_format == expected_format
        assert result.metadata.source_size == len(content)

    @pytest.mark.parametrize("mime_type,text_content", [
        ("text/html", "<h1>HTML Title</h1><p>HTML content</p>"),
        ("text/plain", "Plain text content"),
        ("text/markdown", "# Markdown Title\n\nMarkdown content"),
        ("application/json", '{"title": "JSON", "content": "JSON data"}'),
        ("application/xml", '<?xml version="1.0"?><doc><title>XML</title></doc>'),
    ])
    async def test_text_conversion_mime_types(self, md_converter, mime_type, text_content):
        """Test text conversion with various MIME types."""
        result = await md_converter.convert_text(text_content, mime_type)
        
        assert result.success is True
        assert result.metadata.detected_format == mime_type.lower()
        assert result.metadata.source_type == "text"
        assert result.metadata.source_size == len(text_content.encode())

    async def test_url_conversion_with_js_options(self, md_converter):
        """Test URL conversion with different JavaScript rendering options."""
        with patch.object(md_converter._url_converter, 'convert_url', new_callable=AsyncMock) as mock_convert:
            mock_convert.return_value = "# URL Content"
            
            # Test with default JS setting (False)
            result = await md_converter.convert_url("https://example.com")
            assert result.success is True
            mock_convert.assert_called_with("https://example.com", False)
            
            # Test with JS enabled
            result = await md_converter.convert_url("https://example.com", js_rendering=True)
            assert result.success is True
            mock_convert.assert_called_with("https://example.com", True)
            
            # Test with JS disabled override
            converter_with_js = MDConverter(js_rendering=True)
            with patch.object(converter_with_js._url_converter, 'convert_url', new_callable=AsyncMock) as mock_convert2:
                mock_convert2.return_value = "# URL Content"
                result = await converter_with_js.convert_url("https://example.com", js_rendering=False)
                assert result.success is True
                mock_convert2.assert_called_with("https://example.com", False)

    async def test_error_propagation_across_layers(self, md_converter):
        """Test how errors flow through the conversion system."""
        # Test file not found error
        with pytest.raises(InvalidInputError, match="File not found"):
            await md_converter.convert_file("/nonexistent/file.txt")
        
        # Test invalid URL error
        with pytest.raises(InvalidInputError):
            await md_converter.convert_url("not-a-valid-url")
        
        # Test invalid MIME type error (text with empty string is actually valid - just returns empty result)
        with pytest.raises(InvalidInputError):
            await md_converter.convert_text("content", "invalid-mime")

    async def test_size_limit_enforcement(self, md_converter):
        """Test file size limits are enforced across all methods."""
        # Small size limit for testing
        small_converter = MDConverter(max_file_size_mb=0.001)  # 1KB limit
        large_content = "x" * 2048  # 2KB content
        
        # Test file size limit
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(large_content)
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(FileSizeError):
                await small_converter.convert_file(temp_path)
        finally:
            temp_path.unlink()
        
        # Test content size limit
        with pytest.raises(FileSizeError):
            await small_converter.convert_content(large_content.encode())
        
        # Test text size limit
        with pytest.raises(FileSizeError):
            await small_converter.convert_text(large_content, "text/plain")

    async def test_markdown_cleaning_functionality(self, md_converter):
        """Test markdown cleaning options work across conversion types."""
        cleaner = MDConverter(clean_markdown=True)
        
        # Test with HTML that produces messy markdown
        messy_html = '<h1>Title</h1>\n\n\n<p>Content</p>\n\n\n\n'
        
        # Mock the content converter to return messy markdown
        with patch('md_server.sdk.utils.convert_text_with_mime_type_async') as mock_convert:
            mock_convert.return_value = "# Title\n\n\n\nContent\n\n\n\n"
            
            result = await cleaner.convert_text(messy_html, "text/html")
            
            # Verify cleaning removed excessive whitespace
            assert result.markdown.count('\n\n\n') == 0
            assert result.success is True

    async def test_processing_time_tracking(self, md_converter):
        """Test that processing time is accurately tracked."""
        # Small conversion should be fast
        result = await md_converter.convert_text("Hello", "text/plain")
        
        assert result.metadata.processing_time > 0
        assert result.metadata.processing_time < 5.0  # Should be very fast
        
        # Verify timestamp precision
        assert isinstance(result.metadata.processing_time, float)

    async def test_metadata_completeness(self, md_converter):
        """Test that conversion metadata is complete and accurate."""
        content = "# Test Content\n\nThis is test markdown."
        
        result = await md_converter.convert_text(content, "text/markdown")
        
        # Verify all metadata fields are populated
        assert result.metadata.source_type == "text"
        assert result.metadata.source_size == len(content.encode())
        assert result.metadata.markdown_size > 0
        assert result.metadata.processing_time > 0
        assert result.metadata.detected_format == "text/markdown"
        assert isinstance(result.metadata.warnings, list)
        
        # Verify request ID format
        assert result.request_id.startswith("req_")
        assert len(result.request_id) > 20  # Should be a proper UUID-like string

    async def test_concurrent_conversions(self, md_converter):
        """Test that converter handles concurrent operations correctly."""
        import asyncio
        
        # Run multiple conversions concurrently
        tasks = [
            md_converter.convert_text(f"Content {i}", "text/plain")
            for i in range(5)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Verify all conversions succeeded
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result.success is True
            assert f"Content {i}" in result.markdown
            assert result.request_id.startswith("req_")
            
        # Verify unique request IDs
        request_ids = [r.request_id for r in results]
        assert len(set(request_ids)) == 5  # All unique

    async def test_conversion_options_propagation(self, md_converter):
        """Test that conversion options are properly propagated."""
        # Test with various options
        options_to_test = [
            {"ocr_enabled": True},
            {"extract_images": True},
            {"preserve_formatting": False},
            {"timeout": 60},
        ]
        
        for options in options_to_test:
            converter = MDConverter(**options)
            
            # Verify options are stored correctly
            for key, value in options.items():
                assert getattr(converter.options, key) == value
            
            # Test conversion still works with custom options
            result = await converter.convert_text("Test", "text/plain")
            assert result.success is True

    def test_request_id_uniqueness(self, md_converter):
        """Test that request IDs are unique across conversions."""
        import uuid
        
        # Generate request IDs by creating multiple ConversionResult instances
        request_ids = set()
        for _ in range(100):
            from md_server.sdk.models import ConversionResult, ConversionMetadata
            
            metadata = ConversionMetadata(
                source_type="test",
                source_size=10,
                markdown_size=5,
                processing_time=0.01,
                detected_format="text/plain"
            )
            result = ConversionResult(markdown="Test", metadata=metadata)
            request_ids.add(result.request_id)
            
            # Verify format
            assert result.request_id.startswith("req_")
            # Verify it's a valid UUID after the prefix
            uuid_part = result.request_id[4:]  # Remove "req_" prefix
            uuid.UUID(uuid_part)  # Should not raise exception
        
        # All should be unique
        assert len(request_ids) == 100

