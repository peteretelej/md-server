"""
Remote converter client for md-server API.
"""

import asyncio
import base64
from typing import Optional, Union, Dict, Any
from pathlib import Path

import httpx

from .models import ConversionResult, ConversionMetadata
from .exceptions import ConversionError, NetworkError, TimeoutError, InvalidInputError
from .sync import SyncConverterMixin, sync_wrapper


class RemoteMDConverter(SyncConverterMixin):
    """Remote converter client for md-server API."""

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
            headers=self._build_headers(),
        )

    def _build_headers(self) -> Dict[str, str]:
        """Build default headers for requests."""
        headers = {"User-Agent": "md-server-sdk/1.0", "Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

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

            except httpx.TimeoutException:
                last_exception = TimeoutError(
                    f"Request timed out after {self.timeout}s", {"url": url}
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(
                        self.retry_delay * (2**attempt)
                    )  # Exponential backoff
                    continue
                break

            except (
                httpx.NetworkError,
                httpx.ConnectError,
                ConnectionError,
                OSError,
            ) as e:
                last_exception = NetworkError(f"Network error: {str(e)}", {"url": url})
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * (2**attempt))
                    continue
                break

            except Exception as e:
                # Catch-all for other connection issues
                error_msg = str(e).lower()
                if any(
                    term in error_msg
                    for term in ["connection", "network", "refused", "unreachable"]
                ):
                    last_exception = NetworkError(
                        f"Network error: {str(e)}", {"url": url}
                    )
                else:
                    last_exception = ConversionError(
                        f"Unexpected error: {str(e)}", {"url": url}
                    )
                break

        if last_exception:
            raise last_exception

        raise ConversionError("All retry attempts failed")

    async def _handle_http_error(self, response: httpx.Response):
        """Handle HTTP error responses and map to appropriate exceptions."""
        try:
            error_data = response.json()
            if "error" in error_data:
                error_info = error_data["error"]
                message = error_info.get("message", f"HTTP {response.status_code}")
                details = error_info.get("details", {})

                # Map HTTP status codes to SDK exceptions
                if response.status_code == 400:
                    raise InvalidInputError(message, details)
                elif response.status_code == 408:
                    raise TimeoutError(message, details)
                elif response.status_code == 413:
                    raise InvalidInputError(f"File too large: {message}", details)
                elif response.status_code == 415:
                    raise InvalidInputError(f"Unsupported format: {message}", details)
                else:
                    raise ConversionError(
                        f"Server error ({response.status_code}): {message}", details
                    )
            else:
                raise ConversionError(f"HTTP {response.status_code}: {response.text}")

        except (ValueError, KeyError):
            # Response is not valid JSON or doesn't have expected structure
            raise ConversionError(f"HTTP {response.status_code}: {response.text}")

    def _parse_response(self, response_data: Dict[str, Any]) -> ConversionResult:
        """Parse API response to ConversionResult."""
        if not response_data.get("success", False):
            error = response_data.get("error", {})
            raise ConversionError(
                error.get("message", "Unknown error"), error.get("details", {})
            )

        metadata_data = response_data.get("metadata", {})
        metadata = ConversionMetadata(
            source_type=metadata_data.get("source_type", "unknown"),
            source_size=metadata_data.get("source_size", 0),
            markdown_size=metadata_data.get("markdown_size", 0),
            processing_time=metadata_data.get("conversion_time_ms", 0) / 1000.0,
            detected_format=metadata_data.get("detected_format", "unknown"),
            warnings=metadata_data.get("warnings", []),
        )

        return ConversionResult(
            markdown=response_data.get("markdown", ""),
            metadata=metadata,
            success=True,
            request_id=response_data.get("request_id", ""),
        )

    def _merge_options(self, **options) -> Dict[str, Any]:
        """Merge conversion options into request format."""
        request_options = {}

        # Map SDK options to API options
        option_mapping = {
            "js_rendering": "js_rendering",
            "extract_images": "extract_images",
            "ocr_enabled": "ocr_enabled",
            "preserve_formatting": "preserve_formatting",
            "clean_markdown": "clean_markdown",
            "timeout": "timeout",
        }

        for sdk_key, api_key in option_mapping.items():
            if sdk_key in options and options[sdk_key] is not None:
                request_options[api_key] = options[sdk_key]

        return {"options": request_options} if request_options else {}

    async def convert_file(
        self, file_path: Union[str, Path], **options
    ) -> ConversionResult:
        """Convert a local file using remote API."""
        path = Path(file_path)
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
            raise InvalidInputError("URL must be a non-empty string")

        request_data = {"url": url, **self._merge_options(**options)}

        response = await self._make_request_with_retry(
            "POST",
            "/convert",
            json=request_data,
            headers={"Content-Type": "application/json"},
        )

        return self._parse_response(response.json())

    async def convert_content(
        self, content: bytes, filename: Optional[str] = None, **options
    ) -> ConversionResult:
        """Convert binary content using remote API."""
        if not isinstance(content, bytes):
            raise InvalidInputError("Content must be bytes")

        if len(content) == 0:
            raise InvalidInputError("Content cannot be empty")

        # Encode content as base64 for JSON transmission
        encoded_content = base64.b64encode(content).decode("utf-8")

        request_data = {"content": encoded_content, **self._merge_options(**options)}

        if filename:
            request_data["filename"] = filename

        response = await self._make_request_with_retry(
            "POST",
            "/convert",
            json=request_data,
            headers={"Content-Type": "application/json"},
        )

        return self._parse_response(response.json())

    async def convert_text(
        self, text: str, mime_type: str, **options
    ) -> ConversionResult:
        """Convert text with MIME type using remote API."""
        if not isinstance(text, str):
            raise InvalidInputError("Text must be a string")

        if not text.strip():
            raise InvalidInputError("Text cannot be empty")

        if not mime_type or not isinstance(mime_type, str):
            raise InvalidInputError("MIME type must be a non-empty string")

        request_data = {
            "text": text,
            "mime_type": mime_type,
            **self._merge_options(**options),
        }

        response = await self._make_request_with_retry(
            "POST",
            "/convert",
            json=request_data,
            headers={"Content-Type": "application/json"},
        )

        return self._parse_response(response.json())

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
