"""
Test network failure scenarios for remote SDK.

Tests connection failures, timeouts, dropped connections, and other
network-level error conditions that can occur during remote API calls.
"""

import pytest
import httpx
from unittest.mock import patch

from md_server.sdk.remote import RemoteMDConverter
from md_server.sdk.exceptions import NetworkError, TimeoutError, ConversionError
from tests.helpers.network import NetworkFailureSimulator


class TestRemoteNetworkFailures:
    """Test network failure handling in remote SDK."""

    @pytest.fixture
    def client(self):
        """Create remote client for testing."""
        return RemoteMDConverter(
            endpoint="http://127.0.0.1:8999", timeout=2, max_retries=1
        )

    @pytest.mark.asyncio
    async def test_connection_refused(self, client):
        """Test connection refused error is handled correctly."""
        simulator = NetworkFailureSimulator()

        with simulator.connection_refused():
            with pytest.raises(NetworkError) as exc_info:
                await client.convert_text("test", "text/plain")

            assert "Network error" in str(exc_info.value)
            assert "Connection refused" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_connection_timeout(self, client):
        """Test connection timeout is handled correctly."""
        simulator = NetworkFailureSimulator()

        with simulator.connection_timeout(0.5):
            with pytest.raises(TimeoutError) as exc_info:
                await client.convert_text("test", "text/plain")

            assert "Request timed out" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_connection_dropped_during_request(self, client):
        """Test dropped connection during request."""
        simulator = NetworkFailureSimulator()

        with simulator.connection_dropped(after_bytes=512):
            with pytest.raises(NetworkError) as exc_info:
                await client.convert_text("test" * 1000, "text/plain")

            assert "Network error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_dns_resolution_failure(self, client):
        """Test DNS resolution failure."""
        client_with_invalid_host = RemoteMDConverter(
            endpoint="http://non-existent-host.invalid", timeout=2, max_retries=1
        )

        simulator = NetworkFailureSimulator()

        with simulator.dns_failure("non-existent-host.invalid"):
            with pytest.raises(NetworkError) as exc_info:
                await client_with_invalid_host.convert_text("test", "text/plain")

            assert "Network error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_intermittent_network_failures_exhaust_retries(self, client):
        """Test that intermittent failures eventually exhaust retries."""
        simulator = NetworkFailureSimulator()

        # High failure rate to ensure retry exhaustion
        with simulator.intermittent_failures(failure_rate=1.0):
            with pytest.raises(NetworkError) as exc_info:
                await client.convert_text("test", "text/plain")

            assert "Network error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_slow_network_causes_timeout(self):
        """Test slow network response causes timeout."""
        # Use shorter timeout for this test
        client = RemoteMDConverter(
            endpoint="http://127.0.0.1:8999",
            timeout=1,  # 1 second timeout
            max_retries=0,
        )

        simulator = NetworkFailureSimulator()

        # Delay longer than timeout
        with simulator.slow_response(delay_seconds=2.0):
            with pytest.raises(TimeoutError) as exc_info:
                await client.convert_text("test", "text/plain")

            assert "timed out" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_corrupted_response_data(self, client):
        """Test handling of corrupted response data."""
        simulator = NetworkFailureSimulator()

        with simulator.corrupt_response(corruption_rate=1.0):
            with pytest.raises(ConversionError) as exc_info:
                await client.convert_text("test", "text/plain")

            # Should get conversion error due to invalid JSON
            assert "Unexpected error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_bandwidth_limited_connection(self, client):
        """Test very slow bandwidth-limited connection."""
        # Use shorter timeout for this test
        client = RemoteMDConverter(
            endpoint="http://127.0.0.1:8999",
            timeout=1,  # 1 second timeout
            max_retries=0,
        )

        simulator = NetworkFailureSimulator()

        # Very slow connection (10 bytes/second)
        with simulator.bandwidth_limit(bytes_per_second=10):
            with pytest.raises(TimeoutError) as exc_info:
                await client.convert_text("test", "text/plain")

            assert "timed out" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_httpx_specific_errors(self, client):
        """Test httpx-specific error conditions."""

        async def mock_request_pool_error(*args, **kwargs):
            raise httpx.PoolTimeout("Connection pool exhausted")

        async def mock_request_decode_error(*args, **kwargs):
            raise httpx.DecodingError("Invalid response encoding")

        async def mock_request_too_many_redirects(*args, **kwargs):
            raise httpx.TooManyRedirects("Too many redirects")

        # Test pool timeout
        with patch.object(client._client, "request", mock_request_pool_error):
            with pytest.raises(TimeoutError) as exc_info:
                await client.convert_text("test", "text/plain")
            assert "Request timed out" in str(exc_info.value)

        # Test decode error
        with patch.object(client._client, "request", mock_request_decode_error):
            with pytest.raises(NetworkError) as exc_info:
                await client.convert_text("test", "text/plain")
            assert "Network error" in str(exc_info.value)

        # Test too many redirects
        with patch.object(client._client, "request", mock_request_too_many_redirects):
            with pytest.raises(NetworkError) as exc_info:
                await client.convert_text("test", "text/plain")
            assert "Network error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_health_check_network_failures(self, client):
        """Test health check with network failures."""
        simulator = NetworkFailureSimulator()

        with simulator.connection_refused():
            with pytest.raises(NetworkError) as exc_info:
                await client.health_check()

            assert "Health check failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_formats_network_failures(self, client):
        """Test get_formats with network failures."""
        simulator = NetworkFailureSimulator()

        with simulator.connection_timeout(0.5):
            with pytest.raises(NetworkError) as exc_info:
                await client.get_formats()

            assert "Failed to get formats" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_cleanup_after_network_failure(self, client):
        """Test client cleanup after network failures."""
        simulator = NetworkFailureSimulator()

        try:
            with simulator.connection_refused():
                await client.convert_text("test", "text/plain")
        except NetworkError:
            pass  # Expected

        # Should be able to clean up without errors
        await client.close()

        # Verify client is properly closed
        assert client._client.is_closed

    @pytest.mark.asyncio
    async def test_context_manager_cleanup_on_network_error(self):
        """Test context manager cleanup when network errors occur."""
        simulator = NetworkFailureSimulator()

        try:
            async with RemoteMDConverter("http://127.0.0.1:8999") as client:
                with simulator.connection_refused():
                    await client.convert_text("test", "text/plain")
        except NetworkError:
            pass  # Expected

        # Context manager should have cleaned up properly
        assert client._client.is_closed

    @pytest.mark.asyncio
    async def test_multiple_network_failures_in_sequence(self, client):
        """Test handling multiple different network failures."""
        simulator = NetworkFailureSimulator()

        # Test sequence of different failures
        failures = [
            simulator.connection_refused(),
            simulator.connection_timeout(0.5),
            simulator.dns_failure("127.0.0.1"),
        ]

        for failure_context in failures:
            with failure_context:
                with pytest.raises((NetworkError, TimeoutError)):
                    await client.convert_text("test", "text/plain")

    @pytest.mark.asyncio
    async def test_file_conversion_network_failure(self, client, tmp_path):
        """Test file conversion with network failures."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        simulator = NetworkFailureSimulator()

        with simulator.connection_refused():
            with pytest.raises(NetworkError):
                await client.convert_file(str(test_file))

    @pytest.mark.asyncio
    async def test_content_conversion_network_failure(self, client):
        """Test content conversion with network failures."""
        test_content = b"test content"

        simulator = NetworkFailureSimulator()

        with simulator.connection_timeout(0.5):
            with pytest.raises(TimeoutError):
                await client.convert_content(test_content, "test.txt")

    @pytest.mark.asyncio
    async def test_url_conversion_network_failure(self, client):
        """Test URL conversion with network failures."""
        simulator = NetworkFailureSimulator()

        with simulator.connection_dropped(after_bytes=100):
            with pytest.raises(NetworkError):
                await client.convert_url("https://example.com")
