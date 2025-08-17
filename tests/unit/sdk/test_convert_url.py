"""
Unit tests for URL conversion functionality.
"""

import pytest
from unittest.mock import AsyncMock, patch

from md_server.sdk import MDConverter
from md_server.sdk.exceptions import InvalidInputError, NetworkError


class TestURLConversion:
    """Test cases for URL conversion methods."""
    
    @pytest.mark.asyncio
    async def test_convert_valid_url(self):
        """Test converting a valid URL (mocked response)."""
        converter = MDConverter()
        
        # Mock the URL converter to avoid actual network calls
        with patch.object(converter._url_converter, 'convert_url', new_callable=AsyncMock) as mock_convert:
            mock_convert.return_value = "# Mocked Content\n\nThis is mocked markdown."
            
            result = await converter.convert_url("https://example.com")
            
            assert result.success is True
            assert "Mocked Content" in result.markdown
            assert result.metadata.source_type == "url"
            assert result.metadata.detected_format == "text/html"
            mock_convert.assert_called_once_with("https://example.com", False)
    
    @pytest.mark.asyncio
    async def test_convert_url_with_js_rendering(self):
        """Test URL conversion with JavaScript rendering enabled."""
        converter = MDConverter()
        
        with patch.object(converter._url_converter, 'convert_url', new_callable=AsyncMock) as mock_convert:
            mock_convert.return_value = "# JS Rendered Content"
            
            result = await converter.convert_url("https://example.com", js_rendering=True)
            
            assert result.success is True
            mock_convert.assert_called_once_with("https://example.com", True)
    
    @pytest.mark.asyncio
    async def test_convert_url_with_default_js_setting(self):
        """Test URL conversion uses default JS rendering setting."""
        converter = MDConverter(js_rendering=True)
        
        with patch.object(converter._url_converter, 'convert_url', new_callable=AsyncMock) as mock_convert:
            mock_convert.return_value = "# Content"
            
            result = await converter.convert_url("https://example.com")
            
            assert result.success is True
            mock_convert.assert_called_once_with("https://example.com", True)
    
    @pytest.mark.asyncio
    async def test_convert_invalid_url(self):
        """Test URL conversion with invalid URL."""
        converter = MDConverter()
        
        with pytest.raises(InvalidInputError, match="Invalid URL format"):
            await converter.convert_url("not-a-valid-url")
    
    @pytest.mark.asyncio
    async def test_convert_empty_url(self):
        """Test URL conversion with empty URL."""
        converter = MDConverter()
        
        with pytest.raises(InvalidInputError, match="URL cannot be empty"):
            await converter.convert_url("")
    
    @pytest.mark.asyncio
    async def test_convert_non_http_url(self):
        """Test URL conversion with non-HTTP URL."""
        converter = MDConverter()
        
        with pytest.raises(InvalidInputError, match="Only HTTP/HTTPS URLs allowed"):
            await converter.convert_url("ftp://example.com")
    
    @pytest.mark.asyncio
    async def test_convert_url_network_error(self):
        """Test URL conversion with network error."""
        converter = MDConverter()
        
        with patch.object(converter._url_converter, 'convert_url', side_effect=NetworkError("Connection failed")):
            with pytest.raises(NetworkError, match="Connection failed"):
                await converter.convert_url("https://example.com")
    
    @pytest.mark.asyncio
    async def test_convert_url_processing_time(self):
        """Test that URL conversion tracks processing time."""
        converter = MDConverter()
        
        with patch.object(converter._url_converter, 'convert_url', new_callable=AsyncMock) as mock_convert:
            mock_convert.return_value = "# Content"
            
            result = await converter.convert_url("https://example.com")
            
            assert result.metadata.processing_time > 0
            assert result.metadata.processing_time < 1.0  # Should be very fast for mocked call
    
    @pytest.mark.asyncio
    async def test_convert_url_metadata(self):
        """Test URL conversion metadata is correct."""
        converter = MDConverter()
        
        url = "https://example.com/test"
        markdown_content = "# Test Content\n\nThis is test markdown."
        
        with patch.object(converter._url_converter, 'convert_url', new_callable=AsyncMock) as mock_convert:
            mock_convert.return_value = markdown_content
            
            result = await converter.convert_url(url)
            
            assert result.metadata.source_type == "url"
            assert result.metadata.source_size == len(url)
            assert result.metadata.markdown_size == len(markdown_content.encode())
            assert result.metadata.detected_format == "text/html"
            assert result.request_id.startswith("req_")