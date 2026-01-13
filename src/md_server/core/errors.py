"""Shared error module for HTTP and MCP error handling.

Provides a unified ErrorCode enum and typed exception hierarchy for
classifying HTTP fetch errors, network errors, and conversion errors.
"""

import re
from enum import Enum
from typing import Optional


class ErrorCode(str, Enum):
    """Standard error codes for API responses."""

    TIMEOUT = "TIMEOUT"
    CONNECTION_FAILED = "CONNECTION_FAILED"
    NOT_FOUND = "NOT_FOUND"
    ACCESS_DENIED = "ACCESS_DENIED"
    SERVER_ERROR = "SERVER_ERROR"
    INVALID_URL = "INVALID_URL"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    CONVERSION_FAILED = "CONVERSION_FAILED"
    CONTENT_EMPTY = "CONTENT_EMPTY"
    INVALID_INPUT = "INVALID_INPUT"
    UNKNOWN_TOOL = "UNKNOWN_TOOL"


class ConversionError(Exception):
    """Base exception for conversion errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.CONVERSION_FAILED,
        suggestions: Optional[list[str]] = None,
    ):
        super().__init__(message)
        self.code = code
        self.suggestions = suggestions or [
            "The file may be corrupted or password-protected",
            "Try a different file format if available",
        ]


class HTTPFetchError(ConversionError):
    """Error fetching URL via HTTP."""

    def __init__(
        self,
        message: str,
        code: ErrorCode,
        status_code: Optional[int] = None,
        suggestions: Optional[list[str]] = None,
    ):
        super().__init__(message, code, suggestions)
        self.status_code = status_code


class NotFoundError(HTTPFetchError):
    """HTTP 404 Not Found error."""

    def __init__(self, url: str):
        super().__init__(
            message=f"Page not found: {url}",
            code=ErrorCode.NOT_FOUND,
            status_code=404,
            suggestions=[
                "Verify the URL is correct",
                "The page may have been moved or deleted",
                "Check for typos in the URL",
            ],
        )
        self.url = url


class AccessDeniedError(HTTPFetchError):
    """HTTP 401/403 access denied error."""

    def __init__(self, url: str, status_code: int = 403):
        if status_code == 401:
            suggestions = [
                "The page requires authentication",
                "Try logging in first and using an authenticated session",
            ]
        else:
            suggestions = [
                "You may not have permission to access this resource",
                "The server may be blocking automated requests",
            ]

        super().__init__(
            message=f"Access denied: {url}",
            code=ErrorCode.ACCESS_DENIED,
            status_code=status_code,
            suggestions=suggestions,
        )
        self.url = url


class ServerError(HTTPFetchError):
    """HTTP 5xx server error."""

    def __init__(self, url: str, status_code: int = 500):
        super().__init__(
            message=f"Server error at {url}",
            code=ErrorCode.SERVER_ERROR,
            status_code=status_code,
            suggestions=[
                "The remote server encountered an error",
                "Try again later",
                "The website may be experiencing issues",
            ],
        )
        self.url = url


class URLTimeoutError(ConversionError):
    """URL request timeout error."""

    def __init__(self, url: str, timeout: int):
        super().__init__(
            message=f"Request to {url} timed out after {timeout}s",
            code=ErrorCode.TIMEOUT,
            suggestions=[
                "The server is taking too long to respond",
                "Try again later",
                "For JavaScript-heavy pages, try with render_js: true",
            ],
        )
        self.url = url
        self.timeout = timeout


class URLConnectionError(ConversionError):
    """Network/connection error when fetching URL."""

    def __init__(self, url: str, reason: str):
        super().__init__(
            message=f"Could not connect to {url}: {reason}",
            code=ErrorCode.CONNECTION_FAILED,
            suggestions=[
                "Check the URL is correct and accessible",
                "The server may be down or unreachable",
                "Check your network connection",
            ],
        )
        self.url = url
        self.reason = reason


# Regex pattern to extract HTTP status code from error messages
# Matches patterns like "404 Client Error: Not Found for url: ..."
HTTP_ERROR_PATTERN = re.compile(
    r"(\d{3})\s+(?:Client|Server)\s+Error:\s*(.+?)(?:\s+for url:|\Z)",
    re.IGNORECASE,
)


def parse_http_status_from_error(error: Exception) -> tuple[Optional[int], str]:
    """Extract HTTP status code and message from requests/httpx exceptions.

    Args:
        error: The exception to parse

    Returns:
        Tuple of (status_code, message). status_code is None if not found.
    """
    error_msg = str(error)
    match = HTTP_ERROR_PATTERN.search(error_msg)
    if match:
        return int(match.group(1)), match.group(2).strip()
    return None, error_msg


def classify_http_error(error: Exception, url: str) -> HTTPFetchError:
    """Classify an HTTP error into the appropriate exception type.

    Args:
        error: The original exception
        url: The URL that was being fetched

    Returns:
        An appropriate HTTPFetchError subclass
    """
    status_code, message = parse_http_status_from_error(error)

    if status_code:
        if status_code == 404:
            return NotFoundError(url)
        elif status_code in (401, 403):
            return AccessDeniedError(url, status_code)
        elif 400 <= status_code < 500:
            # Other 4xx errors
            return HTTPFetchError(
                message=f"Client error ({status_code}): {message}",
                code=ErrorCode.ACCESS_DENIED,
                status_code=status_code,
                suggestions=[
                    "Check the URL is correct",
                    "The request may be malformed",
                ],
            )
        elif 500 <= status_code < 600:
            return ServerError(url, status_code)

    # Check for common error patterns in the message
    error_lower = str(error).lower()

    if "timeout" in error_lower or "timed out" in error_lower:
        return HTTPFetchError(
            message=f"Request timed out: {url}",
            code=ErrorCode.TIMEOUT,
            suggestions=[
                "The server is taking too long to respond",
                "Try again later",
            ],
        )

    if "connection" in error_lower or "connect" in error_lower:
        return HTTPFetchError(
            message=f"Connection error: {url}",
            code=ErrorCode.CONNECTION_FAILED,
            suggestions=[
                "Check the URL is correct and accessible",
                "The server may be down or unreachable",
            ],
        )

    if "not found" in error_lower or "404" in error_lower:
        return NotFoundError(url)

    if "forbidden" in error_lower or "403" in error_lower:
        return AccessDeniedError(url, 403)

    if "unauthorized" in error_lower or "401" in error_lower:
        return AccessDeniedError(url, 401)

    # Fallback to generic HTTP fetch error - use CONNECTION_FAILED since
    # the error occurred during URL fetching, not document conversion
    return HTTPFetchError(
        message=f"Failed to fetch URL: {error}",
        code=ErrorCode.CONNECTION_FAILED,
        suggestions=[
            "Check the URL is accessible",
            "Try again later",
        ],
    )
