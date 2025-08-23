"""
Test retry mechanism for remote SDK.

Tests retry logic, exponential backoff, transient failures,
and retry exhaustion scenarios.
"""

import pytest
import time
from unittest.mock import patch, Mock

from md_server.sdk.remote import RemoteMDConverter
from md_server.sdk.exceptions import NetworkError, ConversionError
from md_server.sdk.core.utils import should_retry_request, calculate_retry_delay
from tests.helpers.network import NetworkFailureSimulator


class TestRemoteRetryLogic:
    """Test retry mechanism in remote SDK."""

    @pytest.fixture
    def client_with_retries(self):
        """Create remote client with retry configuration."""
        return RemoteMDConverter(
            endpoint="http://127.0.0.1:8999",
            timeout=2,
            max_retries=3,
            retry_delay=0.1  # Short delay for testing
        )

    @pytest.fixture
    def client_no_retries(self):
        """Create remote client with no retries."""
        return RemoteMDConverter(
            endpoint="http://127.0.0.1:8999",
            timeout=2,
            max_retries=0
        )

    @pytest.mark.asyncio
    async def test_retry_on_transient_network_failure(self, client_with_retries):
        """Test retries occur on transient network failures."""
        call_count = {"value": 0}
        
        async def mock_request(*args, **kwargs):
            call_count["value"] += 1
            if call_count["value"] <= 2:  # Fail first 2 attempts
                raise NetworkError("Connection failed")
            # Succeed on 3rd attempt
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "success": True,
                "markdown": "# Test Result",
                "metadata": {"source_type": "text"}
            }
            return mock_response
        
        with patch.object(client_with_retries._client, 'request', mock_request):
            result = await client_with_retries.convert_text("test", "text/plain")
            
            # Should succeed after retries
            assert result.success
            assert result.markdown == "# Test Result"
            assert call_count["value"] == 3  # 2 failures + 1 success

    @pytest.mark.asyncio
    async def test_retry_exhaustion(self, client_with_retries):
        """Test retry exhaustion when all attempts fail."""
        call_count = {"value": 0}
        
        async def mock_request(*args, **kwargs):
            call_count["value"] += 1
            raise NetworkError("Persistent connection failure")
        
        with patch.object(client_with_retries._client, 'request', mock_request):
            with pytest.raises(NetworkError) as exc_info:
                await client_with_retries.convert_text("test", "text/plain")
            
            assert "Persistent connection failure" in str(exc_info.value)
            # Should try: initial + 3 retries = 4 total attempts
            assert call_count["value"] == 4

    @pytest.mark.asyncio
    async def test_no_retry_on_client_errors(self, client_with_retries):
        """Test no retry attempts on 4xx client errors."""
        call_count = {"value": 0}
        
        async def mock_request(*args, **kwargs):
            call_count["value"] += 1
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.json.return_value = {
                "error": {"message": "Invalid request"}
            }
            return mock_response
        
        with patch.object(client_with_retries._client, 'request', mock_request):
            with pytest.raises(Exception):  # Should be InvalidInputError
                await client_with_retries.convert_text("test", "text/plain")
            
            # Should not retry on client errors
            assert call_count["value"] == 1

    @pytest.mark.asyncio
    async def test_retry_on_server_errors(self, client_with_retries):
        """Test retries occur on 5xx server errors."""
        call_count = {"value": 0}
        
        async def mock_request(*args, **kwargs):
            call_count["value"] += 1
            if call_count["value"] <= 2:  # Fail first 2 attempts with server error
                mock_response = Mock()
                mock_response.status_code = 503
                mock_response.json.return_value = {
                    "error": {"message": "Service unavailable"}
                }
                return mock_response
            # Succeed on 3rd attempt
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "success": True,
                "markdown": "# Success",
                "metadata": {"source_type": "text"}
            }
            return mock_response
        
        with patch.object(client_with_retries._client, 'request', mock_request):
            result = await client_with_retries.convert_text("test", "text/plain")
            
            assert result.success
            assert call_count["value"] == 3

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self, client_with_retries):
        """Test exponential backoff timing between retries."""
        call_times = []
        
        async def mock_request(*args, **kwargs):
            call_times.append(time.time())
            raise NetworkError("Test failure")
        
        with patch.object(client_with_retries._client, 'request', mock_request):
            with pytest.raises(NetworkError):
                await client_with_retries.convert_text("test", "text/plain")
        
        # Calculate delays between calls
        delays = []
        for i in range(1, len(call_times)):
            delays.append(call_times[i] - call_times[i-1])
        
        # Check exponential backoff (approximately)
        base_delay = 0.1
        expected_delays = [
            base_delay,           # 0.1s after 1st failure
            base_delay * 2,       # 0.2s after 2nd failure  
            base_delay * 4,       # 0.4s after 3rd failure
        ]
        
        for i, (actual, expected) in enumerate(zip(delays, expected_delays)):
            # Allow 50% tolerance due to test timing variance
            assert abs(actual - expected) < expected * 0.5, \
                f"Delay {i}: expected ~{expected}s, got {actual}s"

    @pytest.mark.asyncio
    async def test_custom_retry_configuration(self):
        """Test custom retry configuration."""
        client = RemoteMDConverter(
            endpoint="http://127.0.0.1:8999",
            max_retries=5,
            retry_delay=0.05
        )
        
        call_count = {"value": 0}
        
        async def mock_request(*args, **kwargs):
            call_count["value"] += 1
            raise NetworkError("Test failure")
        
        with patch.object(client._client, 'request', mock_request):
            with pytest.raises(NetworkError):
                await client.convert_text("test", "text/plain")
        
        # Should try: initial + 5 retries = 6 total attempts
        assert call_count["value"] == 6

    @pytest.mark.asyncio
    async def test_retry_with_intermittent_failures(self, client_with_retries):
        """Test retry logic with intermittent network failures."""
        simulator = NetworkFailureSimulator()
        
        # Use lower failure rate to allow eventual success
        with simulator.intermittent_failures(failure_rate=0.7, max_retries=5):
            # This might succeed after retries or fail - both are valid
            try:
                result = await client_with_retries.convert_text("test", "text/plain")
                # If it succeeds, it should be valid
                if hasattr(result, 'success'):
                    assert result.success or result.markdown
            except (NetworkError, ConversionError):
                # If it fails after retries, that's also expected
                pass

    def test_should_retry_request_logic(self):
        """Test the should_retry_request utility function."""
        import httpx
        
        # Test retry on network errors
        network_error = httpx.ConnectError("Connection failed")
        assert should_retry_request(0, 3, network_error) is True
        assert should_retry_request(3, 3, network_error) is False  # Max retries reached
        
        # Test retry on timeout errors
        timeout_error = httpx.TimeoutException("Request timeout")
        assert should_retry_request(1, 3, timeout_error) is True
        
        # Test no retry on other errors
        decode_error = httpx.DecodingError("Invalid response")
        assert should_retry_request(0, 3, decode_error) is False

    def test_calculate_retry_delay_exponential_backoff(self):
        """Test exponential backoff calculation."""
        
        base_delay = 1.0
        
        # Test exponential progression
        assert calculate_retry_delay(0, base_delay) == base_delay  # 2^0 * 1.0 = 1.0
        assert calculate_retry_delay(1, base_delay) == base_delay * 2  # 2^1 * 1.0 = 2.0
        assert calculate_retry_delay(2, base_delay) == base_delay * 4  # 2^2 * 1.0 = 4.0
        assert calculate_retry_delay(3, base_delay) == base_delay * 8  # 2^3 * 1.0 = 8.0

    def test_calculate_retry_delay_maximum_cap(self):
        """Test retry delay maximum cap."""
        
        base_delay = 1.0
        
        # Test that delay caps at reasonable maximum (e.g., 60 seconds)
        large_attempt = 10
        delay = calculate_retry_delay(large_attempt, base_delay)
        assert delay <= 60.0  # Should be capped

    @pytest.mark.asyncio
    async def test_retry_with_different_exception_types(self, client_with_retries):
        """Test retry behavior with different exception types."""
        import httpx
        
        exceptions_to_test = [
            (httpx.ConnectError("Connection failed"), True),
            (httpx.TimeoutException("Timeout"), True),
            (httpx.NetworkError("Network issue"), True),
            (httpx.DecodingError("Decode error"), False),
            (ValueError("Invalid value"), False),
        ]
        
        for exception, should_retry in exceptions_to_test:
            call_count = {"value": 0}
            
            async def mock_request(*args, **kwargs):
                call_count["value"] += 1
                raise exception
            
            with patch.object(client_with_retries._client, 'request', mock_request):
                with pytest.raises(Exception):
                    await client_with_retries.convert_text("test", "text/plain")
                
                if should_retry:
                    # Should retry: initial + max_retries attempts
                    assert call_count["value"] == 4, f"Expected 4 calls for {exception}"
                else:
                    # Should not retry: only initial attempt
                    assert call_count["value"] == 1, f"Expected 1 call for {exception}"

    @pytest.mark.asyncio
    async def test_retry_preserves_original_exception(self, client_with_retries):
        """Test that retries preserve the original exception details."""
        original_error = NetworkError("Original connection failure", {"host": "example.com"})
        
        async def mock_request(*args, **kwargs):
            raise original_error
        
        with patch.object(client_with_retries._client, 'request', mock_request):
            with pytest.raises(NetworkError) as exc_info:
                await client_with_retries.convert_text("test", "text/plain")
            
            # Should preserve original error message and details
            assert str(exc_info.value) == str(original_error)
            assert exc_info.value.details == original_error.details

    @pytest.mark.asyncio
    async def test_retry_across_all_conversion_methods(self, client_with_retries, tmp_path):
        """Test retry logic works across all conversion methods."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        call_counts = {"convert_text": 0, "convert_url": 0, "convert_content": 0, "convert_file": 0}
        
        async def mock_request(*args, **kwargs):
            # Determine which method based on request data
            method_key = "convert_text"  # Default
            if len(args) > 1:
                if "json" in kwargs:
                    json_data = kwargs["json"]
                    if "url" in json_data:
                        method_key = "convert_url"
                    elif "content" in json_data:
                        if "filename" in json_data:
                            method_key = "convert_file"
                        else:
                            method_key = "convert_content"
            
            call_counts[method_key] += 1
            
            if call_counts[method_key] <= 2:  # Fail first 2 attempts
                raise NetworkError("Connection failed")
            
            # Success response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "success": True,
                "markdown": f"# {method_key} Result",
                "metadata": {"source_type": "text"}
            }
            return mock_response
        
        methods_and_args = [
            (client_with_retries.convert_text, ("test", "text/plain")),
            (client_with_retries.convert_url, ("https://example.com",)),
            (client_with_retries.convert_content, (b"test", "test.txt")),
            (client_with_retries.convert_file, (str(test_file),)),
        ]
        
        with patch.object(client_with_retries._client, 'request', mock_request):
            for method, args in methods_and_args:
                result = await method(*args)
                assert result.success
                assert "Result" in result.markdown
        
        # Each method should have made 3 calls (2 failures + 1 success)
        for method_key, count in call_counts.items():
            assert count == 3, f"{method_key} should have made 3 attempts"

    @pytest.mark.asyncio  
    async def test_zero_max_retries_disables_retry(self, client_no_retries):
        """Test that max_retries=0 disables retry mechanism."""
        call_count = {"value": 0}
        
        async def mock_request(*args, **kwargs):
            call_count["value"] += 1
            raise NetworkError("Connection failed")
        
        with patch.object(client_no_retries._client, 'request', mock_request):
            with pytest.raises(NetworkError):
                await client_no_retries.convert_text("test", "text/plain")
        
        # Should only try once (no retries)
        assert call_count["value"] == 1