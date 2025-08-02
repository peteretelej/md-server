import asyncio
from typing import Union, BinaryIO, Optional, List, Tuple
from pathlib import Path
from io import BytesIO
from ..core.exceptions import MarkdownConversionError, ConversionTimeoutError
from ..core.markitdown_config import MarkItDownConfig, get_markitdown_config

class MarkItDownAdapter:
    """Async adapter for the MarkItDown library with advanced configuration support."""
    
    def __init__(
        self, 
        config: Optional[MarkItDownConfig] = None,
        timeout_seconds: Optional[int] = None,
        enable_plugins: Optional[bool] = None,
        enable_builtins: Optional[bool] = None
    ) -> None:
        """Initialize adapter with advanced configuration support.
        
        Args:
            config: MarkItDown configuration object (uses defaults if None)
            timeout_seconds: Override timeout from config (backward compatibility)
            enable_plugins: Override plugin setting from config (backward compatibility)
            enable_builtins: Override builtins setting from config (backward compatibility)
        """
        self.config = config or get_markitdown_config()
        
        # Allow parameter overrides for backward compatibility
        if timeout_seconds is not None:
            self.config.timeout_seconds = timeout_seconds
        if enable_plugins is not None:
            self.config.enable_plugins = enable_plugins
        if enable_builtins is not None:
            self.config.enable_builtins = enable_builtins
        
        self.timeout_seconds = self.config.timeout_seconds
        self._markitdown_instance = None
        self._custom_converters_registered = False
    
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
    
    async def convert_url(self, url: str) -> str:
        """Convert a URL to markdown using MarkItDown's native URL support.
        
        Args:
            url: URL to convert
            
        Returns:
            Converted markdown content
            
        Raises:
            ConversionTimeoutError: If conversion takes longer than timeout
            MarkdownConversionError: If conversion fails
        """
        try:
            return await asyncio.wait_for(
                self._convert_url_sync(url),
                timeout=self.timeout_seconds
            )
        except asyncio.TimeoutError:
            raise ConversionTimeoutError(f"Conversion timed out after {self.timeout_seconds}s")
        except Exception as e:
            raise MarkdownConversionError(f"Failed to convert URL: {str(e)}")
    
    async def _convert_file_sync(self, file_path: Union[str, Path]) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_convert_file, file_path)
    
    async def _convert_stream_sync(self, content: bytes, filename: Optional[str] = None) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_convert_stream, content, filename)
    
    async def _convert_url_sync(self, url: str) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_convert_url, url)
    
    def _get_markitdown_instance(self):
        """Get or create MarkItDown instance with configuration."""
        if self._markitdown_instance is None:
            try:
                from markitdown import MarkItDown
                
                # Create instance with configuration
                kwargs = self.config.to_markitdown_kwargs()
                self._markitdown_instance = MarkItDown(**kwargs)
                
                # Register custom converters
                if not self._custom_converters_registered:
                    self._register_custom_converters()
                    self._custom_converters_registered = True
                    
            except ImportError:
                raise MarkdownConversionError("markitdown library not installed")
        
        return self._markitdown_instance
    
    def _register_custom_converters(self):
        """Register custom converters from configuration."""
        if not self.config.custom_converters:
            return
            
        try:
            custom_converters = self.config.load_custom_converters()
            for converter, priority in custom_converters:
                self._markitdown_instance.register_converter(converter, priority=priority)
        except Exception as e:
            raise MarkdownConversionError(f"Failed to register custom converters: {str(e)}")
    
    def _sync_convert_file(self, file_path: Union[str, Path]) -> str:
        try:
            from markitdown import StreamInfo
            from markitdown._exceptions import (
                UnsupportedFormatException,
                FileConversionException,
                MissingDependencyException
            )
            
            md = self._get_markitdown_instance()
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
            from markitdown import StreamInfo
            from markitdown._exceptions import (
                UnsupportedFormatException,
                FileConversionException,
                MissingDependencyException
            )
            
            md = self._get_markitdown_instance()
            
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
    
    def _sync_convert_url(self, url: str) -> str:
        try:
            from markitdown import StreamInfo
            from markitdown._exceptions import (
                UnsupportedFormatException,
                FileConversionException,
                MissingDependencyException
            )
            from urllib.parse import urlparse
            
            md = self._get_markitdown_instance()
            
            # Create StreamInfo with URL metadata for better format detection
            parsed = urlparse(url)
            filename = parsed.path.split('/')[-1] if parsed.path else "document"
            path = Path(filename) if filename else None
            
            stream_info = StreamInfo(
                url=url,
                extension=path.suffix.lower() if path and path.suffix else None,
                filename=filename if filename else None
            )
            
            # Use MarkItDown's native URL conversion
            result = md.convert(url, stream_info=stream_info)
            return result.markdown
            
        except ImportError:
            raise MarkdownConversionError("markitdown library not installed")
        except UnsupportedFormatException as e:
            raise MarkdownConversionError(f"Unsupported URL format: {str(e)}")
        except MissingDependencyException as e:
            raise MarkdownConversionError(f"Missing required dependency: {str(e)}")
        except FileConversionException as e:
            raise MarkdownConversionError(f"URL conversion failed: {str(e)}")
        except Exception as e:
            raise MarkdownConversionError(f"Unexpected URL conversion error: {str(e)}")
    
    async def health_check(self) -> bool:
        """Perform health check on MarkItDown dependencies and configuration.
        
        Returns:
            True if all dependencies are available and configuration is valid
            
        Raises:
            MarkdownConversionError: If dependencies are missing or configuration is invalid
        """
        try:
            # Test basic MarkItDown import and initialization
            md = self._get_markitdown_instance()
            
            # Test LLM client configuration if present
            if self.config.llm_config:
                llm_client = self.config.get_llm_client()
                if llm_client is None:
                    raise MarkdownConversionError("LLM client configuration invalid")
            
            # Test Azure Document Intelligence configuration if present
            if self.config.azure_docintel_config:
                credential = self.config.get_azure_docintel_credential()
                if credential is None:
                    raise MarkdownConversionError("Azure Document Intelligence configuration invalid")
            
            return True
            
        except Exception as e:
            raise MarkdownConversionError(f"Health check failed: {str(e)}")
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported file formats based on current configuration.
        
        Returns:
            List of supported file extensions
        """
        try:
            md = self._get_markitdown_instance()
            
            # Basic supported formats from built-in converters
            formats = [
                ".txt", ".md", ".html", ".htm", ".csv", ".json", ".xml",
                ".zip", ".epub", ".ipynb", ".jpg", ".jpeg", ".png", ".bmp", ".gif"
            ]
            
            # Add formats based on optional dependencies
            try:
                import pypdf
                formats.extend([".pdf"])
            except ImportError:
                pass
            
            try:
                import docx
                formats.extend([".docx"])
            except ImportError:
                pass
            
            try:
                import openpyxl
                formats.extend([".xlsx"])
            except ImportError:
                pass
            
            try:
                import xlrd
                formats.extend([".xls"])
            except ImportError:
                pass
            
            try:
                import pptx
                formats.extend([".pptx"])
            except ImportError:
                pass
            
            return sorted(list(set(formats)))
            
        except Exception:
            # Return minimal set if detection fails
            return [".txt", ".md", ".html", ".csv", ".json"]
    
    def get_configuration_info(self) -> dict:
        """Get information about current configuration.
        
        Returns:
            Dictionary with configuration details
        """
        return {
            "enable_builtins": self.config.enable_builtins,
            "enable_plugins": self.config.enable_plugins,
            "timeout_seconds": self.config.timeout_seconds,
            "llm_enabled": self.config.llm_config is not None,
            "azure_docintel_enabled": self.config.azure_docintel_config is not None,
            "custom_converters_count": len(self.config.custom_converters),
            "supported_formats": self.get_supported_formats()
        }