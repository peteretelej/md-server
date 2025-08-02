import asyncio
from typing import Union, BinaryIO
from pathlib import Path
from ..core.exceptions import MarkdownConversionError, ConversionTimeoutError

class MarkItDownAdapter:
    def __init__(self, timeout_seconds: int = 30):
        self.timeout_seconds = timeout_seconds
    
    async def convert_file(self, file_path: Union[str, Path]) -> str:
        try:
            return await asyncio.wait_for(
                self._convert_file_sync(file_path),
                timeout=self.timeout_seconds
            )
        except asyncio.TimeoutError:
            raise ConversionTimeoutError(f"Conversion timed out after {self.timeout_seconds}s")
        except Exception as e:
            raise MarkdownConversionError(f"Failed to convert file: {str(e)}")
    
    async def convert_content(self, content: bytes, filename: str = None) -> str:
        try:
            return await asyncio.wait_for(
                self._convert_content_sync(content, filename),
                timeout=self.timeout_seconds
            )
        except asyncio.TimeoutError:
            raise ConversionTimeoutError(f"Conversion timed out after {self.timeout_seconds}s")
        except Exception as e:
            raise MarkdownConversionError(f"Failed to convert content: {str(e)}")
    
    async def _convert_file_sync(self, file_path: Union[str, Path]) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_convert_file, file_path)
    
    async def _convert_content_sync(self, content: bytes, filename: str = None) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_convert_content, content, filename)
    
    def _sync_convert_file(self, file_path: Union[str, Path]) -> str:
        try:
            from markitdown import MarkItDown
            md = MarkItDown()
            result = md.convert(str(file_path))
            return result.text_content
        except ImportError:
            raise MarkdownConversionError("markitdown library not installed")
        except Exception as e:
            raise MarkdownConversionError(f"Conversion failed: {str(e)}")
    
    def _sync_convert_content(self, content: bytes, filename: str = None) -> str:
        try:
            from markitdown import MarkItDown
            import tempfile
            import os
            
            md = MarkItDown()
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}" if filename else "") as tmp_file:
                tmp_file.write(content)
                tmp_file.flush()
                
                try:
                    result = md.convert(tmp_file.name)
                    return result.text_content
                finally:
                    os.unlink(tmp_file.name)
                    
        except ImportError:
            raise MarkdownConversionError("markitdown library not installed")
        except Exception as e:
            raise MarkdownConversionError(f"Conversion failed: {str(e)}")