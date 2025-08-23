"""
Remote converter client for md-server API.
"""

import asyncio
from typing import Optional, Union, Dict, Any
from pathlib import Path

import httpx

from .models import ConversionResult
from .exceptions import ConversionError, NetworkError, TimeoutError, InvalidInputError
from .sync import SyncConverterMixin, sync_wrapper
from .core import (
    build_file_payload,
    build_url_payload,
    build_text_payload,
    parse_conversion_response,
    merge_request_options,
    parse_http_error_response,
)
from .core.utils import (
    build_auth_headers,
    should_retry_request,
    calculate_retry_delay,
    classify_request_exception,
)
from .core.validation import validate_file_path


class RemoteMDConverter(SyncConverterMixin):
    """
    Remote converter client for md-server API.

    Provides a client interface to connect to remote md-server instances
    for document conversion. Handles authentication, connection pooling,
    retry logic, and error mapping.

    Example:
        >>> client = RemoteMDConverter(
        ...     endpoint="https://api.example.com",
        ...     api_key="your-secret-key",
        ...     timeout=30
        ... )
        >>> result = await client.convert_file("document.pdf")
    """

    def __init__(
        self,
        endpoint: str,
        api_key: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """Initialize remote converter client.

        Args:
            endpoint: Base URL of the md-server API
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retry attempts in seconds
        """
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Initialize HTTP client with connection pooling
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            headers=build_auth_headers(self.api_key),
        )

    async def __aenter__(self):
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        await self.close()

    async def close(self):
        """Close the HTTP client and clean up resources."""
        if hasattr(self, "_client"):
            await self._client.aclose()

    async def _make_request_with_retry(
        self, method: str, path: str, **kwargs
    ) -> httpx.Response:
        """Make HTTP request with retry logic and error handling."""
        url = f"{self.endpoint}{path}"
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.request(method, url, **kwargs)

                # Handle HTTP errors
                if response.status_code >= 400:
                    await self._handle_http_error(response)

                return response

            except Exception as e:
                # Classify and handle the exception
                exception_type = classify_request_exception(e)

                if exception_type == "timeout":
                    last_exception = TimeoutError(
                        f"Request timed out after {self.timeout}s", {"url": url}
                    )
                elif exception_type == "network":
                    last_exception = NetworkError(
                        f"Network error: {str(e)}", {"url": url}
                    )
                else:
                    last_exception = ConversionError(
                        f"Unexpected error: {str(e)}", {"url": url}
                    )

                # Check if we should retry
                if should_retry_request(attempt, self.max_retries, e):
                    delay = calculate_retry_delay(attempt, self.retry_delay)
                    await asyncio.sleep(delay)
                    continue
                break

        if last_exception:
            raise last_exception

        raise ConversionError("All retry attempts failed")

    async def _handle_http_error(self, response: httpx.Response):
        """Handle HTTP error responses and map to appropriate exceptions."""
        try:
            error_data = response.json()
        except (ValueError, KeyError):
            error_data = {}

        exception = parse_http_error_response(
            error_data, response.status_code, response.text
        )
        raise exception

    async def convert_file(
        self, file_path: Union[str, Path], **options
    ) -> ConversionResult:
        """Convert a local file using remote API."""
        path = validate_file_path(str(file_path))

        if not path.exists():
            raise InvalidInputError(f"File not found: {file_path}")
        if not path.is_file():
            raise InvalidInputError(f"Path is not a file: {file_path}")

        try:
            content = path.read_bytes()
        except PermissionError:
            raise InvalidInputError(f"Permission denied reading file: {file_path}")
        except Exception as e:
            raise InvalidInputError(f"Error reading file {file_path}: {str(e)}")

        return await self.convert_content(content, filename=path.name, **options)

    async def convert_url(self, url: str, **options) -> ConversionResult:
        """Convert a URL using remote API."""
        if not url or not isinstance(url, str):
            raise InvalidInputError("URL cannot be empty")

        url = url.strip()
        if not url:
            raise InvalidInputError("URL cannot be empty")

        # Basic URL format validation
        if "://" not in url:
            raise InvalidInputError("Invalid URL format")

        # Check protocol
        if not (url.startswith("http://") or url.startswith("https://")):
            raise InvalidInputError("Only HTTP/HTTPS URLs allowed")

        request_options = merge_request_options({}, options)
        request_data = build_url_payload(url, request_options)

        response = await self._make_request_with_retry(
            "POST",
            "/convert",
            json=request_data,
            headers={"Content-Type": "application/json"},
        )

        return parse_conversion_response(response.json())

    async def convert_content(
        self, content: bytes, filename: Optional[str] = None, **options
    ) -> ConversionResult:
        """Convert binary content using remote API."""
        if not isinstance(content, bytes):
            raise InvalidInputError("Content must be bytes")

        if len(content) == 0:
            raise InvalidInputError("Content cannot be empty")

        request_options = merge_request_options({}, options)
        request_data = build_file_payload(
            content, filename or "unknown", request_options
        )

        response = await self._make_request_with_retry(
            "POST",
            "/convert",
            json=request_data,
            headers={"Content-Type": "application/json"},
        )

        return parse_conversion_response(response.json())

    async def convert_text(
        self, text: str, mime_type: str, **options
    ) -> ConversionResult:
        """Convert text with MIME type using remote API."""
        if not isinstance(text, str):
            raise InvalidInputError("Text must be a string")

        if not text.strip():
            raise InvalidInputError("Text cannot be empty")

        if not mime_type or not isinstance(mime_type, str):
            raise InvalidInputError("MIME type cannot be empty")

        mime_type = mime_type.strip()
        if not mime_type:
            raise InvalidInputError("MIME type cannot be empty")

        # Basic MIME type validation
        if "/" not in mime_type:
            raise InvalidInputError("MIME type must contain '/'")

        request_options = merge_request_options({}, options)
        request_data = build_text_payload(text, mime_type, request_options)

        response = await self._make_request_with_retry(
            "POST",
            "/convert",
            json=request_data,
            headers={"Content-Type": "application/json"},
        )

        return parse_conversion_response(response.json())

    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the remote server."""
        try:
            response = await self._make_request_with_retry("GET", "/health")
            return response.json()
        except Exception as e:
            raise NetworkError(f"Health check failed: {str(e)}")

    async def get_formats(self) -> Dict[str, Any]:
        """Get supported formats from the remote server."""
        try:
            response = await self._make_request_with_retry("GET", "/formats")
            return response.json()
        except Exception as e:
            raise NetworkError(f"Failed to get formats: {str(e)}")

    # Sync API Methods

    def convert_file_sync(
        self, file_path: Union[str, Path], **options
    ) -> ConversionResult:
        """Synchronous version of convert_file."""
        return sync_wrapper(self.convert_file)(file_path, **options)

    def convert_url_sync(self, url: str, **options) -> ConversionResult:
        """Synchronous version of convert_url."""
        return sync_wrapper(self.convert_url)(url, **options)

    def convert_content_sync(
        self, content: bytes, filename: Optional[str] = None, **options
    ) -> ConversionResult:
        """Synchronous version of convert_content."""
        return sync_wrapper(self.convert_content)(content, filename=filename, **options)

    def convert_text_sync(
        self, text: str, mime_type: str, **options
    ) -> ConversionResult:
        """Synchronous version of convert_text."""
        return sync_wrapper(self.convert_text)(text, mime_type, **options)

    def health_check_sync(self) -> Dict[str, Any]:
        """Synchronous version of health_check."""
        return sync_wrapper(self.health_check)()

    def get_formats_sync(self) -> Dict[str, Any]:
        """Synchronous version of get_formats."""
        return sync_wrapper(self.get_formats)()
