"""
Utility functions for remote SDK operations.
"""

from typing import Dict, Optional


def build_auth_headers(api_key: Optional[str]) -> Dict[str, str]:
    """Build authentication headers."""
    headers = {"User-Agent": "md-server-sdk/1.0", "Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def classify_request_exception(exception: Exception) -> str:
    """Classify exception type for error handling logic."""
    import httpx

    error_msg = str(exception).lower()

    if isinstance(exception, httpx.TimeoutException):
        return "timeout"
    elif isinstance(
        exception, (httpx.NetworkError, httpx.ConnectError, ConnectionError, OSError)
    ):
        return "network"
    elif any(
        term in error_msg
        for term in ["connection", "network", "refused", "unreachable"]
    ):
        return "network"
    else:
        return "unknown"


def should_retry_request(attempt: int, max_retries: int, exception: Exception) -> bool:
    """Determine if request should be retried based on attempt count and exception type."""
    import httpx

    if attempt >= max_retries:
        return False

    retry_exceptions = (
        httpx.TimeoutException,
        httpx.NetworkError,
        httpx.ConnectError,
        ConnectionError,
        OSError,
    )

    return isinstance(exception, retry_exceptions)


def calculate_retry_delay(attempt: int, base_delay: float) -> float:
    """Calculate exponential backoff delay for retry attempts."""
    return base_delay * (2**attempt)