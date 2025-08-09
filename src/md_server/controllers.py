from typing import Annotated, Dict
from litestar import Controller, post
from litestar.datastructures import UploadFile
from litestar.response import Response
from litestar.exceptions import HTTPException
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_413_REQUEST_ENTITY_TOO_LARGE,
    HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    HTTP_408_REQUEST_TIMEOUT,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from litestar.enums import RequestEncodingType
from litestar.params import Body
from markitdown import MarkItDown
import asyncio

from .models import URLConvertRequest, MarkdownResponse
from .converter import convert_content, UrlConverter
from .core.config import Settings


class ConvertController(Controller):
    path = "/convert"

    @post("")
    async def convert_file(
        self,
        data: Annotated[
            Dict[str, UploadFile], Body(media_type=RequestEncodingType.MULTI_PART)
        ],
        converter: MarkItDown,
        settings: Settings,
    ) -> Response[MarkdownResponse]:
        """Convert uploaded file to markdown"""
        if "file" not in data:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="File parameter 'file' is required",
            )

        file = data["file"]

        try:
            content = await file.read()

            if len(content) > settings.max_file_size:
                raise HTTPException(
                    status_code=HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File size {len(content)} exceeds limit {settings.max_file_size}",
                )

            markdown = await asyncio.wait_for(
                convert_content(converter, content, file.filename),
                timeout=settings.timeout_seconds,
            )

            return Response(
                MarkdownResponse(markdown=markdown), status_code=HTTP_200_OK
            )

        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=HTTP_408_REQUEST_TIMEOUT,
                detail=f"Conversion timed out after {settings.timeout_seconds}s",
            )
        except Exception as e:
            error_msg = str(e)
            if "unsupported" in error_msg.lower():
                raise HTTPException(
                    status_code=HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=error_msg
                )
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Conversion failed: {error_msg}",
            )

    @post("/url")
    async def convert_url_endpoint(
        self,
        data: URLConvertRequest,
        url_converter: UrlConverter,
        settings: Settings,
    ) -> Response[MarkdownResponse]:
        """Convert URL content to markdown"""
        try:
            markdown = await asyncio.wait_for(
                url_converter.convert_url(data.url, data.js_rendering),
                timeout=settings.timeout_seconds,
            )

            return Response(
                MarkdownResponse(markdown=markdown), status_code=HTTP_200_OK
            )

        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=HTTP_408_REQUEST_TIMEOUT,
                detail=f"URL conversion timed out after {settings.timeout_seconds}s",
            )
        except ValueError as e:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Conversion failed: {str(e)}",
            )
