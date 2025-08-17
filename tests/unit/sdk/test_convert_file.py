"""
Unit tests for file conversion functionality.
"""

import pytest
import tempfile
from pathlib import Path

from md_server.sdk import MDConverter
from md_server.sdk.exceptions import InvalidInputError, FileSizeError


class TestFileConversion:
    """Test cases for file conversion methods."""
    
    @pytest.mark.asyncio
    async def test_convert_html_file(self):
        """Test converting HTML file to markdown."""
        converter = MDConverter()
        
        html_content = '<h1>Test Title</h1><p>This is a test paragraph with <strong>bold</strong> text.</p>'
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(html_content)
            temp_path = Path(f.name)
        
        try:
            result = await converter.convert_file(temp_path)
            
            assert result.success is True
            assert "Test Title" in result.markdown
            assert "**bold**" in result.markdown
            assert result.metadata.source_type == "file"
            assert result.metadata.detected_format == "text/html"
            assert result.metadata.source_size > 0
        finally:
            temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_convert_text_file(self):
        """Test converting plain text file to markdown."""
        converter = MDConverter()
        
        text_content = "This is a plain text file.\n\nWith multiple paragraphs."
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(text_content)
            temp_path = Path(f.name)
        
        try:
            result = await converter.convert_file(temp_path)
            
            assert result.success is True
            assert "plain text file" in result.markdown
            assert result.metadata.detected_format == "text/plain"
        finally:
            temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_convert_markdown_file(self):
        """Test converting markdown file (should pass through)."""
        converter = MDConverter()
        
        md_content = "# Markdown Title\n\nThis is **already** markdown."
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(md_content)
            temp_path = Path(f.name)
        
        try:
            result = await converter.convert_file(temp_path)
            
            assert result.success is True
            assert "Markdown Title" in result.markdown
            assert result.metadata.detected_format == "text/markdown"
        finally:
            temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_convert_file_with_options(self):
        """Test file conversion with cleaning options."""
        converter = MDConverter(clean_markdown=True)
        
        html_content = '<h1>Title</h1>\n\n\n<p>Content</p>\n\n\n\n'
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(html_content)
            temp_path = Path(f.name)
        
        try:
            result = await converter.convert_file(temp_path)
            
            assert result.success is True
            # Check that excessive whitespace was cleaned
            assert result.markdown.count('\n\n\n') == 0
        finally:
            temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_convert_file_not_found(self):
        """Test file conversion with non-existent file."""
        converter = MDConverter()
        
        with pytest.raises(InvalidInputError, match="File not found"):
            await converter.convert_file("/nonexistent/file.txt")
    
    @pytest.mark.asyncio
    async def test_convert_file_size_limit(self):
        """Test file conversion with size limit exceeded."""
        converter = MDConverter(max_file_size_mb=0.001)  # 1KB limit
        
        # Create a file larger than the limit
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("x" * 2048)  # 2KB file
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(FileSizeError, match="exceeds limit"):
                await converter.convert_file(temp_path)
        finally:
            temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_convert_binary_file(self):
        """Test converting a simple binary file."""
        converter = MDConverter()
        
        # Create a simple binary file
        binary_content = b'\x89PNG\r\n\x1a\n' + b'x' * 100  # PNG-like header
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            f.write(binary_content)
            temp_path = Path(f.name)
        
        try:
            result = await converter.convert_file(temp_path)
            
            assert result.success is True
            assert result.metadata.detected_format == "image/png"
            assert result.metadata.source_size == len(binary_content)
        finally:
            temp_path.unlink()