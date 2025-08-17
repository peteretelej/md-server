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
    HTTP_413_REQUEST_ENTITY_TOO_LARGE,
)
import base64
import time

from .models import (
    ConvertResponse,
    ErrorResponse,
)
from .sdk import MDConverter
from .sdk.exceptions import (
    ConversionError,
    InvalidInputError,
    NetworkError,
    TimeoutError,
    FileSizeError,
    UnsupportedFormatError,
)
from .core.config import Settings
from .detection import ContentTypeDetector


class ConvertController(Controller):
    path = "/convert"

    @post("")
    async def convert_unified(
        self,
        request: Request,
        md_converter: MDConverter,
        settings: Settings,
    ) -> Response[Union[ConvertResponse, ErrorResponse]]:
        """Unified conversion endpoint that handles all input types"""
        start_time = time.time()

        try:
            # Parse request to determine input type and data
            input_data = await self._parse_request(request)

            # Use SDK for conversion based on input type
            if input_data.get("url"):
                result = await md_converter.convert_url(
                    input_data["url"], js_rendering=input_data.get("js_rendering")
                )
            elif input_data.get("content"):
                # Decode base64 content if needed
                if isinstance(input_data["content"], str):
                    try:
                        content = base64.b64decode(input_data["content"])
                    except Exception:
                        raise InvalidInputError("Invalid base64 content")
                else:
                    content = input_data["content"]

                result = await md_converter.convert_content(
                    content, filename=input_data.get("filename")
                )
            elif input_data.get("text"):
                # Determine MIME type: if specified use it, otherwise use markdown for backward compatibility
                mime_type = input_data.get("mime_type", "text/markdown")
                result = await md_converter.convert_text(input_data["text"], mime_type)
            else:
                raise InvalidInputError(
                    "No valid input provided (url, content, or text)"
                )

            # Convert SDK result to API response format
            response = self._create_success_response_from_sdk(result, start_time)
            return Response(response, status_code=HTTP_200_OK)

        except (
            InvalidInputError,
            NetworkError,
            TimeoutError,
            FileSizeError,
            UnsupportedFormatError,
            ConversionError,
        ) as e:
            return self._handle_sdk_error(e)
        except ValueError as e:
            self._handle_value_error(str(e))
        except Exception as e:
            self._handle_generic_error(str(e))

    async def _parse_request(self, request: Request) -> dict:
        """Parse request to extract conversion input data"""
        content_type = request.headers.get("content-type", "")

        # JSON request
        if "application/json" in content_type:
            try:
                json_data = await request.json()

                # Extract options if present
                options = json_data.get("options", {})

                # Add options to the data for SDK consumption
                result = json_data.copy()
                if options:
                    result.update(options)

                return result
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

                return {"content": content, "filename": file.filename}

            except ValueError:
                raise
            except Exception as e:
                raise ValueError(f"Failed to process multipart upload: {str(e)}")

        # Binary upload
        else:
            try:
                content = await request.body()
                return {"content": content}

            except Exception:
                raise ValueError("Failed to read request body")

    def _create_success_response_from_sdk(
        self, result, start_time: float
    ) -> ConvertResponse:
        """Create a successful conversion response from SDK result"""
        # Calculate total time (including SDK processing time)
        total_time_ms = int((time.time() - start_time) * 1000)

        # Use original API source type mapping for backward compatibility
        # For URL inputs, use "url" as source_type regardless of detected format
        if result.metadata.source_type == "url":
            source_type = "url"
        else:
            source_type = ContentTypeDetector.get_source_type(
                result.metadata.detected_format
            )

        return ConvertResponse.create_success(
            markdown=result.markdown,
            source_type=source_type,
            source_size=result.metadata.source_size,
            conversion_time_ms=total_time_ms,
            detected_format=result.metadata.detected_format,
            warnings=[],
        )

    def _handle_sdk_error(self, error) -> Response[ErrorResponse]:
        """Handle SDK exceptions and map to HTTP responses"""
        if isinstance(error, InvalidInputError):
            error_response = ErrorResponse.create_error(
                code="INVALID_INPUT",
                message=str(error),
                details=error.details,
                suggestions=["Check input format", "Verify request structure"],
            )
            status_code = HTTP_400_BAD_REQUEST

        elif isinstance(error, FileSizeError):
            error_response = ErrorResponse.create_error(
                code="FILE_TOO_LARGE",
                message=str(error),
                details=error.details,
                suggestions=["Use a smaller file", "Check size limits at /formats"],
            )
            status_code = HTTP_413_REQUEST_ENTITY_TOO_LARGE

        elif isinstance(error, UnsupportedFormatError):
            error_response = ErrorResponse.create_error(
                code="UNSUPPORTED_FORMAT",
                message=str(error),
                details=error.details,
                suggestions=["Check supported formats at /formats"],
            )
            status_code = HTTP_415_UNSUPPORTED_MEDIA_TYPE

        elif isinstance(error, TimeoutError):
            error_response = ErrorResponse.create_error(
                code="TIMEOUT",
                message=str(error),
                details=error.details,
                suggestions=["Try with a smaller file", "Increase timeout in options"],
            )
            status_code = HTTP_408_REQUEST_TIMEOUT

        elif isinstance(error, NetworkError):
            error_response = ErrorResponse.create_error(
                code="NETWORK_ERROR",
                message=str(error),
                details=error.details,
                suggestions=["Check URL accessibility", "Verify network connectivity"],
            )
            status_code = HTTP_400_BAD_REQUEST

        else:  # ConversionError or generic
            error_response = ErrorResponse.create_error(
                code="CONVERSION_FAILED",
                message=str(error),
                details=getattr(error, "details", {}),
                suggestions=["Check input format", "Contact support if issue persists"],
            )
            status_code = HTTP_500_INTERNAL_SERVER_ERROR

        raise HTTPException(status_code=status_code, detail=error_response.model_dump())

    def _handle_value_error(self, error_msg: str) -> None:
        """Handle ValueError with specific error type detection"""
        error_mappings = [
            (
                ["size", "exceeds"],
                "FILE_TOO_LARGE",
                HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                ["Use a smaller file", "Check size limits at /formats"],
            ),
            (
                ["not allowed", "blocked"],
                "INVALID_URL",
                HTTP_400_BAD_REQUEST,
                ["Use a public URL", "Avoid private IP addresses"],
            ),
            (
                ["content type mismatch"],
                "INVALID_CONTENT",
                HTTP_400_BAD_REQUEST,
                ["Ensure file matches declared content type"],
            ),
        ]

        for keywords, code, status_code, suggestions in error_mappings:
            if any(keyword in error_msg.lower() for keyword in keywords):
                error_response = ErrorResponse.create_error(
                    code=code, message=error_msg, suggestions=suggestions
                )
                raise HTTPException(
                    status_code=status_code, detail=error_response.model_dump()
                )

        # Default ValueError handling
        error_response = ErrorResponse.create_error(
            code="INVALID_INPUT",
            message=error_msg,
            suggestions=["Check input format", "Verify JSON structure"],
        )
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail=error_response.model_dump()
        )

    def _handle_generic_error(self, error_msg: str, format_type: str = None) -> None:
        """Handle generic exceptions"""
        if "unsupported" in error_msg.lower():
            error_response = ErrorResponse.create_error(
                code="UNSUPPORTED_FORMAT",
                message=error_msg,
                details={"detected_format": format_type} if format_type else None,
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

    def _calculate_source_size(
        self, input_type: str, content_data: dict, request_data: dict
    ) -> int:
        """Calculate source content size (backward compatibility method)"""
        if input_type == "json_url":
            return len(request_data.get("url", "").encode("utf-8"))
        elif input_type in ["json_text", "json_text_typed"]:
            return len(request_data.get("text", "").encode("utf-8"))
        elif input_type == "json_content":
            try:
                return len(base64.b64decode(request_data.get("content", "")))
            except Exception:
                return 0
        elif content_data and "content" in content_data:
            return len(content_data["content"])
        return 0
