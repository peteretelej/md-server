import asyncio
from typing import Optional
from pathlib import Path
from io import BytesIO

from markitdown import MarkItDown, StreamInfo


async def convert_content(converter: MarkItDown, content: bytes, filename: Optional[str] = None) -> str:
    """Convert binary content to markdown using MarkItDown"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_convert_content, converter, content, filename)


async def convert_url(converter: MarkItDown, url: str) -> str:
    """Convert URL content to markdown using MarkItDown"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_convert_url, converter, url)


def _sync_convert_content(converter: MarkItDown, content: bytes, filename: Optional[str] = None) -> str:
    """Synchronous content conversion"""
    stream_info = None
    if filename:
        path = Path(filename)
        stream_info = StreamInfo(
            extension=path.suffix.lower(), 
            filename=filename
        )
    
    with BytesIO(content) as stream:
        result = converter.convert_stream(stream, stream_info=stream_info)
        return result.markdown


def _sync_convert_url(converter: MarkItDown, url: str) -> str:
    """Synchronous URL conversion"""
    result = converter.convert(url)
    return result.markdown