"""
Test async context manager for remote SDK.

Tests proper resource management, cleanup on success and failure,
connection lifecycle, and context manager protocol implementation.
"""

import pytest
import asyncio
from unittest.mock import patch, Mock

from md_server.sdk.remote import RemoteMDConverter
from md_server.sdk.exceptions import NetworkError, ConversionError
from tests.helpers.network import NetworkFailureSimulator


class TestRemoteContextManager:
    """Test async context manager functionality in remote SDK."""

    @pytest.mark.asyncio
    async def test_context_manager_entry(self):
        """Test context manager __aenter__ returns self."""
        client = RemoteMDConverter("http://127.0.0.1:8999")
        
        async with client as context_client:
            assert context_client is client
            assert hasattr(context_client, '_client')
            assert not context_client._client.is_closed

    @pytest.mark.asyncio
    async def test_context_manager_exit_cleanup(self):
        """Test context manager __aexit__ cleans up resources."""
        client = RemoteMDConverter("http://127.0.0.1:8999")
        
        async with client as context_client:
            # Client should be active
            assert not context_client._client.is_closed
        
        # After context exit, client should be closed
        assert client._client.is_closed

    @pytest.mark.asyncio
    async def test_manual_close_vs_context_manager(self):
        """Test manual close vs context manager cleanup."""
        # Test manual close
        client1 = RemoteMDConverter("http://127.0.0.1:8999")
        assert not client1._client.is_closed
        await client1.close()
        assert client1._client.is_closed
        
        # Test context manager close
        client2 = RemoteMDConverter("http://127.0.0.1:8999")
        async with client2:
            assert not client2._client.is_closed
        assert client2._client.is_closed

    @pytest.mark.asyncio
    async def test_context_manager_cleanup_on_success(self):
        """Test cleanup occurs even when operations succeed."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "markdown": "# Test",
            "metadata": {"source_type": "text"}
        }
        
        async with RemoteMDConverter("http://127.0.0.1:8999") as client:
            with patch.object(client._client, 'request', return_value=mock_response):
                result = await client.convert_text("test", "text/plain")
                assert result.success
        
        # Should be cleaned up
        assert client._client.is_closed

    @pytest.mark.asyncio
    async def test_context_manager_cleanup_on_exception(self):
        """Test cleanup occurs when exceptions are raised."""
        async with pytest.raises(NetworkError):
            async with RemoteMDConverter("http://127.0.0.1:8999") as client:
                simulator = NetworkFailureSimulator()
                with simulator.connection_refused():
                    await client.convert_text("test", "text/plain")
        
        # Should be cleaned up even after exception
        assert client._client.is_closed

    @pytest.mark.asyncio
    async def test_context_manager_cleanup_on_conversion_error(self):
        """Test cleanup occurs on conversion errors."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {"message": "Invalid input"}
        }
        
        async with pytest.raises(Exception):  # Should raise InvalidInputError
            async with RemoteMDConverter("http://127.0.0.1:8999") as client:
                with patch.object(client._client, 'request', return_value=mock_response):
                    await client.convert_text("test", "text/plain")
        
        assert client._client.is_closed

    @pytest.mark.asyncio
    async def test_context_manager_cleanup_on_unexpected_error(self):
        """Test cleanup occurs on unexpected errors."""
        async def mock_request(*args, **kwargs):
            raise ValueError("Unexpected error")
        
        async with pytest.raises(ConversionError):
            async with RemoteMDConverter("http://127.0.0.1:8999") as client:
                with patch.object(client._client, 'request', mock_request):
                    await client.convert_text("test", "text/plain")
        
        assert client._client.is_closed

    @pytest.mark.asyncio
    async def test_multiple_operations_in_context(self):
        """Test multiple operations within same context manager."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "markdown": "# Result",
            "metadata": {"source_type": "text"}
        }
        
        async with RemoteMDConverter("http://127.0.0.1:8999") as client:
            with patch.object(client._client, 'request', return_value=mock_response):
                # Multiple operations should reuse same connection
                result1 = await client.convert_text("test1", "text/plain")
                result2 = await client.convert_text("test2", "text/plain")
                result3 = await client.health_check()
                
                assert result1.success
                assert result2.success
                assert isinstance(result3, dict)
                
                # Client should still be active during context
                assert not client._client.is_closed
        
        # Should be cleaned up after context
        assert client._client.is_closed

    @pytest.mark.asyncio
    async def test_nested_context_managers(self):
        """Test behavior with nested context managers."""
        clients = []
        
        async with RemoteMDConverter("http://127.0.0.1:8999") as client1:
            clients.append(client1)
            async with RemoteMDConverter("http://127.0.0.1:8998") as client2:
                clients.append(client2)
                
                # Both should be active
                assert not client1._client.is_closed
                assert not client2._client.is_closed
            
            # client2 should be closed, client1 still active
            assert not client1._client.is_closed
            assert client2._client.is_closed
        
        # Both should be closed
        assert client1._client.is_closed
        assert client2._client.is_closed

    @pytest.mark.asyncio
    async def test_context_manager_exception_suppression(self):
        """Test context manager doesn't suppress exceptions."""
        with pytest.raises(NetworkError):
            async with RemoteMDConverter("http://127.0.0.1:8999") as client:
                simulator = NetworkFailureSimulator()
                with simulator.connection_refused():
                    await client.convert_text("test", "text/plain")

    @pytest.mark.asyncio
    async def test_context_manager_with_retries(self):
        """Test context manager cleanup with retry logic."""
        call_count = {"value": 0}
        
        async def mock_request(*args, **kwargs):
            call_count["value"] += 1
            raise NetworkError("Connection failed")
        
        client = RemoteMDConverter(
            "http://127.0.0.1:8999",
            max_retries=2,
            retry_delay=0.01
        )
        
        async with pytest.raises(NetworkError):
            async with client:
                with patch.object(client._client, 'request', mock_request):
                    await client.convert_text("test", "text/plain")
        
        # Should have retried and then cleaned up
        assert call_count["value"] == 3  # initial + 2 retries
        assert client._client.is_closed

    @pytest.mark.asyncio
    async def test_context_manager_cleanup_idempotent(self):
        """Test context manager cleanup is idempotent."""
        client = RemoteMDConverter("http://127.0.0.1:8999")
        
        async with client:
            pass
        
        # Should be closed
        assert client._client.is_closed
        
        # Multiple close calls should be safe
        await client.close()  # Should not raise
        await client.close()  # Should not raise
        
        assert client._client.is_closed

    @pytest.mark.asyncio
    async def test_close_method_with_missing_client(self):
        """Test close method handles missing client gracefully."""
        client = RemoteMDConverter("http://127.0.0.1:8999")
        
        # Remove client attribute to simulate edge case
        delattr(client, '_client')
        
        # Should not raise exception
        await client.close()

    @pytest.mark.asyncio
    async def test_context_manager_with_all_conversion_methods(self, tmp_path):
        """Test context manager works with all conversion methods."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "markdown": "# Test",
            "metadata": {"source_type": "text"}
        }
        
        async with RemoteMDConverter("http://127.0.0.1:8999") as client:
            with patch.object(client._client, 'request', return_value=mock_response):
                # Test all conversion methods
                await client.convert_text("test", "text/plain")
                await client.convert_url("https://example.com")
                await client.convert_content(b"test", "test.txt")
                await client.convert_file(str(test_file))
                await client.health_check()
                await client.get_formats()
                
                # Client should still be active
                assert not client._client.is_closed
        
        # Should be cleaned up
        assert client._client.is_closed

    @pytest.mark.asyncio
    async def test_context_manager_with_auth(self):
        """Test context manager with authentication."""
        client = RemoteMDConverter(
            "http://127.0.0.1:8999",
            api_key="test-key-123"
        )
        
        async with client as auth_client:
            # Should have auth headers
            auth_headers = auth_client._client.headers
            assert "Authorization" in auth_headers
            assert auth_headers["Authorization"] == "Bearer test-key-123"
            assert not auth_client._client.is_closed
        
        assert client._client.is_closed

    @pytest.mark.asyncio
    async def test_context_manager_connection_pooling(self):
        """Test context manager preserves connection pooling configuration."""
        client = RemoteMDConverter("http://127.0.0.1:8999")
        
        async with client as pooled_client:
            # Check connection limits are preserved
            limits = pooled_client._client._limits
            assert limits.max_keepalive_connections == 5
            assert limits.max_connections == 10
        
        assert client._client.is_closed

    @pytest.mark.asyncio
    async def test_context_manager_concurrent_operations(self):
        """Test context manager with concurrent operations."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "markdown": "# Concurrent",
            "metadata": {"source_type": "text"}
        }
        
        async with RemoteMDConverter("http://127.0.0.1:8999") as client:
            with patch.object(client._client, 'request', return_value=mock_response):
                # Run multiple operations concurrently
                tasks = [
                    client.convert_text(f"test{i}", "text/plain")
                    for i in range(3)
                ]
                
                results = await asyncio.gather(*tasks)
                
                # All should succeed
                for result in results:
                    assert result.success
                    assert result.markdown == "# Concurrent"
        
        assert client._client.is_closed

    @pytest.mark.asyncio
    async def test_context_manager_timeout_configuration(self):
        """Test context manager preserves timeout configuration."""
        client = RemoteMDConverter(
            "http://127.0.0.1:8999",
            timeout=15
        )
        
        async with client as timeout_client:
            # Check timeout is preserved
            timeout_config = timeout_client._client._timeout
            assert timeout_config.read == 15.0
            assert timeout_config.write == 15.0
            assert timeout_config.connect == 15.0
        
        assert client._client.is_closed

    @pytest.mark.asyncio
    async def test_context_manager_exception_types(self):
        """Test context manager handles different exception types properly."""
        exceptions_to_test = [
            NetworkError("Network error"),
            ConversionError("Conversion error"),
            ValueError("Value error"),
            RuntimeError("Runtime error"),
        ]
        
        for exception in exceptions_to_test:
            async def mock_request(*args, **kwargs):
                raise exception
            
            async with pytest.raises(type(exception)):
                async with RemoteMDConverter("http://127.0.0.1:8999") as client:
                    with patch.object(client._client, 'request', mock_request):
                        await client.convert_text("test", "text/plain")
            
            # Should always clean up regardless of exception type
            assert client._client.is_closed