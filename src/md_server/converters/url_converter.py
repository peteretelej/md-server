from .base_converter import BaseConverter
from ..adapters.markitdown_adapter import MarkItDownAdapter
from urllib.parse import urlparse
import re

class URLConverter(BaseConverter):
    def __init__(self, settings):
        super().__init__(settings)
        self.adapter = MarkItDownAdapter(timeout_seconds=settings.timeout_seconds)
    
    async def convert(self, url: str) -> str:
        # Validate URL before conversion
        validated_url = self._validate_url(url)
        return await self.adapter.convert_url(validated_url)
    
    def _validate_url(self, url: str) -> str:
        """Validate and sanitize URL."""
        if not url:
            raise ValueError("URL cannot be empty")
        
        # Basic URL validation
        if not re.match(r'^https?://', url):
            raise ValueError("URL must start with http:// or https://")
        
        try:
            parsed = urlparse(url)
            if not parsed.netloc:
                raise ValueError("Invalid URL: missing network location")
            return url
        except Exception as e:
            raise ValueError(f"Invalid URL format: {str(e)}")