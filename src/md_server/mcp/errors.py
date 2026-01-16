"""MCP error taxonomy with factory functions for structured errors."""

from .models import MCPError, MCPErrorResponse, MCPErrorDetails

# Import ErrorCode from shared module for consistency across HTTP and MCP APIs
from ..core.errors import ErrorCode


SUPPORTED_FORMATS = [
    "pdf",
    "docx",
    "doc",
    "xlsx",
    "xls",
    "pptx",
    "ppt",
    "html",
    "txt",
    "md",
    "csv",
    "json",
    "xml",
    "png",
    "jpg",
    "jpeg",
    "gif",
    "webp",
]


def timeout_error(operation: str, timeout_seconds: int) -> MCPErrorResponse:
    """Create a timeout error response."""
    return MCPErrorResponse(
        error=MCPError(
            code=ErrorCode.TIMEOUT,
            message=f"{operation} timed out after {timeout_seconds} seconds",
            suggestions=[
                "The server may be slow or unresponsive. Try again later.",
                "For JavaScript-heavy pages, try with render_js: true",
            ],
        )
    )


def connection_error(url: str, reason: str) -> MCPErrorResponse:
    """Create a connection error response."""
    return MCPErrorResponse(
        error=MCPError(
            code=ErrorCode.CONNECTION_FAILED,
            message=f"Could not connect to {url}: {reason}",
            suggestions=[
                "Check the URL is correct and accessible",
                "The server may be down or unreachable",
            ],
        )
    )


def not_found_error(url: str) -> MCPErrorResponse:
    """Create a not found (404) error response."""
    return MCPErrorResponse(
        error=MCPError(
            code=ErrorCode.NOT_FOUND,
            message=f"Page not found: {url}",
            suggestions=[
                "Verify the URL is correct",
                "The page may have been moved or deleted",
            ],
            details=MCPErrorDetails(status_code=404),
        )
    )


def access_denied_error(url: str, status_code: int = 403) -> MCPErrorResponse:
    """Create an access denied error response."""
    return MCPErrorResponse(
        error=MCPError(
            code=ErrorCode.ACCESS_DENIED,
            message=f"Access denied to {url}",
            suggestions=[
                "The page may require authentication",
                "You may not have permission to access this resource",
            ],
            details=MCPErrorDetails(status_code=status_code),
        )
    )


def invalid_url_error(url: str) -> MCPErrorResponse:
    """Create an invalid URL error response."""
    return MCPErrorResponse(
        error=MCPError(
            code=ErrorCode.INVALID_URL,
            message=f"Invalid URL format: {url}",
            suggestions=[
                "URL must start with http:// or https://",
                "Example: https://example.com/page",
            ],
        )
    )


def unsupported_format_error(
    extension: str, supported: list[str] | None = None
) -> MCPErrorResponse:
    """Create an unsupported format error response."""
    formats = supported or SUPPORTED_FORMATS
    return MCPErrorResponse(
        error=MCPError(
            code=ErrorCode.UNSUPPORTED_FORMAT,
            message=f"Unsupported file format: {extension}",
            suggestions=[
                f"Supported formats: {', '.join(formats[:10])}{'...' if len(formats) > 10 else ''}",
            ],
        )
    )


def file_too_large_error(size_mb: float, max_mb: int) -> MCPErrorResponse:
    """Create a file too large error response."""
    return MCPErrorResponse(
        error=MCPError(
            code=ErrorCode.FILE_TOO_LARGE,
            message=f"File size ({size_mb:.1f}MB) exceeds maximum ({max_mb}MB)",
            suggestions=[
                "Try compressing the file",
                "Split large documents into smaller parts",
            ],
        )
    )


def content_empty_error(source: str, tried_js: bool) -> MCPErrorResponse:
    """Create a content empty error response."""
    suggestions = ["The page may require authentication to view content"]
    if not tried_js:
        suggestions.insert(0, "Try with render_js: true for JavaScript-heavy pages")
    return MCPErrorResponse(
        error=MCPError(
            code=ErrorCode.CONTENT_EMPTY,
            message=f"Very little content extracted from {source}",
            suggestions=suggestions,
        )
    )


def unknown_tool_error(name: str) -> MCPErrorResponse:
    """Create an unknown tool error response."""
    return MCPErrorResponse(
        error=MCPError(
            code=ErrorCode.UNKNOWN_TOOL,
            message=f"Unknown tool: {name}",
            suggestions=[
                "Available tools: read_resource",
            ],
        )
    )


def conversion_error(message: str) -> MCPErrorResponse:
    """Create a generic conversion error response."""
    return MCPErrorResponse(
        error=MCPError(
            code=ErrorCode.CONVERSION_FAILED,
            message=f"Conversion failed: {message}",
            suggestions=[
                "The file may be corrupted or password-protected",
                "Try a different file format if available",
            ],
        )
    )


def invalid_input_error(message: str) -> MCPErrorResponse:
    """Create an invalid input error response."""
    return MCPErrorResponse(
        error=MCPError(
            code=ErrorCode.INVALID_INPUT,
            message=message,
            suggestions=[
                "Check the input parameters are correct",
            ],
        )
    )


def server_error(url: str, status_code: int = 500) -> MCPErrorResponse:
    """Create a server error (5xx) response."""
    return MCPErrorResponse(
        error=MCPError(
            code=ErrorCode.SERVER_ERROR,
            message=f"Server error at {url}",
            suggestions=[
                "The remote server encountered an error",
                "Try again later",
                "The website may be experiencing issues",
            ],
            details=MCPErrorDetails(status_code=status_code),
        )
    )
