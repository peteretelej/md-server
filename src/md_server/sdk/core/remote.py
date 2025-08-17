"""
Pure functions for remote API operations.

Functions for building API payloads, parsing responses, and handling
authentication without I/O dependencies.
"""

import base64
from typing import Dict, Any, Optional, Tuple

from ..models import ConversionResult, ConversionMetadata
from ..exceptions import ConversionError


def build_file_payload(
    content: bytes, filename: str, options: Dict[str, Any]
) -> Dict[str, Any]:
    """Build API payload for file conversion."""
    encoded_content = base64.b64encode(content).decode("utf-8")
    payload = {"content": encoded_content, "filename": filename}
    payload.update(options)
    return payload


def build_url_payload(url: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """Build API payload for URL conversion."""
    payload = {"url": url}
    payload.update(options)
    return payload


def build_content_payload(
    content: bytes, content_type: str, options: Dict[str, Any]
) -> Dict[str, Any]:
    """Build API payload for content conversion."""
    encoded_content = base64.b64encode(content).decode("utf-8")
    payload = {"content": encoded_content}
    if content_type:
        payload["content_type"] = content_type
    payload.update(options)
    return payload


def build_text_payload(
    text: str, mime_type: str, options: Dict[str, Any]
) -> Dict[str, Any]:
    """Build API payload for text conversion."""
    payload = {"text": text, "mime_type": mime_type}
    payload.update(options)
    return payload


def parse_conversion_response(response_data: Dict[str, Any]) -> ConversionResult:
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


def validate_api_response(response_data: Dict[str, Any]) -> None:
    """Validate API response structure."""
    if not isinstance(response_data, dict):
        raise ConversionError("Invalid response format: expected JSON object")

    if "success" not in response_data:
        raise ConversionError("Invalid response format: missing 'success' field")

    if not response_data.get("success", False):
        if "error" not in response_data:
            raise ConversionError("Invalid error response: missing 'error' field")


def extract_error_details(response_data: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """Extract error message and details from API response."""
    error = response_data.get("error", {})
    message = error.get("message", "Unknown error")
    details = error.get("details", {})
    return message, details


def merge_request_options(
    defaults: Dict[str, Any], overrides: Dict[str, Any]
) -> Dict[str, Any]:
    """Merge conversion options into request format."""
    request_options = {}

    option_mapping = {
        "js_rendering": "js_rendering",
        "extract_images": "extract_images",
        "ocr_enabled": "ocr_enabled",
        "preserve_formatting": "preserve_formatting",
        "clean_markdown": "clean_markdown",
        "timeout": "timeout",
    }

    all_options = {**defaults, **overrides}

    for sdk_key, api_key in option_mapping.items():
        if sdk_key in all_options and all_options[sdk_key] is not None:
            request_options[api_key] = all_options[sdk_key]

    return {"options": request_options} if request_options else {}


def build_auth_headers(api_key: Optional[str]) -> Dict[str, str]:
    """Build authentication headers."""
    headers = {"User-Agent": "md-server-sdk/1.0", "Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def encode_file_content(content: bytes) -> str:
    """Encode file content as base64 string."""
    return base64.b64encode(content).decode("utf-8")


def map_status_code_to_exception(
    status_code: int, message: str, details: Dict[str, Any]
) -> Exception:
    """Map HTTP status codes to appropriate SDK exceptions."""
    from ..exceptions import InvalidInputError, TimeoutError, ConversionError

    if status_code == 400:
        return InvalidInputError(message, details)
    elif status_code == 408:
        return TimeoutError(message, details)
    elif status_code == 413:
        return InvalidInputError(f"File too large: {message}", details)
    elif status_code == 415:
        return InvalidInputError(f"Unsupported format: {message}", details)
    else:
        return ConversionError(f"Server error ({status_code}): {message}", details)


def parse_http_error_response(
    response_data: Dict[str, Any], status_code: int, response_text: str
) -> Exception:
    """Parse HTTP error response and return appropriate exception."""
    from ..exceptions import ConversionError

    try:
        if "error" in response_data:
            error_info = response_data["error"]
            message = error_info.get("message", f"HTTP {status_code}")
            details = error_info.get("details", {})
            return map_status_code_to_exception(status_code, message, details)
        else:
            return ConversionError(f"HTTP {status_code}: {response_text}")
    except (KeyError, TypeError):
        return ConversionError(f"HTTP {status_code}: {response_text}")


def should_retry_request(attempt: int, max_retries: int, exception: Exception) -> bool:
    """Determine if request should be retried based on attempt count and exception type."""
    import httpx

    if attempt >= max_retries:
        return False

    # Retry on network errors and timeouts, but not on client errors
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
