"""
Data models for conversion results and metadata.
"""

from dataclasses import dataclass, field
from typing import List, Optional
import uuid


@dataclass
class ConversionMetadata:
    """Metadata about the conversion process."""
    
    source_type: str
    source_size: int
    markdown_size: int
    processing_time: float
    detected_format: str
    warnings: List[str] = field(default_factory=list)
    
    
@dataclass
class ConversionResult:
    """Result of a document conversion operation."""
    
    markdown: str
    metadata: ConversionMetadata
    success: bool = True
    request_id: str = field(default_factory=lambda: f"req_{uuid.uuid4()}")


@dataclass
class ConversionOptions:
    """Options for document conversion."""
    
    ocr_enabled: bool = False
    js_rendering: bool = False
    extract_images: bool = False
    preserve_formatting: bool = True
    clean_markdown: bool = False
    timeout: int = 30
    max_file_size_mb: int = 50