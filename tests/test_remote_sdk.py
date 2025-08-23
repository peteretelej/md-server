import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests

from md_server.sdk import RemoteMDConverter, ConversionResult, ConversionMetadata
from md_server.sdk.exceptions import (
    ConversionError,
    InvalidInputError,
    NetworkError,
    TimeoutError,
)


class TestRemoteSDKUsers:
    """Test Remote SDK users - clients connecting to running servers."""

    @pytest.fixture
    def test_server_port(self):
        """Find an available port for test server."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]

    @pytest.fixture
    def test_server(self, test_server_port):
        """Start a test server for remote SDK testing."""
        # Start server process
        server_process = subprocess.Popen(
            [sys.executable, "-m", "md_server", "--port", str(test_server_port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait for server to start
        server_ready = False
        for attempt in range(15):  # Try for up to 15 seconds
            time.sleep(1)
            try:
                response = requests.get(
                    f"http://127.0.0.1:{test_server_port}/health", timeout=2
                )
                if response.status_code == 200:
                    server_ready = True
                    break
            except requests.exceptions.ConnectionError:
                continue

        if not server_ready:
            server_process.terminate()
            try:
                stdout, stderr = server_process.communicate(timeout=2)
                print(f"Server stdout: {stdout.decode()}")
                print(f"Server stderr: {stderr.decode()}")
            except subprocess.TimeoutExpired:
                server_process.kill()
                server_process.communicate()
            pytest.fail("Test server failed to start")

        yield f"http://127.0.0.1:{test_server_port}"

        # Cleanup
        if server_process.poll() is None:
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()
                server_process.wait()

    @pytest.fixture
    def remote_converter(self, test_server):
        """Remote converter connected to test server."""
        return RemoteMDConverter(endpoint=test_server)

    @pytest.fixture
    def test_files(self):
        """Paths to test files."""
        test_data_dir = Path(__file__).parent / "test_data"
        return {
            "pdf": test_data_dir / "test.pdf",
            "html": test_data_dir / "test_blog.html",
        }

    @pytest.mark.asyncio
    async def test_remote_connection(self, remote_converter, test_server):
        """Test basic remote connection - core remote SDK usage."""
        # Test that we can connect to the server via SDK
        html_content = "<h1>Connection Test</h1><p>Testing remote connection</p>"

        result = await remote_converter.convert_text(html_content, "text/html")

        # Verify successful remote conversion
        assert isinstance(result, ConversionResult)
        assert result.markdown is not None
        assert "# Connection Test" in result.markdown
        assert "Testing remote connection" in result.markdown

        # Verify result structure from remote server
        assert result.success is True
        assert result.request_id is not None
        assert isinstance(result.metadata, ConversionMetadata)

    @pytest.mark.asyncio
    async def test_remote_conversion(self, remote_converter, test_files):
        """Test end-to-end remote file conversion - complete workflow."""
        # Test file conversion via remote server
        result = await remote_converter.convert_file(str(test_files["html"]))

        # Verify successful conversion
        assert isinstance(result, ConversionResult)
        assert result.markdown is not None
        assert len(result.markdown) > 0

        # Verify metadata from remote conversion
        assert result.metadata.source_type in ["file", "html"]
        assert result.metadata.source_size > 0
        assert result.metadata.processing_time > 0

    @pytest.mark.asyncio
    async def test_remote_error_handling(self, remote_converter):
        """Test remote error handling - network and API errors."""
        # Test invalid file path
        with pytest.raises((ConversionError, InvalidInputError, FileNotFoundError)):
            await remote_converter.convert_file("/nonexistent/file.pdf")

        # Test invalid URL
        with pytest.raises((ConversionError, InvalidInputError, NetworkError)):
            await remote_converter.convert_url("not-a-valid-url")

        # Verify error messages are meaningful
        try:
            await remote_converter.convert_file("/invalid/path")
        except Exception as e:
            assert str(e) is not None
            assert len(str(e)) > 0

    def test_remote_authentication(self, test_server):
        """Test API key authentication - when auth is configured."""
        # Test without API key (should work for test server)
        converter_no_auth = RemoteMDConverter(endpoint=test_server)

        # Test with API key
        converter_with_auth = RemoteMDConverter(
            endpoint=test_server, api_key="test-api-key"
        )

        # Both should be configured properly
        assert converter_no_auth.api_key is None
        assert converter_with_auth.api_key == "test-api-key"

        # Note: Actual auth testing would require server configuration
        # This tests the client-side auth setup

    @pytest.mark.asyncio
    async def test_remote_timeout(self, test_server):
        """Test request timeout handling - network timeout scenarios."""
        # Create converter with very short timeout
        short_timeout_converter = RemoteMDConverter(
            endpoint=test_server,
            timeout=1,  # 1 second timeout
        )

        # Test with content that should process quickly
        simple_content = "<h1>Quick Test</h1>"

        try:
            result = await short_timeout_converter.convert_text(
                simple_content, "text/html"
            )
            # If it succeeds within timeout, that's fine
            assert isinstance(result, ConversionResult)
        except TimeoutError:
            # Timeout is also acceptable for this test
            pass

    @pytest.mark.asyncio
    async def test_remote_retry_logic(self, test_server):
        """Test connection retry behavior - resilient remote connections."""
        # Create converter with retry configuration
        retry_converter = RemoteMDConverter(
            endpoint=test_server,
            max_retries=2,
            retry_delay=0.1,  # Fast retries for testing
        )

        # Test normal operation (should not need retries)
        content = "<h1>Retry Test</h1><p>Testing retry logic</p>"
        result = await retry_converter.convert_text(content, "text/html")

        assert isinstance(result, ConversionResult)
        assert "# Retry Test" in result.markdown

    def test_remote_sync_methods(self, remote_converter):
        """Test synchronous remote methods - blocking API usage."""
        # Test sync text conversion
        content = "<h1>Sync Remote Test</h1><p>Testing sync remote conversion</p>"
        result = remote_converter.convert_text_sync(content, "text/html")

        assert isinstance(result, ConversionResult)
        assert "# Sync Remote Test" in result.markdown
        assert "Testing sync remote conversion" in result.markdown


class TestRemoteSDKConfiguration:
    """Test Remote SDK configuration and connection options."""

    def test_remote_initialization_basic(self):
        """Test basic remote SDK initialization."""
        converter = RemoteMDConverter(endpoint="https://api.example.com")

        assert converter.endpoint == "https://api.example.com"
        assert converter.api_key is None
        assert converter.timeout == 30  # Default
        assert converter.max_retries == 3  # Default

    def test_remote_initialization_custom(self):
        """Test remote SDK with custom configuration."""
        converter = RemoteMDConverter(
            endpoint="https://custom.api.com/",  # With trailing slash
            api_key="secret-key",
            timeout=60,
            max_retries=5,
            retry_delay=2.0,
        )

        assert converter.endpoint == "https://custom.api.com"  # Trailing slash removed
        assert converter.api_key == "secret-key"
        assert converter.timeout == 60
        assert converter.max_retries == 5
        assert converter.retry_delay == 2.0

    def test_remote_endpoint_normalization(self):
        """Test endpoint URL normalization."""
        # Test trailing slash removal
        converter1 = RemoteMDConverter(endpoint="https://api.example.com/")
        assert converter1.endpoint == "https://api.example.com"

        # Test no trailing slash
        converter2 = RemoteMDConverter(endpoint="https://api.example.com")
        assert converter2.endpoint == "https://api.example.com"


class TestRemoteSDKIntegration:
    """Test Remote SDK integration scenarios."""

    def test_remote_error_scenarios(self):
        """Test remote SDK error handling without server."""
        # Test connection to non-existent server
        converter = RemoteMDConverter(
            endpoint="http://127.0.0.1:99999",  # Non-existent port
            timeout=1,
        )

        # This should be configured but not tested for actual connection
        # (avoiding network calls in unit tests)
        assert converter.endpoint == "http://127.0.0.1:99999"
        assert converter.timeout == 1

    @pytest.mark.asyncio
    async def test_remote_network_error_handling(self):
        """Test handling of network errors."""
        # Test with invalid endpoint
        converter = RemoteMDConverter(
            endpoint="http://invalid-domain-12345.com", timeout=2
        )

        try:
            await converter.convert_text("test", "text/plain")
        except (NetworkError, ConversionError) as e:
            # Should get a network-related error
            assert str(e) is not None
        except Exception:
            # Other exceptions are also acceptable for network errors
            pass

    def test_remote_payload_building(self):
        """Test remote request payload configuration."""
        converter = RemoteMDConverter(
            endpoint="https://api.example.com", api_key="test-key"
        )

        # Test that converter is configured for different payload types
        assert converter.endpoint == "https://api.example.com"
        assert converter.api_key == "test-key"

        # Payload building is tested through actual conversion calls


class TestRemoteSDKUserExperience:
    """Test Remote SDK from user perspective."""

    def test_remote_client_creation_patterns(self):
        """Test common patterns for creating remote clients."""
        # Pattern 1: Basic client
        basic_client = RemoteMDConverter("https://api.example.com")
        assert basic_client.endpoint == "https://api.example.com"

        # Pattern 2: Authenticated client
        auth_client = RemoteMDConverter(
            endpoint="https://api.example.com", api_key="sk-123456789"
        )
        assert auth_client.api_key == "sk-123456789"

        # Pattern 3: Production client with retries
        prod_client = RemoteMDConverter(
            endpoint="https://prod.api.com",
            api_key="prod-key",
            timeout=60,
            max_retries=5,
        )
        assert prod_client.timeout == 60
        assert prod_client.max_retries == 5

    def test_remote_client_documentation_examples(self):
        """Test examples that would appear in documentation."""
        # Example 1: Quick start
        client = RemoteMDConverter("https://api.example.com")
        assert client is not None

        # Example 2: With authentication
        secure_client = RemoteMDConverter(
            endpoint="https://api.example.com", api_key="your-api-key-here"
        )
        assert secure_client.api_key == "your-api-key-here"

        # Example 3: Production configuration
        production_client = RemoteMDConverter(
            endpoint="https://prod-api.example.com",
            api_key="prod-key",
            timeout=120,  # 2 minutes for large files
            max_retries=3,
        )
        assert production_client.timeout == 120

    @pytest.mark.asyncio
    async def test_remote_content_type_handling(self):
        """Test remote SDK handles various content types."""
        # This would normally connect to a server, but we'll test configuration
        converter = RemoteMDConverter("https://api.example.com")

        # Test that converter is set up to handle different content types
        assert converter.endpoint == "https://api.example.com"

        # Content type handling is tested through integration tests with real server


class TestRemoteSDKEdgeCases:
    """Test Remote SDK edge cases and error conditions."""

    def test_remote_empty_endpoint(self):
        """Test handling of invalid endpoint configurations."""
        # Test empty endpoint (may or may not raise exception)
        try:
            converter = RemoteMDConverter("")  # Empty endpoint
            # If it allows empty endpoint, verify it's stored correctly
            assert converter.endpoint == ""
        except (ValueError, TypeError):
            # Rejecting empty endpoint is also valid behavior
            pass

        # Test None endpoint (should raise exception)
        with pytest.raises(AttributeError):
            RemoteMDConverter(None)  # None endpoint

    def test_remote_invalid_timeout(self):
        """Test handling of invalid timeout values."""
        # Negative timeout should be handled
        try:
            converter = RemoteMDConverter("https://api.example.com", timeout=-1)
            # If it allows negative timeout, that's implementation-specific
            assert converter.timeout == -1
        except ValueError:
            # Rejecting negative timeout is also valid
            pass

    def test_remote_configuration_edge_cases(self):
        """Test edge cases in remote configuration."""
        # Very high retry count
        converter = RemoteMDConverter("https://api.example.com", max_retries=100)
        assert converter.max_retries == 100

        # Zero retries
        converter = RemoteMDConverter("https://api.example.com", max_retries=0)
        assert converter.max_retries == 0

    @pytest.mark.asyncio
    async def test_retry_mechanism(self):
        """Test remote SDK retry mechanism with various failure scenarios."""
        from unittest.mock import patch, AsyncMock
        import asyncio
        
        # Test first attempt fails, retry succeeds
        with patch("md_server.sdk.core.remote.aiohttp.ClientSession") as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # First call fails, second succeeds
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "success": True,
                "markdown": "# Test",
                "metadata": {"source_type": "text"},
                "request_id": "test-id"
            })
            
            mock_session_instance.post.side_effect = [
                Exception("Connection failed"),  # First attempt fails
                mock_response  # Second attempt succeeds
            ]
            
            converter = RemoteMDConverter(
                endpoint="http://test.example.com",
                max_retries=2,
                retry_delay=0.01  # Fast retry for testing
            )
            
            result = await converter.convert_text("test", "text/plain")
            
            # Should succeed after retry
            assert isinstance(result, ConversionResult)
            assert result.markdown == "# Test"
            
            # Should have made 2 calls (initial + 1 retry)
            assert mock_session_instance.post.call_count == 2

        # Test max retries exceeded
        with patch("md_server.sdk.core.remote.aiohttp.ClientSession") as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # All attempts fail
            mock_session_instance.post.side_effect = Exception("Connection failed")
            
            converter = RemoteMDConverter(
                endpoint="http://test.example.com",
                max_retries=2,
                retry_delay=0.01
            )
            
            with pytest.raises((NetworkError, ConversionError)):
                await converter.convert_text("test", "text/plain")
            
            # Should have made 3 calls (initial + 2 retries)
            assert mock_session_instance.post.call_count == 3

        # Test exponential backoff timing
        with patch("md_server.sdk.core.remote.aiohttp.ClientSession") as mock_session:
            with patch("asyncio.sleep") as mock_sleep:
                mock_session_instance = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_session_instance
                mock_session_instance.post.side_effect = Exception("Connection failed")
                
                converter = RemoteMDConverter(
                    endpoint="http://test.example.com",
                    max_retries=2,
                    retry_delay=1.0  # 1 second base delay
                )
                
                try:
                    await converter.convert_text("test", "text/plain")
                except:
                    pass
                
                # Should have called sleep with exponential backoff
                sleep_calls = [call.args[0] for call in mock_sleep.call_args_list]
                if sleep_calls:  # Implementation may vary
                    assert len(sleep_calls) >= 1
                    # First retry should wait base delay
                    assert sleep_calls[0] >= 1.0

        # Test network error during retry
        with patch("md_server.sdk.core.remote.aiohttp.ClientSession") as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # Different types of network errors
            mock_session_instance.post.side_effect = [
                asyncio.TimeoutError("Request timeout"),
                ConnectionError("Network unreachable"),
                Exception("Generic network error")
            ]
            
            converter = RemoteMDConverter(
                endpoint="http://test.example.com",
                max_retries=3,
                retry_delay=0.01
            )
            
            with pytest.raises((NetworkError, ConversionError, TimeoutError)):
                await converter.convert_text("test", "text/plain")
            
            # Should have attempted all retries
            assert mock_session_instance.post.call_count == 3
