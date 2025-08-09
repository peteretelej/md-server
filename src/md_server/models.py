from dataclasses import dataclass
from typing import Optional


@dataclass
class URLConvertRequest:
    url: str
    js_rendering: Optional[bool] = None


@dataclass
class MarkdownResponse:
    markdown: str


@dataclass
class ErrorResponse:
    error: str
