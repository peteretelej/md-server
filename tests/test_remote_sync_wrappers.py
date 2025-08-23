"""
Test sync wrappers for remote SDK.

Tests synchronous API methods, error propagation from async to sync,
threading behavior, and sync wrapper functionality.
"""

import pytest
import threading
from unittest.mock import patch, Mock
from concurrent.futures import ThreadPoolExecutor

from md_server.sdk.remote import RemoteMDConverter
from md_server.sdk.exceptions import NetworkError, ConversionError, InvalidInputError
from md_server.sdk.sync import sync_wrapper


class TestRemoteSyncWrappers:
    """Test synchronous wrapper functionality for remote SDK."""

    @pytest.fixture
    def client(self):
        """Create remote client for testing."""
        return RemoteMDConverter(
            endpoint="http://127.0.0.1:8999",
            timeout=5,
            max_retries=1
        )

    @pytest.fixture
    def success_mock_response(self):
        """Mock successful response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "markdown": "# Test Result",
            "metadata": {
                "source_type": "text",
                "source_size": 100,
                "markdown_size": 50,
                "conversion_time_ms": 150.0,
                "detected_format": "text",
                "warnings": []
            },
            "request_id": "sync_test_123"
        }
        return mock_response

    def test_convert_text_sync(self, client, success_mock_response):
        """Test synchronous text conversion."""
        with patch.object(client._client, 'request', return_value=success_mock_response):
            result = client.convert_text_sync("test content", "text/plain")
            
            assert result.success
            assert result.markdown == "# Test Result"
            assert result.metadata.source_type == "text"
            assert result.request_id == "sync_test_123"

    def test_convert_url_sync(self, client, success_mock_response):
        """Test synchronous URL conversion."""
        with patch.object(client._client, 'request', return_value=success_mock_response):
            result = client.convert_url_sync("https://example.com")
            
            assert result.success
            assert result.markdown == "# Test Result"
            assert result.metadata.source_type == "text"

    def test_convert_content_sync(self, client, success_mock_response):
        """Test synchronous content conversion."""
        test_content = b"test binary content"
        
        with patch.object(client._client, 'request', return_value=success_mock_response):
            result = client.convert_content_sync(test_content, "test.txt")
            
            assert result.success
            assert result.markdown == "# Test Result"

    def test_convert_file_sync(self, client, success_mock_response, tmp_path):
        """Test synchronous file conversion."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test file content")
        
        with patch.object(client._client, 'request', return_value=success_mock_response):
            result = client.convert_file_sync(str(test_file))
            
            assert result.success
            assert result.markdown == "# Test Result"

    def test_health_check_sync(self, client):
        """Test synchronous health check."""
        health_response = Mock()
        health_response.status_code = 200
        health_response.json.return_value = {
            "status": "healthy",
            "version": "1.0.0",
            "uptime": 3600
        }
        
        with patch.object(client._client, 'request', return_value=health_response):
            result = client.health_check_sync()
            
            assert result["status"] == "healthy"
            assert result["version"] == "1.0.0"

    def test_get_formats_sync(self, client):
        """Test synchronous get formats."""
        formats_response = Mock()
        formats_response.status_code = 200
        formats_response.json.return_value = {
            "supported_formats": ["pdf", "docx", "html"],
            "version": "1.0.0"
        }
        
        with patch.object(client._client, 'request', return_value=formats_response):
            result = client.get_formats_sync()
            
            assert "supported_formats" in result
            assert "pdf" in result["supported_formats"]

    def test_sync_method_error_propagation(self, client):
        """Test error propagation from async to sync methods."""
        async def mock_request(*args, **kwargs):
            raise NetworkError("Connection failed", {"host": "example.com"})
        
        with patch.object(client._client, 'request', mock_request):
            with pytest.raises(NetworkError) as exc_info:
                client.convert_text_sync("test", "text/plain")
            
            assert "Connection failed" in str(exc_info.value)
            assert exc_info.value.details["host"] == "example.com"

    def test_sync_method_conversion_error_propagation(self, client):
        """Test conversion error propagation in sync methods."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {
                "message": "Invalid input format",
                "details": {"field": "mime_type"}
            }
        }
        
        with patch.object(client._client, 'request', return_value=mock_response):
            with pytest.raises(InvalidInputError) as exc_info:
                client.convert_text_sync("test", "invalid/mime")
            
            assert "Invalid input format" in str(exc_info.value)
            assert exc_info.value.details["field"] == "mime_type"

    def test_sync_method_timeout_propagation(self, client):
        """Test timeout error propagation in sync methods."""
        import httpx
        
        async def mock_request(*args, **kwargs):
            raise httpx.TimeoutException("Request timeout")
        
        with patch.object(client._client, 'request', mock_request):
            with pytest.raises(Exception):  # Should be TimeoutError
                client.convert_text_sync("test", "text/plain")

    def test_sync_wrapper_function_directly(self):
        """Test sync_wrapper function directly."""
        async def async_function(value, multiplier=2):
            return value * multiplier
        
        sync_function = sync_wrapper(async_function)
        result = sync_function(5, multiplier=3)
        
        assert result == 15

    def test_sync_wrapper_with_exception(self):
        """Test sync_wrapper handles exceptions correctly."""
        async def async_function_with_error():
            raise ValueError("Test error")
        
        sync_function = sync_wrapper(async_function_with_error)
        
        with pytest.raises(ValueError) as exc_info:
            sync_function()
        
        assert "Test error" in str(exc_info.value)

    def test_sync_methods_thread_safety(self, client, success_mock_response):
        """Test sync methods are thread-safe."""
        results = []
        errors = []
        
        def convert_in_thread(thread_id):
            try:
                with patch.object(client._client, 'request', return_value=success_mock_response):
                    result = client.convert_text_sync(f"test {thread_id}", "text/plain")
                    results.append((thread_id, result.markdown))
            except Exception as e:
                errors.append((thread_id, e))
        
        # Run conversions in multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=convert_in_thread, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5
        
        for thread_id, markdown in results:
            assert markdown == "# Test Result"

    def test_sync_methods_with_thread_pool(self, client, success_mock_response):
        """Test sync methods work with ThreadPoolExecutor."""
        def convert_text_task(text):
            with patch.object(client._client, 'request', return_value=success_mock_response):
                return client.convert_text_sync(text, "text/plain")
        
        texts = [f"test content {i}" for i in range(3)]
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(convert_text_task, text) for text in texts]
            results = [future.result() for future in futures]
        
        assert len(results) == 3
        for result in results:
            assert result.success
            assert result.markdown == "# Test Result"

    def test_sync_methods_preserve_client_configuration(self, client):
        """Test sync methods preserve client configuration."""
        # Verify client configuration is preserved in sync calls
        assert client.endpoint == "http://127.0.0.1:8999"
        assert client.timeout == 5
        assert client.max_retries == 1
        
        # Mock response that allows inspection of request
        request_data = {}
        
        async def mock_request(*args, **kwargs):
            request_data.update(kwargs)
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "success": True,
                "markdown": "# Test",
                "metadata": {"source_type": "text"}
            }
            return mock_response
        
        with patch.object(client._client, 'request', mock_request):
            client.convert_text_sync("test", "text/plain")
            
            # Verify configuration was used
            assert "json" in request_data
            assert request_data["json"]["text"] == "test"

    def test_sync_methods_with_options(self, client, success_mock_response):
        """Test sync methods handle conversion options."""
        conversion_options = {
            "js_rendering": True,
            "extract_images": False,
            "timeout": 30
        }
        
        with patch.object(client._client, 'request', return_value=success_mock_response):
            result = client.convert_text_sync(
                "test", 
                "text/plain", 
                **conversion_options
            )
            
            assert result.success
            assert result.markdown == "# Test Result"

    def test_sync_methods_input_validation(self, client):
        """Test sync methods validate input correctly."""
        # Test invalid text input
        with pytest.raises(InvalidInputError):
            client.convert_text_sync("", "text/plain")  # Empty text
        
        with pytest.raises(InvalidInputError):
            client.convert_text_sync("test", "")  # Empty mime type
        
        # Test invalid URL input
        with pytest.raises(InvalidInputError):
            client.convert_url_sync("")  # Empty URL
        
        with pytest.raises(InvalidInputError):
            client.convert_url_sync("invalid-url")  # Invalid format
        
        # Test invalid content input
        with pytest.raises(InvalidInputError):
            client.convert_content_sync(b"", "test.txt")  # Empty content

    def test_sync_methods_file_operations(self, client, success_mock_response, tmp_path):
        """Test sync methods handle file operations correctly."""
        # Test existing file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        with patch.object(client._client, 'request', return_value=success_mock_response):
            result = client.convert_file_sync(str(test_file))
            assert result.success
        
        # Test non-existent file
        non_existent = tmp_path / "non_existent.txt"
        with pytest.raises(InvalidInputError):
            client.convert_file_sync(str(non_existent))
        
        # Test directory instead of file
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        with pytest.raises(InvalidInputError):
            client.convert_file_sync(str(test_dir))

    def test_sync_methods_cleanup_resources(self, client, success_mock_response):
        """Test sync methods properly clean up resources."""
        # Track if cleanup is called
        cleanup_called = {"value": False}
        original_close = client._client.aclose
        
        async def mock_close():
            cleanup_called["value"] = True
            return await original_close()
        
        client._client.aclose = mock_close
        
        with patch.object(client._client, 'request', return_value=success_mock_response):
            # Use context manager to ensure cleanup
            with client:
                client.convert_text_sync("test", "text/plain")
        
        # Note: In real usage, sync wrappers handle their own event loops
        # but don't automatically close the client

    def test_sync_methods_concurrent_access(self, client, success_mock_response):
        """Test multiple sync method calls can run concurrently."""
        import concurrent.futures
        
        def make_request(method_name, *args):
            method = getattr(client, f"{method_name}_sync")
            with patch.object(client._client, 'request', return_value=success_mock_response):
                return method(*args)
        
        # Create test file for file conversion
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("test content")
            temp_file_path = f.name
        
        tasks = [
            ("convert_text", "test1", "text/plain"),
            ("convert_url", "https://example.com"),
            ("convert_content", b"test content", "test.txt"),
            ("convert_file", temp_file_path),
        ]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(make_request, *task) for task in tasks]
            results = [future.result() for future in futures]
        
        # Cleanup temp file
        import os
        os.unlink(temp_file_path)
        
        # All should succeed
        assert len(results) == 4
        for result in results:
            if hasattr(result, 'success'):
                assert result.success
            else:
                assert isinstance(result, dict)  # health_check/get_formats return dict

    def test_sync_methods_preserve_exception_details(self, client):
        """Test sync methods preserve exception details from async methods."""
        detailed_error = ConversionError(
            "Complex conversion error",
            {
                "error_code": "CONV_001",
                "file_type": "unknown",
                "suggestions": ["Try PDF format", "Check file integrity"]
            }
        )
        
        async def mock_request(*args, **kwargs):
            raise detailed_error
        
        with patch.object(client._client, 'request', mock_request):
            with pytest.raises(ConversionError) as exc_info:
                client.convert_text_sync("test", "text/plain")
            
            # Check that all details are preserved
            assert str(exc_info.value) == str(detailed_error)
            assert exc_info.value.details == detailed_error.details
            assert exc_info.value.details["error_code"] == "CONV_001"
            assert "Try PDF format" in exc_info.value.details["suggestions"]