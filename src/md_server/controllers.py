from dataclasses import dataclass
from typing import Annotated, Dict
from litestar import Controller, post
from litestar.datastructures import UploadFile
from litestar.response import Response
from litestar.exceptions import HTTPException
from litestar.status_codes import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_413_REQUEST_ENTITY_TOO_LARGE, HTTP_415_UNSUPPORTED_MEDIA_TYPE, HTTP_408_REQUEST_TIMEOUT, HTTP_500_INTERNAL_SERVER_ERROR
from litestar.enums import RequestEncodingType
from litestar.params import Body

from .models import URLConvertRequest, MarkdownResponse
from .adapters.markitdown_adapter import MarkItDownAdapter
from .core.config import get_settings
from .core.exceptions import (
    UnsupportedFileTypeError,
    FileTooLargeError,
    URLFetchError,
    ConversionTimeoutError,
)


class ConvertController(Controller):
    path = "/convert"

    @post("")
    async def convert_file(
        self, 
        data: Annotated[Dict[str, UploadFile], Body(media_type=RequestEncodingType.MULTI_PART)]
    ) -> Response[MarkdownResponse]:
        """Convert uploaded file to markdown"""
        settings = get_settings()
        adapter = MarkItDownAdapter(timeout_seconds=settings.timeout_seconds)
        
        # Get the file from the dictionary (expecting 'file' key)
        if 'file' not in data:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="File parameter 'file' is required"
            )
        
        file = data['file']
        
        try:
            # Read file content first
            content = await file.read()
            
            # Validate file size
            if len(content) > settings.max_file_size:
                raise HTTPException(
                    status_code=HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File size {len(content)} exceeds limit {settings.max_file_size}"
                )
            
            # Convert using adapter
            markdown = await adapter.convert_content(content, file.filename)
            
            return Response(
                MarkdownResponse(markdown=markdown),
                status_code=HTTP_200_OK
            )
            
        except UnsupportedFileTypeError as e:
            raise HTTPException(status_code=HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(e))
        except FileTooLargeError as e:
            raise HTTPException(status_code=HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(e))
        except ConversionTimeoutError as e:
            raise HTTPException(status_code=HTTP_408_REQUEST_TIMEOUT, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Conversion failed: {str(e)}")

    @post("/url")
    async def convert_url(self, data: URLConvertRequest) -> Response[MarkdownResponse]:
        """Convert URL content to markdown"""
        settings = get_settings()
        adapter = MarkItDownAdapter(timeout_seconds=settings.timeout_seconds)
        
        try:
            # Convert using adapter
            markdown = await adapter.convert_url(data.url)
            
            return Response(
                MarkdownResponse(markdown=markdown),
                status_code=HTTP_200_OK
            )
            
        except URLFetchError as e:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
        except ConversionTimeoutError as e:
            raise HTTPException(status_code=HTTP_408_REQUEST_TIMEOUT, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Conversion failed: {str(e)}")