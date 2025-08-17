"""
MD Server SDK

Python SDK for document to markdown conversion.
"""

from .local import LocalMDConverter as MDConverter
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
    "MDConverter",  # LocalMDConverter with clean architecture
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
