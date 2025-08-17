"""
MD Server SDK

Python SDK for document to markdown conversion.
"""

from .converter import MDConverter
from .remote import RemoteMDConverter
from .models import ConversionResult, ConversionMetadata
from .exceptions import (
    ConversionError,
    InvalidInputError,
    NetworkError,
    TimeoutError,
    FileSizeError,
    UnsupportedFormatError,
)

__version__ = "1.0.0"

__all__ = [
    "MDConverter",
    "RemoteMDConverter",
    "ConversionResult",
    "ConversionMetadata",
    "ConversionError",
    "InvalidInputError",
    "NetworkError",
    "TimeoutError",
    "FileSizeError",
    "UnsupportedFormatError",
]
