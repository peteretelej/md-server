from pydantic import BaseModel, HttpUrl

class URLConvertRequest(BaseModel):
    url: HttpUrl

class MarkdownResponse(BaseModel):
    markdown: str

class ErrorResponse(BaseModel):
    error: str