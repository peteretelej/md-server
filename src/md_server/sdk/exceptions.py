"""
Custom exceptions for the MD Server SDK.
"""


class ConversionError(Exception):
    """Base exception for conversion errors."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class InvalidInputError(ConversionError):
    """Raised when input data is invalid or unsupported."""
    pass


class NetworkError(ConversionError):
    """Raised when network operations fail."""
    pass


class TimeoutError(ConversionError):
    """Raised when conversion exceeds timeout limit."""
    pass


class FileSizeError(ConversionError):
    """Raised when file size exceeds limits."""
    pass


class UnsupportedFormatError(ConversionError):
    """Raised when file format is not supported."""
    pass