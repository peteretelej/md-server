"""
Tests for sync API wrappers.
"""

import asyncio
import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from md_server.sdk import MDConverter, RemoteMDConverter
from md_server.sdk.models import ConversionResult, ConversionMetadata
from md_server.sdk.sync import sync_wrapper, get_or_create_event_loop


class TestSyncWrapper:
    """Test the sync_wrapper function."""
    
    async def dummy_async_function(self, value):
        """Dummy async function for testing."""
        await asyncio.sleep(0.01)
        return f"result: {value}"
    
    def test_sync_wrapper_basic(self):
        """Test basic sync wrapper functionality."""
        
        async def dummy_async_function(value):
            await asyncio.sleep(0.01)
            return f"result: {value}"
        
        sync_func = sync_wrapper(dummy_async_function)
        result = sync_func("test")
        assert result == "result: test"
    
    def test_sync_wrapper_with_exception(self):
        """Test sync wrapper propagates exceptions."""
        async def failing_func():
            raise ValueError("test error")
        
        sync_func = sync_wrapper(failing_func)
        with pytest.raises(ValueError, match="test error"):
            sync_func()
    
    def test_get_or_create_event_loop(self):
        """Test event loop creation."""
        loop = get_or_create_event_loop()
        assert isinstance(loop, asyncio.AbstractEventLoop)


class TestMDConverterSync:
    """Test sync methods of MDConverter."""
    
    @pytest.fixture
    def converter(self):
        """Create a converter instance for testing."""
        return MDConverter(timeout=5, max_file_size_mb=1)
    
    def test_convert_file_sync(self, converter):
        """Test synchronous file conversion."""
        # Mock the async method
        expected_result = ConversionResult(
            markdown="# Test",
            metadata=ConversionMetadata(
                source_type="pdf",
                source_size=1024,
                markdown_size=6,
                processing_time=0.1,
                detected_format="application/pdf"
            )
        )
        
        async def mock_async(*args, **kwargs):
            return expected_result
        
        # Patch the async method directly
        with patch.object(converter, 'convert_file', new=mock_async):
            result = converter.convert_file_sync("test.pdf")
            assert result.markdown == "# Test"
    
    def test_convert_url_sync(self, converter):
        """Test synchronous URL conversion."""
        expected_result = ConversionResult(
            markdown="# Web Page",
            metadata=ConversionMetadata(
                source_type="html",
                source_size=2048,
                markdown_size=11,
                processing_time=0.2,
                detected_format="text/html"
            )
        )
        
        async def mock_async(*args, **kwargs):
            return expected_result
        
        # Patch the async method directly
        with patch.object(converter, 'convert_url', new=mock_async):
            result = converter.convert_url_sync("https://example.com", js_rendering=True)
            assert result.markdown == "# Web Page"
    
    def test_convert_content_sync(self, converter):
        """Test synchronous content conversion."""
        expected_result = ConversionResult(
            markdown="# Content",
            metadata=ConversionMetadata(
                source_type="text",
                source_size=100,
                markdown_size=9,
                processing_time=0.05,
                detected_format="text/plain"
            )
        )
        
        async def mock_async(*args, **kwargs):
            return expected_result
        
        # Patch the async method directly
        with patch.object(converter, 'convert_content', new=mock_async):
            content = b"test content"
            result = converter.convert_content_sync(content, filename="test.txt")
            assert result.markdown == "# Content"
    
    def test_convert_text_sync(self, converter):
        """Test synchronous text conversion."""
        expected_result = ConversionResult(
            markdown="# HTML Title",
            metadata=ConversionMetadata(
                source_type="html",
                source_size=50,
                markdown_size=12,
                processing_time=0.03,
                detected_format="text/html"
            )
        )
        
        async def mock_async(*args, **kwargs):
            return expected_result
        
        # Patch the async method directly
        with patch.object(converter, 'convert_text', new=mock_async):
            result = converter.convert_text_sync("<h1>HTML Title</h1>", "text/html")
            assert result.markdown == "# HTML Title"


class TestRemoteMDConverterSync:
    """Test sync methods of RemoteMDConverter."""
    
    @pytest.fixture
    def remote_converter(self):
        """Create a remote converter instance for testing."""
        return RemoteMDConverter("http://localhost:8080")
    
    def test_convert_file_sync(self, remote_converter):
        """Test synchronous file conversion for remote client."""
        expected_result = ConversionResult(
            markdown="# Remote Test",
            metadata=ConversionMetadata(
                source_type="pdf",
                source_size=1024,
                markdown_size=13,
                processing_time=0.1,
                detected_format="application/pdf"
            )
        )
        
        async def mock_async(*args, **kwargs):
            return expected_result
        
        # Patch the async method directly
        with patch.object(remote_converter, 'convert_file', new=mock_async):
            result = remote_converter.convert_file_sync("test.pdf")
            assert result.markdown == "# Remote Test"
    
    def test_health_check_sync(self, remote_converter):
        """Test synchronous health check."""
        expected_result = {"status": "healthy", "version": "1.0.0"}
        
        async def mock_async(*args, **kwargs):
            return expected_result
        
        # Patch the async method directly
        with patch.object(remote_converter, 'health_check', new=mock_async):
            result = remote_converter.health_check_sync()
            assert result == expected_result
    
    def test_get_formats_sync(self, remote_converter):
        """Test synchronous format retrieval."""
        expected_result = {"formats": ["pdf", "docx", "html"]}
        
        async def mock_async(*args, **kwargs):
            return expected_result
        
        # Patch the async method directly
        with patch.object(remote_converter, 'get_formats', new=mock_async):
            result = remote_converter.get_formats_sync()
            assert result == expected_result


class TestContextManagers:
    """Test context manager support."""
    
    def test_sync_context_manager(self):
        """Test sync context manager."""
        with MDConverter() as converter:
            assert isinstance(converter, MDConverter)
    
    async def test_async_context_manager(self):
        """Test async context manager."""
        async with MDConverter() as converter:
            assert isinstance(converter, MDConverter)
    
    def test_sync_context_manager_with_exception(self):
        """Test sync context manager handles exceptions."""
        with pytest.raises(ValueError):
            with MDConverter() as converter:
                raise ValueError("test exception")
    
    async def test_async_context_manager_with_exception(self):
        """Test async context manager handles exceptions."""
        with pytest.raises(ValueError):
            async with MDConverter() as converter:
                raise ValueError("test exception")


class TestAsyncSyncInteroperability:
    """Test that async and sync APIs work together."""
    
    def test_sync_wrapper_works_independently(self):
        """Test sync wrapper works independently."""
        converter = MDConverter()
        
        expected_result = ConversionResult(
            markdown="# Test",
            metadata=ConversionMetadata(
                source_type="html",
                source_size=20,
                markdown_size=6,
                processing_time=0.01,
                detected_format="text/html"
            )
        )
        
        async def mock_async(*args, **kwargs):
            return expected_result
        
        # Patch the async method directly
        with patch.object(converter, 'convert_text', new=mock_async):
            result = converter.convert_text_sync("<h1>Test</h1>", "text/html")
            assert result.markdown == "# Test"
    
    def test_multiple_sync_calls(self):
        """Test multiple sync calls work correctly."""
        converter = MDConverter()
        
        expected_result = ConversionResult(
            markdown="# Test",
            metadata=ConversionMetadata(
                source_type="html",
                source_size=20,
                markdown_size=6,
                processing_time=0.01,
                detected_format="text/html"
            )
        )
        
        async def mock_async(*args, **kwargs):
            return expected_result
        
        # Patch the async method directly
        with patch.object(converter, 'convert_text', new=mock_async):
            # Multiple calls should work
            result1 = converter.convert_text_sync("<h1>Test1</h1>", "text/html")
            result2 = converter.convert_text_sync("<h1>Test2</h1>", "text/html")
            
            assert result1.markdown == "# Test"
            assert result2.markdown == "# Test"