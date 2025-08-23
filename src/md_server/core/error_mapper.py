"""
Error mapping and response generation functions.
"""

import base64
from typing import Dict, Any, Tuple
from litestar.status_codes import (
    HTTP_400_BAD_REQUEST,
    HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    HTTP_408_REQUEST_TIMEOUT,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_413_REQUEST_ENTITY_TOO_LARGE,
)

from ..sdk.exceptions import (
    InvalidInputError,
    NetworkError,
    TimeoutError,
    FileSizeError,
    UnsupportedFormatError,
)


def map_conversion_error(error: Exception) -> Tuple[str, str, int, list]:
    """Map SDK exceptions to HTTP error responses.
    
    Args:
        error: SDK exception to map
        
    Returns:
        Tuple of (error_code, message, status_code, suggestions)
    """
    if isinstance(error, InvalidInputError):
        return (
            "INVALID_INPUT",
            str(error),
            HTTP_400_BAD_REQUEST,
            ["Check input format", "Verify request structure"]
        )
    elif isinstance(error, FileSizeError):
        return (
            "FILE_TOO_LARGE",
            str(error),
            HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            ["Use a smaller file", "Check size limits at /formats"]
        )
    elif isinstance(error, UnsupportedFormatError):
        return (
            "UNSUPPORTED_FORMAT",
            str(error),
            HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            ["Check supported formats at /formats"]
        )
    elif isinstance(error, TimeoutError):
        return (
            "TIMEOUT",
            str(error),
            HTTP_408_REQUEST_TIMEOUT,
            ["Try with a smaller file", "Increase timeout in options"]
        )
    elif isinstance(error, NetworkError):
        return (
            "NETWORK_ERROR",
            str(error),
            HTTP_400_BAD_REQUEST,
            ["Check URL accessibility", "Verify network connectivity"]
        )
    else:  # ConversionError or generic
        return (
            "CONVERSION_FAILED",
            str(error),
            HTTP_500_INTERNAL_SERVER_ERROR,
            ["Check input format", "Contact support if issue persists"]
        )


def map_value_error(error_msg: str) -> Tuple[str, int, list]:
    """Map ValueError messages to HTTP error responses.
    
    Args:
        error_msg: Error message to classify
        
    Returns:
        Tuple of (error_code, status_code, suggestions)
    """
    error_mappings = [
        (
            ["size", "exceeds"],
            "FILE_TOO_LARGE",
            HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            ["Use a smaller file", "Check size limits at /formats"],
        ),
        (
            ["not allowed", "blocked"],
            "INVALID_URL",
            HTTP_400_BAD_REQUEST,
            ["Use a public URL", "Avoid private IP addresses"],
        ),
        (
            ["content type mismatch"],
            "INVALID_CONTENT",
            HTTP_400_BAD_REQUEST,
            ["Ensure file matches declared content type"],
        ),
    ]

    for keywords, code, status_code, suggestions in error_mappings:
        if any(keyword in error_msg.lower() for keyword in keywords):
            return code, status_code, suggestions

    # Default ValueError handling
    return (
        "INVALID_INPUT", 
        HTTP_400_BAD_REQUEST, 
        ["Check input format", "Verify JSON structure"]
    )


def map_generic_error(error_msg: str, format_type: str = None) -> Tuple[str, int, Dict[str, Any], list]:
    """Map generic exceptions to HTTP error responses.
    
    Args:
        error_msg: Error message to classify
        format_type: Optional detected format type
        
    Returns:
        Tuple of (error_code, status_code, details, suggestions)
    """
    if "unsupported" in error_msg.lower():
        details = {"detected_format": format_type} if format_type else {}
        return (
            "UNSUPPORTED_FORMAT",
            HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            details,
            ["Check supported formats at /formats"]
        )

    return (
        "CONVERSION_FAILED",
        HTTP_500_INTERNAL_SERVER_ERROR,
        {},
        ["Check input format", "Contact support if issue persists"]
    )


def calculate_source_size(input_type: str, content_data: dict, request_data: dict) -> int:
    """Calculate source content size for different input types.
    
    Args:
        input_type: Type of input (json_url, json_text, etc.)
        content_data: Parsed content data
        request_data: Original request data
        
    Returns:
        Size in bytes
    """
    if input_type == "json_url":
        return len(request_data.get("url", "").encode("utf-8"))
    elif input_type in ["json_text", "json_text_typed"]:
        return len(request_data.get("text", "").encode("utf-8"))
    elif input_type == "json_content":
        try:
            return len(base64.b64decode(request_data.get("content", "")))
        except Exception:
            return 0
    elif content_data and "content" in content_data:
        return len(content_data["content"])
    return 0