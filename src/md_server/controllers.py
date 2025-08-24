from typing import Union
from litestar import Controller, post, Request
from litestar.response import Response
from litestar.exceptions import HTTPException
from litestar.status_codes import (
    HTTP_200_OK,
)
import base64
import time

from .models import (
    ConvertResponse,
    ErrorResponse,
)
from .core.converter import DocumentConverter
from .core.validation import ValidationError
from .core.config import Settings
from .core.detection import ContentTypeDetector


class ConvertController(Controller):
    path = "/convert"

    @post("")
    async def convert_unified(
        self,
        request: Request,
        document_converter: DocumentConverter,
        settings: Settings,
    ) -> Response[Union[ConvertResponse, ErrorResponse]]:
        """Unified conversion endpoint that handles all input types"""
        start_time = time.time()

        try:
            # Parse request to determine input type and data
            input_data = await self._parse_request(request)

            # Use core converter for conversion based on input type
            if input_data.get("url"):
                result = await document_converter.convert_url(
                    input_data["url"], js_rendering=input_data.get("js_rendering")
                )
            elif input_data.get("content"):
                # Decode base64 content if needed
                if isinstance(input_data["content"], str):
                    try:
                        content = base64.b64decode(input_data["content"])
                    except Exception:
                        raise ValueError("Invalid base64 content")
                else:
                    content = input_data["content"]

                result = await document_converter.convert_content(
                    content, filename=input_data.get("filename")
                )
            elif input_data.get("text"):
                # Determine MIME type: if specified use it, otherwise use markdown for backward compatibility
                mime_type = input_data.get("mime_type", "text/markdown")
                result = await document_converter.convert_text(
                    input_data["text"], mime_type
                )
            else:
                raise ValueError("No valid input provided (url, content, or text)")

            # Convert SDK result to API response format
            response = self._create_success_response_from_sdk(result, start_time)
            return Response(response, status_code=HTTP_200_OK)

        except ValidationError as e:
            return self._handle_validation_error(e)
        except ValueError as e:
            error_response = ErrorResponse.create_error(
                code="INVALID_INPUT",
                message=str(e),
                suggestions=["Check input format", "Verify JSON structure"],
            )
            raise HTTPException(status_code=400, detail=error_response.model_dump())
        except Exception as e:
            error_response = ErrorResponse.create_error(
                code="CONVERSION_FAILED",
                message=f"Conversion failed: {str(e)}",
                suggestions=["Check input format", "Contact support if issue persists"],
            )
            raise HTTPException(status_code=500, detail=error_response.model_dump())

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

    def _handle_validation_error(
        self, error: ValidationError
    ) -> Response[ErrorResponse]:
        """Handle validation exceptions"""
        error_response = ErrorResponse.create_error(
            code="VALIDATION_ERROR",
            message=str(error),
            details=getattr(error, "details", {}),
        )
        raise HTTPException(status_code=400, detail=error_response.model_dump())
