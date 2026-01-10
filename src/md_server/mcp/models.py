"""MCP response models for structured tool responses."""

from pydantic import BaseModel, Field
from typing import Optional


class MCPMetadata(BaseModel):
    """Metadata extracted from content."""

    author: Optional[str] = None
    description: Optional[str] = None
    published: Optional[str] = None
    language: Optional[str] = None
    pages: Optional[int] = None
    format: Optional[str] = None
    ocr_applied: Optional[bool] = None


class MCPSuccessResponse(BaseModel):
    """Successful tool response."""

    success: bool = Field(default=True)
    title: str
    content: str
    source: str
    word_count: int
    metadata: MCPMetadata = Field(default_factory=MCPMetadata)


class MCPErrorDetails(BaseModel):
    """Optional technical error details."""

    status_code: Optional[int] = None
    content_type: Optional[str] = None


class MCPError(BaseModel):
    """Structured error information."""

    code: str
    message: str
    suggestions: list[str] = Field(default_factory=list)
    details: Optional[MCPErrorDetails] = None


class MCPErrorResponse(BaseModel):
    """Error tool response."""

    success: bool = Field(default=False)
    error: MCPError
