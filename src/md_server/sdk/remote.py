import asyncio
import base64
from pathlib import Path
from typing import Optional, Union, Dict, Any

import httpx

from ..models import ConversionResult, ConversionMetadata


class RemoteMDConverter:
    """Remote converter client for md-server API."""

    def __init__(
        self,
        endpoint: str,
        api_key: Optional[str] = None,
        timeout: int = 30,
    ):
        self.endpoint = endpoint.rstrip("/")
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers=headers,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        await self._client.aclose()

    async def convert_file(
        self, file_path: Union[str, Path], **options
    ) -> ConversionResult:
        """Convert a local file using remote API."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        content = path.read_bytes()
        return await self.convert_content(content, filename=path.name, **options)

    async def convert_url(self, url: str, **options) -> ConversionResult:
        """Convert a URL using remote API."""
        if not url or not url.strip():
            raise ValueError("URL cannot be empty")

        if not url.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")

        data = {"url": url}
        if options:
            data["options"] = options

        response = await self._client.post(f"{self.endpoint}/convert", json=data)
        response.raise_for_status()

        result = response.json()
        return self._parse_response(result)

    async def convert_content(
        self, content: bytes, filename: Optional[str] = None, **options
    ) -> ConversionResult:
        """Convert binary content using remote API."""
        if not content:
            raise ValueError("Content cannot be empty")

        encoded_content = base64.b64encode(content).decode("utf-8")
        data = {"content": encoded_content}

        if filename:
            data["filename"] = filename
        if options:
            data["options"] = options

        response = await self._client.post(f"{self.endpoint}/convert", json=data)
        response.raise_for_status()

        result = response.json()
        return self._parse_response(result)

    async def convert_text(
        self, text: str, mime_type: str = "text/plain", **options
    ) -> ConversionResult:
        """Convert text with MIME type using remote API."""
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        data = {"text": text, "mime_type": mime_type}
        if options:
            data["options"] = options

        response = await self._client.post(f"{self.endpoint}/convert", json=data)
        response.raise_for_status()

        result = response.json()
        return self._parse_response(result)

    def convert_file_sync(
        self, file_path: Union[str, Path], **options
    ) -> ConversionResult:
        """Synchronous version of convert_file."""
        return asyncio.run(self.convert_file(file_path, **options))

    def convert_url_sync(self, url: str, **options) -> ConversionResult:
        """Synchronous version of convert_url."""
        return asyncio.run(self.convert_url(url, **options))

    def convert_content_sync(
        self, content: bytes, filename: Optional[str] = None, **options
    ) -> ConversionResult:
        """Synchronous version of convert_content."""
        return asyncio.run(self.convert_content(content, filename, **options))

    def convert_text_sync(
        self, text: str, mime_type: str = "text/plain", **options
    ) -> ConversionResult:
        """Synchronous version of convert_text."""
        return asyncio.run(self.convert_text(text, mime_type, **options))

    def _parse_response(self, response: Dict[str, Any]) -> ConversionResult:
        """Parse API response to ConversionResult."""
        metadata_data = response.get("metadata", {})
        metadata = ConversionMetadata(
            source_type=metadata_data.get("source_type", "unknown"),
            source_size=metadata_data.get("source_size", 0),
            markdown_size=metadata_data.get("markdown_size", 0),
            conversion_time_ms=metadata_data.get("conversion_time_ms", 0),
            detected_format=metadata_data.get("detected_format", "unknown"),
            warnings=metadata_data.get("warnings", []),
        )

        return ConversionResult(
            success=response.get("success", True),
            markdown=response.get("markdown", ""),
            metadata=metadata,
            request_id=response.get("request_id", ""),
        )
