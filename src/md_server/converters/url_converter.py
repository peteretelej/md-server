import httpx
from .base_converter import BaseConverter
from ..adapters.markitdown_adapter import MarkItDownAdapter
from ..core.exceptions import URLFetchError

class URLConverter(BaseConverter):
    def __init__(self, settings):
        super().__init__(settings)
        self.adapter = MarkItDownAdapter(timeout_seconds=settings.timeout_seconds)
    
    async def convert(self, url: str) -> str:
        content = await self._fetch_url_content(url)
        return await self.adapter.convert_content(content, filename=self._get_filename_from_url(url))
    
    async def _fetch_url_content(self, url: str) -> bytes:
        try:
            async with httpx.AsyncClient(timeout=self.settings.timeout_seconds) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.content
        except httpx.HTTPError as e:
            raise URLFetchError(f"Failed to fetch URL: {str(e)}")
        except Exception as e:
            raise URLFetchError(f"Unexpected error fetching URL: {str(e)}")
    
    def _get_filename_from_url(self, url: str) -> str:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.path.split('/')[-1] if parsed.path else "document"