from typing import Union
from litestar import Controller, post, Request
from litestar.response import Response
from litestar.exceptions import HTTPException
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    HTTP_408_REQUEST_TIMEOUT,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from markitdown import MarkItDown
import asyncio
import base64
import time

from .models import (
    URLConvertRequest,
    MarkdownResponse,
    ConvertResponse,
    ErrorResponse,
    ConversionOptions,
)
from .converter import convert_content, UrlConverter
from .core.config import Settings
from .detection import ContentTypeDetector
from .security import FileSizeValidator, ContentValidator


class ConvertController(Controller):
    path = "/convert"

    @post("")
    async def convert_unified(
        self,
        request: Request,
        converter: MarkItDown,
        url_converter: UrlConverter,
        settings: Settings,
    ) -> Response[Union[ConvertResponse, ErrorResponse]]:
        """Unified conversion endpoint that handles all input types"""
        start_time = time.time()

        try:
            (
                input_type,
                format_type,
                content_data,
                request_data,
            ) = await self._detect_input_type(request)

            # Create conversion options from request
            options = ConversionOptions()
            if request_data and "options" in request_data:
                options = ConversionOptions(**request_data["options"])

            # Apply appropriate timeout based on operation type
            if input_type == "json_url":
                # URL operations use URL fetch timeout (typically shorter)
                timeout = options.timeout or settings.url_fetch_timeout
                url = request_data.get("url")
                js_rendering = options.js_rendering
                markdown = await asyncio.wait_for(
                    url_converter.convert_url(url, js_rendering),
                    timeout=timeout,
                )
            else:
                # File conversions use conversion timeout (typically longer)
                timeout = options.timeout or settings.conversion_timeout
                markdown = await asyncio.wait_for(
                    self._convert_by_input_type(
                        input_type,
                        content_data,
                        converter,
                        url_converter,
                        options,
                        request_data,
                    ),
                    timeout=timeout,
                )

            # Calculate metrics
            conversion_time_ms = int((time.time() - start_time) * 1000)
            source_size = self._calculate_source_size(
                input_type, content_data, request_data
            )
            source_type = ContentTypeDetector.get_source_type(format_type)

            # Create successful response
            response = ConvertResponse.create_success(
                markdown=markdown,
                source_type=source_type,
                source_size=source_size,
                conversion_time_ms=conversion_time_ms,
                detected_format=format_type,
                warnings=[],
            )

            return Response(response, status_code=HTTP_200_OK)

        except asyncio.TimeoutError:
            error_response = ErrorResponse.create_error(
                code="TIMEOUT",
                message=f"Conversion timed out after {timeout}s",
                suggestions=["Try with a smaller file", "Increase timeout in options"],
            )
            raise HTTPException(
                status_code=HTTP_408_REQUEST_TIMEOUT, detail=error_response.model_dump()
            )

        except ValueError as e:
            error_msg = str(e)
            
            # Handle specific security-related errors
            if "size" in error_msg.lower() and "exceeds" in error_msg.lower():
                error_response = ErrorResponse.create_error(
                    code="FILE_TOO_LARGE",
                    message=error_msg,
                    suggestions=["Use a smaller file", "Check size limits at /formats"],
                )
                raise HTTPException(
                    status_code=413, detail=error_response.model_dump()  # 413 Payload Too Large
                )
            elif "not allowed" in error_msg.lower() or "blocked" in error_msg.lower():
                error_response = ErrorResponse.create_error(
                    code="INVALID_URL",
                    message=error_msg,
                    suggestions=["Use a public URL", "Avoid private IP addresses"],
                )
                raise HTTPException(
                    status_code=HTTP_400_BAD_REQUEST, detail=error_response.model_dump()
                )
            elif "content type mismatch" in error_msg.lower():
                error_response = ErrorResponse.create_error(
                    code="INVALID_CONTENT",
                    message=error_msg,
                    suggestions=["Ensure file matches declared content type"],
                )
                raise HTTPException(
                    status_code=HTTP_400_BAD_REQUEST, detail=error_response.model_dump()
                )
            else:
                error_response = ErrorResponse.create_error(
                    code="INVALID_INPUT",
                    message=error_msg,
                    suggestions=["Check input format", "Verify JSON structure"],
                )
                raise HTTPException(
                    status_code=HTTP_400_BAD_REQUEST, detail=error_response.model_dump()
                )

        except Exception as e:
            error_msg = str(e)
            if "unsupported" in error_msg.lower():
                error_response = ErrorResponse.create_error(
                    code="UNSUPPORTED_FORMAT",
                    message=error_msg,
                    details={"detected_format": format_type},
                    suggestions=["Check supported formats at /formats"],
                )
                raise HTTPException(
                    status_code=HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail=error_response.model_dump(),
                )

            error_response = ErrorResponse.create_error(
                code="CONVERSION_FAILED", message=f"Conversion failed: {error_msg}"
            )
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_response.model_dump(),
            )

    async def _detect_input_type(self, request: Request) -> tuple:
        """Detect input type from request"""
        content_type = request.headers.get("content-type", "")

        # JSON request
        if "application/json" in content_type:
            try:
                json_data = await request.json()
                input_type, format_type = ContentTypeDetector.detect_input_type(
                    request_data=json_data
                )
                return input_type, format_type, None, json_data
            except Exception:
                raise ValueError("Invalid JSON in request body")

        # Multipart form request
        elif "multipart/form-data" in content_type:
            try:
                form_data = await request.form()
                if "file" not in form_data:
                    raise ValueError(
                        "File parameter 'file' is required for multipart uploads"
                    )

                file = form_data["file"]
                content = await file.read()
                
                # Validate content type matches detected type
                validated_type = ContentValidator.validate_content_type(
                    content, file.content_type
                )
                
                # Validate file size
                FileSizeValidator.validate_size(len(content), validated_type)
                
                input_type, format_type = ContentTypeDetector.detect_input_type(
                    content_type=validated_type,
                    filename=file.filename,
                    content=content,
                )
                return (
                    input_type,
                    format_type,
                    {"content": content, "filename": file.filename},
                    None,
                )

            except ValueError:
                # Re-raise ValueError for proper error handling
                raise
            except Exception as e:
                raise ValueError(f"Failed to process multipart upload: {str(e)}")

        # Binary upload
        else:
            try:
                content = await request.body()
                
                # Validate content type matches detected type
                validated_type = ContentValidator.validate_content_type(
                    content, content_type or None
                )
                
                # Validate file size
                FileSizeValidator.validate_size(len(content), validated_type)
                
                input_type, format_type = ContentTypeDetector.detect_input_type(
                    content_type=validated_type, content=content
                )
                return input_type, format_type, {"content": content}, None

            except ValueError:
                # Re-raise ValueError for proper error handling
                raise
            except Exception:
                raise ValueError("Failed to read request body")

    async def _convert_by_input_type(
        self,
        input_type: str,
        content_data: dict,
        converter: MarkItDown,
        url_converter: UrlConverter,
        options: ConversionOptions,
        request_data: dict = None,
    ) -> str:
        """Convert content based on detected input type"""

        if input_type in ["json_content", "binary", "multipart"]:
            if input_type == "json_content":
                # Decode base64 content
                try:
                    content = base64.b64decode(request_data["content"])
                except Exception:
                    raise ValueError("Invalid base64 content")
                
                filename = request_data.get("filename")
                
                # Validate content type and size for base64 content
                detected_type = ContentValidator.detect_content_type(content)
                FileSizeValidator.validate_size(len(content), detected_type)
            else:
                content = content_data["content"]
                filename = content_data.get("filename")

            return await convert_content(converter, content, filename)

        elif input_type == "json_text":
            # Return text as-is or apply cleaning if requested
            text = request_data["text"]
            if options.clean_markdown:
                # Apply basic markdown cleaning
                return text.strip()
            return text

        else:
            raise ValueError(f"Unsupported input type: {input_type}")

    def _calculate_source_size(
        self, input_type: str, content_data: dict, request_data: dict
    ) -> int:
        """Calculate source content size"""
        if input_type == "json_url":
            return len(request_data.get("url", "").encode("utf-8"))
        elif input_type == "json_text":
            return len(request_data.get("text", "").encode("utf-8"))
        elif input_type == "json_content":
            return len(base64.b64decode(request_data.get("content", "")))
        elif content_data and "content" in content_data:
            return len(content_data["content"])
        return 0

    # Legacy endpoints for backward compatibility
    @post("/url")
    async def convert_url_endpoint(
        self,
        data: URLConvertRequest,
        url_converter: UrlConverter,
        settings: Settings,
    ) -> Response[MarkdownResponse]:
        """Legacy URL conversion endpoint"""
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
