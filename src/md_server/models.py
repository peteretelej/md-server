from dataclasses import dataclass


@dataclass
class URLConvertRequest:
    url: str


@dataclass
class MarkdownResponse:
    markdown: str


@dataclass
class ErrorResponse:
    error: str
