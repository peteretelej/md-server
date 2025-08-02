import asyncio
from typing import Union, BinaryIO, Optional
from pathlib import Path
from io import BytesIO
from ..core.exceptions import MarkdownConversionError, ConversionTimeoutError

class MarkItDownAdapter:
    """Async adapter for the MarkItDown library with stream-based conversion, timeout and error handling."""
    
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
        """Convert binary content to markdown using stream-based conversion.
        
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
                self._convert_stream_sync(content, filename),
                timeout=self.timeout_seconds
            )
        except asyncio.TimeoutError:
            raise ConversionTimeoutError(f"Conversion timed out after {self.timeout_seconds}s")
        except Exception as e:
            raise MarkdownConversionError(f"Failed to convert content: {str(e)}")
    
    async def convert_stream(self, stream: BinaryIO, filename: Optional[str] = None) -> str:
        """Convert binary stream to markdown.
        
        Args:
            stream: Binary stream to convert
            filename: Optional filename for format detection hints
            
        Returns:
            Converted markdown content
            
        Raises:
            ConversionTimeoutError: If conversion takes longer than timeout
            MarkdownConversionError: If conversion fails
        """
        try:
            content = stream.read()
            stream.seek(0)  # Reset stream position
            return await asyncio.wait_for(
                self._convert_stream_sync(content, filename),
                timeout=self.timeout_seconds
            )
        except asyncio.TimeoutError:
            raise ConversionTimeoutError(f"Conversion timed out after {self.timeout_seconds}s")
        except Exception as e:
            raise MarkdownConversionError(f"Failed to convert stream: {str(e)}")
    
    async def _convert_file_sync(self, file_path: Union[str, Path]) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_convert_file, file_path)
    
    async def _convert_stream_sync(self, content: bytes, filename: Optional[str] = None) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_convert_stream, content, filename)
    
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
    
    def _sync_convert_stream(self, content: bytes, filename: Optional[str] = None) -> str:
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
            
            # Create StreamInfo with format detection hints
            stream_info = None
            if filename:
                path = Path(filename)
                stream_info = StreamInfo(
                    extension=path.suffix.lower(),
                    filename=filename
                )
            
            # Use BytesIO for direct stream conversion without temporary files
            with BytesIO(content) as stream:
                result = md.convert_stream(stream, stream_info=stream_info)
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