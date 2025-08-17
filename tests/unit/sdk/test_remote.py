"""
Integration tests for RemoteMDConverter using real md-server instance.
"""

import asyncio
import socket
import subprocess
import tempfile
import time
from pathlib import Path

import pytest

from md_server.sdk.remote import RemoteMDConverter
from md_server.sdk.models import ConversionResult
from md_server.sdk.exceptions import (
    ConversionError, 
    NetworkError, 
    TimeoutError, 
    InvalidInputError
)


def find_free_port(start_port: int = 19000, end_port: int = 19999) -> int:
    """Find a free port in the given range."""
    for port in range(start_port, end_port + 1):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"No free ports available in range {start_port}-{end_port}")


@pytest.fixture(scope="function")
async def test_server():
    """Start a real md-server instance for testing."""
    port = find_free_port()
    endpoint = f"http://127.0.0.1:{port}"
    
    # Start server process
    process = subprocess.Popen([
        "uv", "run", "python", "-m", "md_server",
        "--host", "127.0.0.1",
        "--port", str(port)
    ], 
    stdout=subprocess.PIPE, 
    stderr=subprocess.PIPE
    )
    
    # Wait for server to start up
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            async with RemoteMDConverter(endpoint, timeout=5) as client:
                await client.health_check()
                break
        except (NetworkError, TimeoutError):
            if attempt == max_attempts - 1:
                process.terminate()
                stdout, stderr = process.communicate(timeout=5)
                raise RuntimeError(f"Server failed to start. stdout: {stdout}, stderr: {stderr}")
            await asyncio.sleep(0.5)
    
    yield endpoint
    
    # Cleanup
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


class TestRemoteMDConverterBasic:
    """Basic unit tests without server dependency."""
    
    def test_init_with_defaults(self):
        """Test initialization with default values."""
        client = RemoteMDConverter("http://localhost:8080")
        
        assert client.endpoint == "http://localhost:8080"
        assert client.api_key is None
        assert client.timeout == 30
        assert client.max_retries == 3
        assert client.retry_delay == 1.0
    
    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        client = RemoteMDConverter(
            "https://api.example.com/",
            api_key="test-key",
            timeout=60,
            max_retries=5,
            retry_delay=2.0
        )
        
        assert client.endpoint == "https://api.example.com"
        assert client.api_key == "test-key"
        assert client.timeout == 60
        assert client.max_retries == 5
        assert client.retry_delay == 2.0
    
    def test_build_headers_without_api_key(self):
        """Test header building without API key."""
        client = RemoteMDConverter("http://localhost:8080")
        headers = client._build_headers()
        
        assert headers["User-Agent"] == "md-server-sdk/1.0"
        assert headers["Accept"] == "application/json"
        assert "Authorization" not in headers
    
    def test_build_headers_with_api_key(self):
        """Test header building with API key."""
        client = RemoteMDConverter("http://localhost:8080", api_key="test-key")
        headers = client._build_headers()
        
        assert headers["User-Agent"] == "md-server-sdk/1.0"
        assert headers["Accept"] == "application/json"
        assert headers["Authorization"] == "Bearer test-key"
    
    def test_merge_options_empty(self):
        """Test option merging with no options."""
        client = RemoteMDConverter("http://localhost:8080")
        result = client._merge_options()
        assert result == {}
    
    def test_merge_options_with_values(self):
        """Test option merging with various options."""
        client = RemoteMDConverter("http://localhost:8080")
        result = client._merge_options(
            js_rendering=True,
            ocr_enabled=False,
            timeout=60,
            invalid_option="ignored"  # Should be filtered out
        )
        
        expected = {
            "options": {
                "js_rendering": True,
                "ocr_enabled": False,
                "timeout": 60
            }
        }
        assert result == expected
    
    @pytest.mark.asyncio
    async def test_convert_url_invalid_input(self):
        """Test URL conversion with invalid input."""
        client = RemoteMDConverter("http://localhost:8080")
        
        with pytest.raises(InvalidInputError):
            await client.convert_url("")
        
        with pytest.raises(InvalidInputError):
            await client.convert_url(None)
    
    @pytest.mark.asyncio
    async def test_convert_content_invalid_input(self):
        """Test content conversion with invalid input."""
        client = RemoteMDConverter("http://localhost:8080")
        
        with pytest.raises(InvalidInputError):
            await client.convert_content("not bytes")
        
        with pytest.raises(InvalidInputError):
            await client.convert_content(b"")
    
    @pytest.mark.asyncio
    async def test_convert_text_invalid_input(self):
        """Test text conversion with invalid input."""
        client = RemoteMDConverter("http://localhost:8080")
        
        with pytest.raises(InvalidInputError):
            await client.convert_text(123, "text/html")
        
        with pytest.raises(InvalidInputError):
            await client.convert_text("", "text/html")
        
        with pytest.raises(InvalidInputError):
            await client.convert_text("   ", "text/html")
        
        with pytest.raises(InvalidInputError):
            await client.convert_text("Hello", "")
        
        with pytest.raises(InvalidInputError):
            await client.convert_text("Hello", None)
    
    @pytest.mark.asyncio
    async def test_convert_file_not_found(self):
        """Test file conversion with non-existent file."""
        client = RemoteMDConverter("http://localhost:8080")
        
        with pytest.raises(InvalidInputError) as exc_info:
            await client.convert_file("/path/that/does/not/exist.pdf")
        
        assert "File not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_convert_file_directory(self):
        """Test file conversion with directory path."""
        client = RemoteMDConverter("http://localhost:8080")
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            with pytest.raises(InvalidInputError) as exc_info:
                await client.convert_file(tmp_dir)
            
            assert "Path is not a file" in str(exc_info.value)


class TestRemoteMDConverterIntegration:
    """Integration tests using real md-server instance."""
    
    @pytest.mark.asyncio
    async def test_health_check(self, test_server):
        """Test health check endpoint."""
        async with RemoteMDConverter(test_server) as client:
            health = await client.health_check()
            
            assert health["status"] == "healthy"
            assert "version" in health
            assert "uptime_seconds" in health
    
    @pytest.mark.asyncio
    async def test_get_formats(self, test_server):
        """Test formats endpoint."""
        async with RemoteMDConverter(test_server) as client:
            formats = await client.get_formats()
            
            assert "formats" in formats
            assert isinstance(formats["formats"], dict)
            assert len(formats["formats"]) > 0
    
    @pytest.mark.asyncio
    async def test_convert_text_html(self, test_server):
        """Test converting HTML text."""
        async with RemoteMDConverter(test_server) as client:
            html_content = "<h1>Hello World</h1><p>This is a test.</p>"
            
            result = await client.convert_text(html_content, "text/html")
            
            assert isinstance(result, ConversionResult)
            assert result.success is True
            assert "Hello World" in result.markdown
            assert result.metadata.source_type in ["html", "markdown"]
            assert result.metadata.detected_format == "text/html"
    
    @pytest.mark.asyncio
    async def test_convert_text_plain(self, test_server):
        """Test converting plain text."""
        async with RemoteMDConverter(test_server) as client:
            text_content = "Hello World\nThis is plain text."
            
            result = await client.convert_text(text_content, "text/plain")
            
            assert isinstance(result, ConversionResult)
            assert result.success is True
            assert "Hello World" in result.markdown
    
    @pytest.mark.asyncio
    async def test_convert_file_text(self, test_server, sample_files):
        """Test converting a text file."""
        if not sample_files.get("html") or not sample_files["html"].exists():
            pytest.skip("HTML test file not available")
        
        async with RemoteMDConverter(test_server) as client:
            result = await client.convert_file(sample_files["html"])
            
            assert isinstance(result, ConversionResult)
            assert result.success is True
            assert len(result.markdown) > 0
            assert result.metadata.source_size > 0
    
    @pytest.mark.asyncio
    async def test_convert_content_with_options(self, test_server):
        """Test converting content with various options."""
        async with RemoteMDConverter(test_server) as client:
            content = b"<h1>Title</h1><p>Content</p>"
            
            result = await client.convert_content(
                content,
                filename="test.html",
                preserve_formatting=True,
                clean_markdown=False
            )
            
            assert isinstance(result, ConversionResult)
            assert result.success is True
            assert "Title" in result.markdown
    
    @pytest.mark.asyncio
    async def test_error_handling_invalid_format(self, test_server):
        """Test error handling for unsupported content."""
        async with RemoteMDConverter(test_server, max_retries=1) as client:
            # Send invalid binary data
            invalid_content = b"\x00\x01\x02\x03" * 100
            
            with pytest.raises(ConversionError):
                await client.convert_content(invalid_content, filename="invalid.unknown")
    
    @pytest.mark.asyncio
    async def test_context_manager(self, test_server):
        """Test context manager functionality."""
        async with RemoteMDConverter(test_server) as client:
            result = await client.convert_text("Hello", "text/plain")
            assert result.success is True
        # Client should be properly closed after context
    
    @pytest.mark.asyncio
    async def test_connection_error_handling(self):
        """Test handling of connection errors."""
        # Use non-existent server
        async with RemoteMDConverter("http://127.0.0.1:99999", max_retries=1, retry_delay=0.1) as client:
            with pytest.raises((NetworkError, ConversionError)):
                await client.convert_text("Hello", "text/plain")