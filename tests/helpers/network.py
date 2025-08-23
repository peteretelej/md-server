import asyncio
import random
import socket
import time
from contextlib import contextmanager
from typing import Generator
from unittest.mock import patch, Mock
import aiohttp


class NetworkFailureSimulator:
    """Simulates various network failure conditions for testing."""
    
    def __init__(self):
        self.original_functions = {}
    
    @contextmanager
    def connection_refused(self, target_host: str = "127.0.0.1") -> Generator[None, None, None]:
        """Simulate connection refused error for target host."""
        
        def mock_connect(*args, **kwargs):
            raise ConnectionRefusedError(f"Connection refused to {target_host}")
        
        def mock_aiohttp_request(*args, **kwargs):
            raise aiohttp.ClientConnectorError(
                connection_key="mock", 
                os_error=ConnectionRefusedError(f"Connection refused to {target_host}")
            )
        
        with patch('socket.socket.connect', side_effect=mock_connect), \
             patch('aiohttp.ClientSession.request', side_effect=mock_aiohttp_request):
            yield
    
    @contextmanager
    def connection_timeout(self, timeout_seconds: float = 1.0) -> Generator[None, None, None]:
        """Simulate connection timeout after specified seconds."""
        
        def mock_connect(*args, **kwargs):
            time.sleep(timeout_seconds + 0.1)  # Slightly longer than timeout
            raise socket.timeout(f"Connection timed out after {timeout_seconds}s")
        
        def mock_aiohttp_request(*args, **kwargs):
            raise asyncio.TimeoutError(f"Request timed out after {timeout_seconds}s")
        
        with patch('socket.socket.connect', side_effect=mock_connect), \
             patch('aiohttp.ClientSession.request', side_effect=mock_aiohttp_request):
            yield
    
    @contextmanager
    def connection_dropped(self, after_bytes: int = 1024) -> Generator[None, None, None]:
        """Simulate connection dropped after receiving specified bytes."""
        
        class MockResponse:
            def __init__(self):
                self.status = 200
                self.headers = {'content-type': 'application/json'}
                self._bytes_sent = 0
            
            async def read(self, size: int = -1):
                self._bytes_sent += size if size > 0 else 1024
                if self._bytes_sent > after_bytes:
                    raise aiohttp.ClientPayloadError("Connection broken")
                return b'{"partial": "data"}'
            
            async def text(self):
                if self._bytes_sent > after_bytes:
                    raise aiohttp.ClientPayloadError("Connection broken")
                return '{"partial": "data"}'
        
        def mock_aiohttp_request(*args, **kwargs):
            return MockResponse()
        
        with patch('aiohttp.ClientSession.request', side_effect=mock_aiohttp_request):
            yield
    
    @contextmanager
    def slow_response(self, delay_seconds: float = 2.0) -> Generator[None, None, None]:
        """Simulate slow network response with artificial delay."""
        
        original_request = None
        
        async def slow_request(*args, **kwargs):
            await asyncio.sleep(delay_seconds)
            if original_request:
                return await original_request(*args, **kwargs)
            # Fallback mock response
            mock_response = Mock()
            mock_response.status = 200
            mock_response.text = Mock(return_value='{"delayed": "response"}')
            return mock_response
        
        try:
            # Store original if it exists
            if hasattr(aiohttp.ClientSession, 'request'):
                original_request = aiohttp.ClientSession.request
            
            with patch('aiohttp.ClientSession.request', side_effect=slow_request):
                yield
        finally:
            # Restore original if we had one
            pass
    
    @contextmanager
    def intermittent_failures(self, failure_rate: float = 0.3, max_retries: int = 3) -> Generator[None, None, None]:
        """Simulate intermittent network failures with specified failure rate."""
        
        def mock_request(*args, **kwargs):
            if random.random() < failure_rate:
                raise aiohttp.ClientConnectorError(
                    connection_key="mock",
                    os_error=ConnectionError("Intermittent network failure")
                )
            # Success case - return mock response
            mock_response = Mock()
            mock_response.status = 200
            mock_response.text = Mock(return_value='{"success": true}')
            return mock_response
        
        with patch('aiohttp.ClientSession.request', side_effect=mock_request):
            yield
    
    @contextmanager
    def dns_failure(self, host: str = "example.com") -> Generator[None, None, None]:
        """Simulate DNS resolution failure for specified host."""
        
        def mock_getaddrinfo(host_arg, port, family=0, type=0, proto=0, flags=0):
            if host_arg == host:
                raise socket.gaierror(socket.EAI_NONAME, f"Name or service not known: {host}")
            # Return original behavior for other hosts
            return socket.getaddrinfo(host_arg, port, family, type, proto, flags)
        
        with patch('socket.getaddrinfo', side_effect=mock_getaddrinfo):
            yield
    
    @contextmanager
    def corrupt_response(self, corruption_rate: float = 0.1) -> Generator[None, None, None]:
        """Simulate response data corruption."""
        
        class CorruptResponse:
            def __init__(self):
                self.status = 200
                self.headers = {'content-type': 'application/json'}
            
            async def read(self, size: int = -1):
                data = b'{"valid": "json", "data": "content"}'
                if random.random() < corruption_rate:
                    # Corrupt random bytes
                    data_list = list(data)
                    corrupt_idx = random.randint(0, len(data_list) - 1)
                    data_list[corrupt_idx] = random.randint(0, 255)
                    return bytes(data_list)
                return data
            
            async def text(self):
                data = await self.read()
                try:
                    return data.decode('utf-8')
                except UnicodeDecodeError:
                    raise aiohttp.ClientPayloadError("Response data corrupted")
        
        def mock_request(*args, **kwargs):
            return CorruptResponse()
        
        with patch('aiohttp.ClientSession.request', side_effect=mock_request):
            yield
    
    @contextmanager
    def bandwidth_limit(self, bytes_per_second: int = 1024) -> Generator[None, None, None]:
        """Simulate bandwidth-limited connection."""
        
        class ThrottledResponse:
            def __init__(self):
                self.status = 200
                self.headers = {'content-type': 'application/json'}
                self._data = b'{"throttled": "response", "data": "' + b'x' * 10000 + b'"}'
            
            async def read(self, size: int = -1):
                if size <= 0:
                    size = len(self._data)
                
                # Simulate throttling
                chunk_size = min(size, bytes_per_second)
                await asyncio.sleep(chunk_size / bytes_per_second)
                
                return self._data[:chunk_size]
            
            async def text(self):
                data = await self.read()
                return data.decode('utf-8')
        
        def mock_request(*args, **kwargs):
            return ThrottledResponse()
        
        with patch('aiohttp.ClientSession.request', side_effect=mock_request):
            yield


# Convenience functions for common network failure scenarios
def simulate_network_partition(duration: float = 1.0):
    """Context manager for complete network partition."""
    simulator = NetworkFailureSimulator()
    return simulator.connection_refused()


def simulate_flaky_network(failure_rate: float = 0.2):
    """Context manager for intermittent network issues."""
    simulator = NetworkFailureSimulator()
    return simulator.intermittent_failures(failure_rate)


def simulate_slow_network(delay: float = 2.0):
    """Context manager for slow network responses."""
    simulator = NetworkFailureSimulator()
    return simulator.slow_response(delay)