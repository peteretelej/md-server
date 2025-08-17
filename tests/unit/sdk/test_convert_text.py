"""
Unit tests for text conversion functionality.
"""

import pytest

from md_server.sdk import MDConverter
from md_server.sdk.exceptions import InvalidInputError, FileSizeError


class TestTextConversion:
    """Test cases for text conversion methods."""
    
    @pytest.mark.asyncio
    async def test_convert_html_text(self):
        """Test converting HTML text to markdown."""
        converter = MDConverter()
        
        html_text = '<h1>Test Title</h1><p>This is a test paragraph with <strong>bold</strong> text.</p>'
        
        result = await converter.convert_text(html_text, "text/html")
        
        assert result.success is True
        assert "Test Title" in result.markdown
        assert "**bold**" in result.markdown
        assert result.metadata.source_type == "text"
        assert result.metadata.detected_format == "text/html"
    
    @pytest.mark.asyncio
    async def test_convert_plain_text(self):
        """Test converting plain text to markdown."""
        converter = MDConverter()
        
        plain_text = "This is plain text.\n\nWith multiple paragraphs."
        
        result = await converter.convert_text(plain_text, "text/plain")
        
        assert result.success is True
        assert "plain text" in result.markdown
        assert result.metadata.detected_format == "text/plain"
    
    @pytest.mark.asyncio
    async def test_convert_markdown_text(self):
        """Test converting markdown text (should pass through)."""
        converter = MDConverter()
        
        markdown_text = "# Markdown Title\n\nThis is **already** markdown."
        
        result = await converter.convert_text(markdown_text, "text/markdown")
        
        assert result.success is True
        assert result.markdown == markdown_text  # Should be unchanged
        assert result.metadata.detected_format == "text/markdown"
    
    @pytest.mark.asyncio
    async def test_convert_json_text(self):
        """Test converting JSON text to markdown."""
        converter = MDConverter()
        
        json_text = '{"title": "Test", "content": "This is JSON content"}'
        
        result = await converter.convert_text(json_text, "application/json")
        
        assert result.success is True
        assert result.metadata.detected_format == "application/json"
    
    @pytest.mark.asyncio
    async def test_convert_xml_text(self):
        """Test converting XML text to markdown."""
        converter = MDConverter()
        
        xml_text = '<?xml version="1.0"?><doc><title>Test</title><content>XML content</content></doc>'
        
        result = await converter.convert_text(xml_text, "application/xml")
        
        assert result.success is True
        assert result.metadata.detected_format == "application/xml"
    
    @pytest.mark.asyncio
    async def test_convert_text_with_cleaning(self):
        """Test text conversion with markdown cleaning."""
        converter = MDConverter(clean_markdown=True)
        
        html_text = '<h1>Title</h1>\n\n\n<p>Content</p>\n\n\n\n'
        
        result = await converter.convert_text(html_text, "text/html")
        
        assert result.success is True
        # Check that excessive whitespace was cleaned
        assert result.markdown.count('\n\n\n') == 0
    
    @pytest.mark.asyncio
    async def test_convert_text_invalid_mime_type(self):
        """Test text conversion with invalid MIME type."""
        converter = MDConverter()
        
        with pytest.raises(InvalidInputError, match="MIME type must contain"):
            await converter.convert_text("test", "invalid-mime-type")
    
    @pytest.mark.asyncio
    async def test_convert_text_empty_mime_type(self):
        """Test text conversion with empty MIME type."""
        converter = MDConverter()
        
        with pytest.raises(InvalidInputError, match="MIME type cannot be empty"):
            await converter.convert_text("test", "")
    
    @pytest.mark.asyncio
    async def test_convert_text_size_limit(self):
        """Test text conversion with size limit exceeded."""
        converter = MDConverter(max_file_size_mb=0.001)  # 1KB limit
        
        large_text = "x" * 2048  # 2KB text
        
        with pytest.raises(FileSizeError, match="exceeds limit"):
            await converter.convert_text(large_text, "text/plain")
    
    @pytest.mark.asyncio
    async def test_convert_empty_text(self):
        """Test converting empty text."""
        converter = MDConverter()
        
        result = await converter.convert_text("", "text/plain")
        
        assert result.success is True
        assert result.metadata.source_size == 0
    
    @pytest.mark.asyncio
    async def test_convert_text_mime_type_validation(self):
        """Test MIME type validation and normalization."""
        converter = MDConverter()
        
        # Test case insensitive MIME type handling
        result = await converter.convert_text("<h1>Test</h1>", "TEXT/HTML")
        
        assert result.success is True
        assert result.metadata.detected_format == "text/html"  # Should be normalized to lowercase
    
    @pytest.mark.asyncio
    async def test_convert_text_processing_time(self):
        """Test that text conversion tracks processing time."""
        converter = MDConverter()
        
        html_text = '<h1>Test</h1><p>Content</p>'
        
        result = await converter.convert_text(html_text, "text/html")
        
        assert result.metadata.processing_time > 0
        assert result.metadata.processing_time < 5.0  # Should be fast for small text
    
    @pytest.mark.asyncio
    async def test_convert_text_metadata(self):
        """Test text conversion metadata is complete."""
        converter = MDConverter()
        
        text = '<h1>Test</h1><p>This is test content.</p>'
        mime_type = "text/html"
        
        result = await converter.convert_text(text, mime_type)
        
        assert result.metadata.source_type == "text"
        assert result.metadata.source_size == len(text.encode())
        assert result.metadata.markdown_size > 0
        assert result.metadata.processing_time > 0
        assert result.metadata.detected_format == mime_type
        assert result.request_id.startswith("req_")