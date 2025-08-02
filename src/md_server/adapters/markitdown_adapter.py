import asyncio
from typing import Union, BinaryIO, Optional
from pathlib import Path
from ..core.exceptions import MarkdownConversionError, ConversionTimeoutError

class MarkItDownAdapter:
    """Async adapter for the MarkItDown library with timeout and error handling."""
    
    def __init__(
        self, 
        timeout_seconds: int = 30,
        enable_plugins: bool = False,
        enable_builtins: bool = True
    ) -> None:
        """Initialize adapter with conversion timeout and options.
        
        Args:
            timeout_seconds: Maximum time to wait for conversion (default: 30)
            enable_plugins: Enable 3rd-party plugins (default: False)
            enable_builtins: Enable built-in converters (default: True)
        """
        self.timeout_seconds = timeout_seconds
        self.enable_plugins = enable_plugins
        self.enable_builtins = enable_builtins
    
    async def convert_file(self, file_path: Union[str, Path]) -> str:
        """Convert a local file to markdown.
        
        Args:
            file_path: Path to the file to convert
            
        Returns:
            Converted markdown content
            
        Raises:
            ConversionTimeoutError: If conversion takes longer than timeout
            MarkdownConversionError: If conversion fails
        """
        try:
            return await asyncio.wait_for(
                self._convert_file_sync(file_path),
                timeout=self.timeout_seconds
            )
        except asyncio.TimeoutError:
            raise ConversionTimeoutError(f"Conversion timed out after {self.timeout_seconds}s")
        except Exception as e:
            raise MarkdownConversionError(f"Failed to convert file: {str(e)}")
    
    async def convert_content(self, content: bytes, filename: Optional[str] = None) -> str:
        """Convert binary content to markdown.
        
        Args:
            content: Binary content to convert
            filename: Optional filename for format detection hints
            
        Returns:
            Converted markdown content
            
        Raises:
            ConversionTimeoutError: If conversion takes longer than timeout
            MarkdownConversionError: If conversion fails
        """
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
    
    async def _convert_content_sync(self, content: bytes, filename: Optional[str] = None) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_convert_content, content, filename)
    
    def _sync_convert_file(self, file_path: Union[str, Path]) -> str:
        try:
            from markitdown import MarkItDown, StreamInfo
            from markitdown._exceptions import (
                UnsupportedFormatException,
                FileConversionException,
                MissingDependencyException
            )
            
            md = MarkItDown(
                enable_builtins=self.enable_builtins,
                enable_plugins=self.enable_plugins
            )
            path = Path(file_path)
            
            stream_info = StreamInfo(
                extension=path.suffix.lower(),
                filename=path.name,
                local_path=str(path.absolute())
            )
            
            result = md.convert(str(file_path), stream_info=stream_info)
            return result.markdown
        except ImportError:
            raise MarkdownConversionError("markitdown library not installed")
        except UnsupportedFormatException as e:
            raise MarkdownConversionError(f"Unsupported file format: {str(e)}")
        except MissingDependencyException as e:
            raise MarkdownConversionError(f"Missing required dependency: {str(e)}")
        except FileConversionException as e:
            raise MarkdownConversionError(f"File conversion failed: {str(e)}")
        except Exception as e:
            raise MarkdownConversionError(f"Unexpected conversion error: {str(e)}")
    
    def _sync_convert_content(self, content: bytes, filename: Optional[str] = None) -> str:
        try:
            from markitdown import MarkItDown, StreamInfo
            from markitdown._exceptions import (
                UnsupportedFormatException,
                FileConversionException,
                MissingDependencyException
            )
            import tempfile
            import os
            
            md = MarkItDown(
                enable_builtins=self.enable_builtins,
                enable_plugins=self.enable_plugins
            )
            
            # Create StreamInfo with hints
            stream_info = None
            if filename:
                path = Path(filename)
                stream_info = StreamInfo(
                    extension=path.suffix.lower(),
                    filename=filename
                )
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}" if filename else "") as tmp_file:
                tmp_file.write(content)
                tmp_file.flush()
                
                try:
                    result = md.convert(tmp_file.name, stream_info=stream_info)
                    return result.markdown
                finally:
                    os.unlink(tmp_file.name)
                    
        except ImportError:
            raise MarkdownConversionError("markitdown library not installed")
        except UnsupportedFormatException as e:
            raise MarkdownConversionError(f"Unsupported file format: {str(e)}")
        except MissingDependencyException as e:
            raise MarkdownConversionError(f"Missing required dependency: {str(e)}")
        except FileConversionException as e:
            raise MarkdownConversionError(f"File conversion failed: {str(e)}")
        except Exception as e:
            raise MarkdownConversionError(f"Unexpected conversion error: {str(e)}")