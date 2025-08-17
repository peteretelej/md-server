"""
Unit tests for content conversion functionality.
"""

import pytest

from md_server.sdk import MDConverter
from md_server.sdk.exceptions import FileSizeError


class TestContentConversion:
    """Test cases for content conversion methods."""
    
    @pytest.mark.asyncio
    async def test_convert_html_content(self):
        """Test converting HTML content to markdown."""
        converter = MDConverter()
        
        html_content = b'<h1>Test Title</h1><p>This is a test paragraph with <strong>bold</strong> text.</p>'
        
        result = await converter.convert_content(html_content, filename="test.html")
        
        assert result.success is True
        assert "Test Title" in result.markdown
        assert "**bold**" in result.markdown
        assert result.metadata.source_type == "content"
        assert result.metadata.detected_format == "text/html"
        assert result.metadata.source_size == len(html_content)
    
    @pytest.mark.asyncio
    async def test_convert_text_content(self):
        """Test converting plain text content to markdown."""
        converter = MDConverter()
        
        text_content = b"This is plain text content.\n\nWith multiple lines."
        
        result = await converter.convert_content(text_content, filename="test.txt")
        
        assert result.success is True
        assert "plain text content" in result.markdown
        assert result.metadata.detected_format == "text/plain"
    
    @pytest.mark.asyncio
    async def test_convert_content_without_filename(self):
        """Test converting content without filename hint."""
        converter = MDConverter()
        
        html_content = b'<html><body><h1>Title</h1></body></html>'
        
        result = await converter.convert_content(html_content)
        
        assert result.success is True
        assert result.metadata.detected_format == "text/html"
    
    @pytest.mark.asyncio
    async def test_convert_binary_content(self):
        """Test converting binary content."""
        converter = MDConverter()
        
        # Create PDF-like content
        pdf_content = b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n' + b'x' * 100
        
        result = await converter.convert_content(pdf_content, filename="test.pdf")
        
        assert result.success is True
        assert result.metadata.detected_format == "application/pdf"
        assert result.metadata.source_size == len(pdf_content)
    
    @pytest.mark.asyncio
    async def test_convert_content_with_cleaning(self):
        """Test content conversion with markdown cleaning."""
        converter = MDConverter(clean_markdown=True)
        
        html_content = b'<h1>Title</h1>\n\n\n<p>Content</p>\n\n\n\n'
        
        result = await converter.convert_content(html_content, filename="test.html")
        
        assert result.success is True
        # Check that excessive whitespace was cleaned
        assert result.markdown.count('\n\n\n') == 0
    
    @pytest.mark.asyncio
    async def test_convert_content_size_limit(self):
        """Test content conversion with size limit exceeded."""
        converter = MDConverter(max_file_size_mb=0.001)  # 1KB limit
        
        large_content = b"x" * 2048  # 2KB content
        
        with pytest.raises(FileSizeError, match="exceeds limit"):
            await converter.convert_content(large_content)
    
    @pytest.mark.asyncio
    async def test_convert_empty_content(self):
        """Test converting empty content."""
        converter = MDConverter()
        
        result = await converter.convert_content(b"", filename="empty.txt")
        
        assert result.success is True
        assert result.metadata.source_size == 0
    
    @pytest.mark.asyncio
    async def test_convert_content_format_detection(self):
        """Test content format detection with various file types."""
        converter = MDConverter()
        
        test_cases = [
            (b'%PDF-1.4', "test.pdf", "application/pdf"),
            (b'PK\x03\x04', "test.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            (b'\x89PNG\r\n\x1a\n', "test.png", "image/png"),
            (b'\xff\xd8\xff', "test.jpg", "image/jpeg"),
        ]
        
        for content, filename, expected_format in test_cases:
            content_with_padding = content + b'x' * 50  # Add some content
            result = await converter.convert_content(content_with_padding, filename=filename)
            
            assert result.success is True
            assert result.metadata.detected_format == expected_format
    
    @pytest.mark.asyncio
    async def test_convert_content_processing_time(self):
        """Test that content conversion tracks processing time."""
        converter = MDConverter()
        
        html_content = b'<h1>Test</h1><p>Content</p>'
        
        result = await converter.convert_content(html_content, filename="test.html")
        
        assert result.metadata.processing_time > 0
        assert result.metadata.processing_time < 5.0  # Should be fast for small content
    
    @pytest.mark.asyncio
    async def test_convert_content_metadata(self):
        """Test content conversion metadata is complete."""
        converter = MDConverter()
        
        content = b'<h1>Test</h1><p>This is test content.</p>'
        filename = "test.html"
        
        result = await converter.convert_content(content, filename=filename)
        
        assert result.metadata.source_type == "content"
        assert result.metadata.source_size == len(content)
        assert result.metadata.markdown_size > 0
        assert result.metadata.processing_time > 0
        assert result.metadata.detected_format == "text/html"
        assert result.request_id.startswith("req_")