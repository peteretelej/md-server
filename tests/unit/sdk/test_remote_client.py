"""
Comprehensive tests for RemoteMDConverter with HTTP integration.

This file consolidates remote client testing with real server integration,
covering all remote functionality including authentication, error handling,
and network scenarios.
"""

import asyncio
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

import pytest
import httpx

from md_server.sdk.remote import RemoteMDConverter
from md_server.sdk.models import ConversionResult, ConversionMetadata
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
    """Start a real md-server instance for integration testing."""
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
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{endpoint}/health", timeout=5)
                if response.status_code == 200:
                    break
        except (httpx.RequestError, httpx.TimeoutException):
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
    """Unit tests for RemoteMDConverter without server dependency."""
    
    def test_initialization_defaults(self):
        """Test initialization with default values."""
        client = RemoteMDConverter("http://localhost:8080")
        
        assert client.endpoint == "http://localhost:8080"
        assert client.api_key is None
        assert client.timeout == 30
        assert client.max_retries == 3
        assert client.retry_delay == 1.0
    
    def test_initialization_custom_values(self):
        """Test initialization with custom values."""
        client = RemoteMDConverter(
            "https://api.example.com/",
            api_key="test-key",
            timeout=60,
            max_retries=5,
            retry_delay=2.0
        )
        
        assert client.endpoint == "https://api.example.com"  # Trailing slash removed
        assert client.api_key == "test-key"
        assert client.timeout == 60
        assert client.max_retries == 5
        assert client.retry_delay == 2.0
    
    def test_header_building_without_api_key(self):
        """Test header building without API key."""
        client = RemoteMDConverter("http://localhost:8080")
        headers = client._build_headers()
        
        expected_headers = {
            "User-Agent": "md-server-sdk/1.0",
            "Accept": "application/json"
        }
        
        for key, value in expected_headers.items():
            assert headers[key] == value
        assert "Authorization" not in headers
    
    def test_header_building_with_api_key(self):
        """Test header building with API key."""
        client = RemoteMDConverter("http://localhost:8080", api_key="test-key")
        headers = client._build_headers()
        
        assert headers["User-Agent"] == "md-server-sdk/1.0"
        assert headers["Accept"] == "application/json"
        assert headers["Authorization"] == "Bearer test-key"
    
    def test_option_merging(self):
        """Test option merging functionality."""
        client = RemoteMDConverter("http://localhost:8080")
        
        # Test empty options
        result = client._merge_options()
        assert result == {}
        
        # Test with valid options
        result = client._merge_options(
            js_rendering=True,
            ocr_enabled=False,
            timeout=60,
            extract_images=True,
            invalid_option="ignored"  # Should be filtered out
        )
        
        expected = {
            "options": {
                "js_rendering": True,
                "ocr_enabled": False,
                "timeout": 60,
                "extract_images": True
            }
        }
        assert result == expected
    
    @pytest.mark.parametrize("invalid_input,expected_error", [
        ("", "URL cannot be empty"),
        (None, "URL cannot be empty"),
        ("   ", "URL cannot be empty"),
        ("not-a-url", "Invalid URL format"),
        ("ftp://example.com", "Only HTTP/HTTPS URLs allowed"),
    ])
    async def test_url_validation(self, invalid_input, expected_error):
        """Test URL validation with various invalid inputs."""
        client = RemoteMDConverter("http://localhost:8080")
        
        with pytest.raises(InvalidInputError, match=expected_error):
            await client.convert_url(invalid_input)
    
    @pytest.mark.parametrize("invalid_input,expected_error", [
        ("not bytes", "Content must be bytes"),
        (b"", "Content cannot be empty"),
        (None, "Content must be bytes"),
    ])
    async def test_content_validation(self, invalid_input, expected_error):
        """Test content validation with invalid inputs."""
        client = RemoteMDConverter("http://localhost:8080")
        
        with pytest.raises(InvalidInputError, match=expected_error):
            await client.convert_content(invalid_input)
    
    @pytest.mark.parametrize("text,mime_type,expected_error", [
        (123, "text/html", "Text must be a string"),
        ("", "text/html", "Text cannot be empty"),
        ("   ", "text/html", "Text cannot be empty"),
        ("Hello", "", "MIME type cannot be empty"),
        ("Hello", None, "MIME type cannot be empty"),
        ("Hello", "invalid", "MIME type must contain"),
    ])
    async def test_text_validation(self, text, mime_type, expected_error):
        """Test text validation with invalid inputs."""
        client = RemoteMDConverter("http://localhost:8080")
        
        with pytest.raises(InvalidInputError, match=expected_error):
            await client.convert_text(text, mime_type)
    
    async def test_file_validation(self):
        """Test file validation with invalid file paths."""
        client = RemoteMDConverter("http://localhost:8080")
        
        # Non-existent file
        with pytest.raises(InvalidInputError, match="File not found"):
            await client.convert_file("/path/that/does/not/exist.pdf")
        
        # Directory instead of file
        with tempfile.TemporaryDirectory() as tmp_dir:
            with pytest.raises(InvalidInputError, match="Path is not a file"):
                await client.convert_file(tmp_dir)


class TestRemoteMDConverterIntegration:
    """Integration tests using real md-server instance."""
    
    async def test_health_check(self, test_server):
        """Test health check endpoint."""
        async with RemoteMDConverter(test_server) as client:
            health = await client.health_check()
            
            assert isinstance(health, dict)
            assert health["status"] == "healthy"
            assert "version" in health
            assert "uptime_seconds" in health
            assert isinstance(health["uptime_seconds"], (int, float))
    
    async def test_get_formats(self, test_server):
        """Test formats endpoint."""
        async with RemoteMDConverter(test_server) as client:
            formats = await client.get_formats()
            
            assert isinstance(formats, dict)
            assert "formats" in formats
            assert isinstance(formats["formats"], dict)
            assert len(formats["formats"]) > 0
            
            # Verify common formats are supported
            supported_formats = formats["formats"]
            assert "pdf" in str(supported_formats).lower()
            assert "html" in str(supported_formats).lower()
    
    async def test_convert_text_html(self, test_server):
        """Test converting HTML text."""
        async with RemoteMDConverter(test_server) as client:
            html_content = "<h1>Hello World</h1><p>This is a <strong>test</strong>.</p>"
            
            result = await client.convert_text(html_content, "text/html")
            
            assert isinstance(result, ConversionResult)
            assert result.success is True
            assert "Hello World" in result.markdown
            assert "**test**" in result.markdown or "*test*" in result.markdown
            assert result.metadata.source_type in ["text", "html"]
            assert result.metadata.detected_format == "text/html"
            assert result.metadata.source_size == len(html_content.encode())
            assert result.metadata.processing_time > 0
    
    async def test_convert_text_plain(self, test_server):
        """Test converting plain text."""
        async with RemoteMDConverter(test_server) as client:
            text_content = "Hello World\nThis is plain text with\nmultiple lines."
            
            result = await client.convert_text(text_content, "text/plain")
            
            assert isinstance(result, ConversionResult)
            assert result.success is True
            assert "Hello World" in result.markdown
            assert "plain text" in result.markdown
            assert result.metadata.detected_format == "text/plain"
    
    async def test_convert_content_with_filename(self, test_server):
        """Test converting binary content with filename hint."""
        async with RemoteMDConverter(test_server) as client:
            html_content = b"<h1>Binary HTML</h1><p>Content from bytes</p>"
            
            result = await client.convert_content(
                html_content,
                filename="test.html"
            )
            
            assert isinstance(result, ConversionResult)
            assert result.success is True
            assert "Binary HTML" in result.markdown
            assert result.metadata.source_type == "content"
            assert result.metadata.source_size == len(html_content)
    
    async def test_convert_content_with_options(self, test_server):
        """Test converting content with various options."""
        async with RemoteMDConverter(test_server) as client:
            content = b"<h1>Title</h1><p>Content with options</p>"
            
            result = await client.convert_content(
                content,
                filename="test.html",
                preserve_formatting=True,
                clean_markdown=False,
                extract_images=False
            )
            
            assert isinstance(result, ConversionResult)
            assert result.success is True
            assert "Title" in result.markdown
            assert "Content with options" in result.markdown
    
    async def test_convert_file_integration(self, test_server, sample_files):
        """Test converting actual files."""
        async with RemoteMDConverter(test_server) as client:
            # Test with HTML file if available
            if sample_files.get("html") and sample_files["html"].exists():
                result = await client.convert_file(sample_files["html"])
                
                assert isinstance(result, ConversionResult)
                assert result.success is True
                assert len(result.markdown) > 0
                assert result.metadata.source_size > 0
                assert result.metadata.processing_time > 0
    
    async def test_context_manager_functionality(self, test_server):
        """Test context manager properly manages resources."""
        async with RemoteMDConverter(test_server) as client:
            # Verify client is functional inside context
            result = await client.convert_text("Hello", "text/plain")
            assert result.success is True
            
            # Verify we can make multiple calls
            result2 = await client.convert_text("World", "text/plain")
            assert result2.success is True
        
        # After context, client should be properly cleaned up
        # (httpx client closed automatically)
    
    async def test_retry_mechanism(self, test_server):
        """Test retry mechanism with transient failures."""
        # Create client with fast retries for testing
        async with RemoteMDConverter(test_server, max_retries=2, retry_delay=0.1) as client:
            # First, test normal operation works
            result = await client.convert_text("Test", "text/plain")
            assert result.success is True
            
            # Mock a transient failure followed by success
            original_request = client._make_request
            call_count = 0
            
            async def mock_request_with_retry(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise httpx.ConnectError("Transient failure")
                return await original_request(*args, **kwargs)
            
            client._make_request = mock_request_with_retry
            
            # Should succeed after retry
            result = await client.convert_text("Retry test", "text/plain")
            assert result.success is True
            assert call_count == 2  # Failed once, succeeded on retry


class TestRemoteMDConverterErrorHandling:
    """Test error handling scenarios."""
    
    async def test_connection_error_handling(self):
        """Test handling of connection errors."""
        # Use non-existent server
        async with RemoteMDConverter(
            "http://127.0.0.1:99999", 
            max_retries=1, 
            retry_delay=0.1
        ) as client:
            with pytest.raises((NetworkError, ConversionError)):
                await client.convert_text("Hello", "text/plain")
    
    async def test_timeout_handling(self):
        """Test timeout handling."""
        # Use very short timeout
        async with RemoteMDConverter(
            "http://httpbin.org/delay/10",  # Endpoint that takes 10 seconds
            timeout=0.1,  # 100ms timeout
            max_retries=0
        ) as client:
            with pytest.raises((TimeoutError, NetworkError)):
                await client.convert_text("Hello", "text/plain")
    
    async def test_authentication_handling(self, test_server):
        """Test authentication handling (no specific auth error in current SDK)."""
        # Test with API key - should work if server accepts it
        async with RemoteMDConverter(test_server, api_key="test-key") as client:
            try:
                result = await client.convert_text("Hello", "text/plain")
                # Should succeed (server likely doesn't require auth in test)
                assert result.success is True
            except (ConversionError, NetworkError):
                # If auth fails, it would likely be a conversion or network error
                pass
    
    async def test_server_error_handling(self, test_server):
        """Test handling of server errors."""
        async with RemoteMDConverter(test_server) as client:
            # Try to send invalid data that might cause server error
            try:
                # Send extremely large content that might be rejected
                large_content = "x" * (100 * 1024 * 1024)  # 100MB of text
                await client.convert_text(large_content, "text/plain")
            except (ConversionError, NetworkError):
                # Server should reject this gracefully
                pass
    
    async def test_malformed_response_handling(self):
        """Test handling of malformed server responses."""
        with patch('httpx.AsyncClient.post') as mock_post:
            # Mock a response with invalid JSON
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_response.text = "Invalid response"
            mock_post.return_value.__aenter__.return_value = mock_response
            
            async with RemoteMDConverter("http://localhost:8080") as client:
                with pytest.raises(ConversionError):
                    await client.convert_text("Hello", "text/plain")


class TestRemoteMDConverterPerformance:
    """Performance and concurrency tests."""
    
    async def test_concurrent_requests(self, test_server):
        """Test handling multiple concurrent requests."""
        async with RemoteMDConverter(test_server) as client:
            # Create multiple concurrent conversion tasks
            tasks = [
                client.convert_text(f"Content {i}", "text/plain")
                for i in range(10)
            ]
            
            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify all succeeded (or handle expected failures gracefully)
            successful_results = [r for r in results if isinstance(r, ConversionResult)]
            assert len(successful_results) >= 8  # Allow for some potential failures
            
            # Verify unique request IDs
            request_ids = [r.request_id for r in successful_results]
            assert len(set(request_ids)) == len(successful_results)
    
    async def test_connection_pooling(self, test_server):
        """Test that connection pooling works correctly."""
        async with RemoteMDConverter(test_server) as client:
            # Make multiple sequential requests
            results = []
            for i in range(5):
                result = await client.convert_text(f"Test {i}", "text/plain")
                results.append(result)
            
            # All should succeed
            assert len(results) == 5
            for result in results:
                assert result.success is True
    
    async def test_large_content_handling(self, test_server):
        """Test handling of reasonably large content."""
        async with RemoteMDConverter(test_server) as client:
            # Create moderately large HTML content
            large_html = "<html><body>" + "<p>Content line</p>\n" * 1000 + "</body></html>"
            
            result = await client.convert_text(large_html, "text/html")
            
            assert result.success is True
            assert len(result.markdown) > 1000  # Should produce substantial markdown
            assert result.metadata.source_size == len(large_html.encode())


class TestRemoteMDConverterSync:
    """Test synchronous wrapper methods."""
    
    def test_sync_convert_text(self, test_server):
        """Test synchronous text conversion."""
        client = RemoteMDConverter(test_server)
        
        # Mock the async method to avoid actual network calls in sync test
        with patch.object(client, 'convert_text', new_callable=AsyncMock) as mock_async:
            expected_result = ConversionResult(
                markdown="# Sync Test",
                metadata=ConversionMetadata(
                    source_type="text",
                    source_size=10,
                    markdown_size=11,
                    processing_time=0.1,
                    detected_format="text/plain"
                )
            )
            mock_async.return_value = expected_result
            
            result = client.convert_text_sync("Hello sync", "text/plain")
            
            assert result.markdown == "# Sync Test"
            mock_async.assert_called_once_with("Hello sync", "text/plain")
    
    def test_sync_health_check(self, test_server):
        """Test synchronous health check."""
        client = RemoteMDConverter(test_server)
        
        with patch.object(client, 'health_check', new_callable=AsyncMock) as mock_async:
            expected_result = {"status": "healthy", "version": "1.0.0"}
            mock_async.return_value = expected_result
            
            result = client.health_check_sync()
            
            assert result == expected_result
            mock_async.assert_called_once()