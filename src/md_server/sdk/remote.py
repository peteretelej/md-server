"""
Remote converter client for md-server API.
This is a placeholder for Phase 3 implementation.
"""

from typing import Optional, Union
from pathlib import Path

from .models import ConversionResult
from .exceptions import ConversionError


class RemoteMDConverter:
    """Remote converter client for md-server API."""
    
    def __init__(
        self,
        endpoint: str,
        api_key: Optional[str] = None,
        timeout: int = 30
    ):
        self.endpoint = endpoint.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
    
    async def convert_file(self, file_path: Union[str, Path], **options) -> ConversionResult:
        """Convert a file using remote API."""
        raise NotImplementedError("Remote client will be implemented in Phase 3")
    
    async def convert_url(self, url: str, **options) -> ConversionResult:
        """Convert a URL using remote API."""
        raise NotImplementedError("Remote client will be implemented in Phase 3")
    
    async def convert_content(self, content: bytes, filename: Optional[str] = None, **options) -> ConversionResult:
        """Convert content using remote API."""
        raise NotImplementedError("Remote client will be implemented in Phase 3")
    
    async def convert_text(self, text: str, mime_type: str, **options) -> ConversionResult:
        """Convert text using remote API."""
        raise NotImplementedError("Remote client will be implemented in Phase 3")