from typing import Union
from urllib.parse import quote
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
from .security import SSRFError


def _wants_markdown(accept_header: str, output_format: str = None) -> bool:
    """
    Check if client prefers Markdown over JSON.

    Priority: Accept header > output_format option > default (JSON)
    """
    # Check Accept header first
    if accept_header:
        accept_lower = accept_header.lower()
        if "text/markdown" in accept_lower or "text/x-markdown" in accept_lower:
            return True

    # Check output_format option
    if output_format and output_format.lower() == "markdown":
        return True

    return False


def _create_markdown_headers(
    response: ConvertResponse, conversion_time_ms: int
) -> dict:
    """Create HTTP headers from conversion result metadata."""
    headers = {
        "X-Request-Id": response.request_id,
        "X-Source-Type": response.metadata.source_type,
        "X-Source-Size": str(response.metadata.source_size),
        "X-Markdown-Size": str(response.metadata.markdown_size),
        "X-Conversion-Time-Ms": str(conversion_time_ms),
        "X-Detected-Format": response.metadata.detected_format,
    }

    if response.metadata.estimated_tokens:
        headers["X-Estimated-Tokens"] = str(response.metadata.estimated_tokens)

    if response.metadata.detected_language:
        headers["X-Detected-Language"] = response.metadata.detected_language

    if response.metadata.title:
        headers["X-Title"] = quote(response.metadata.title, safe="")

    return headers


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

            # Extract options that are passed to the converter
            options = {
                "js_rendering": input_data.get("js_rendering"),
                "include_frontmatter": input_data.get("include_frontmatter", False),
            }

            # Use core converter for conversion based on input type
            if input_data.get("url"):
                result = await document_converter.convert_url(
                    input_data["url"], **options
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
                    content, filename=input_data.get("filename"), **options
                )
            elif input_data.get("text"):
                # Determine MIME type: if specified use it, otherwise use markdown for backward compatibility
                mime_type = input_data.get("mime_type", "text/markdown")
                result = await document_converter.convert_text(
                    input_data["text"], mime_type, **options
                )
            else:
                raise ValueError("No valid input provided (url, content, or text)")

            # Convert SDK result to API response format
            conversion_time_ms = int((time.time() - start_time) * 1000)
            response = self._create_success_response_from_sdk(result, start_time)

            # Check for content negotiation (Accept header or output_format option)
            accept_header = request.headers.get("accept", "")
            output_format = input_data.get("output_format")
            if _wants_markdown(accept_header, output_format):
                return Response(
                    content=result.markdown,
                    status_code=HTTP_200_OK,
                    media_type="text/markdown; charset=utf-8",
                    headers=_create_markdown_headers(response, conversion_time_ms),
                )

            return Response(response, status_code=HTTP_200_OK)

        except ValidationError as e:
            return self._handle_validation_error(e)
        except SSRFError as e:
            error_response = ErrorResponse.create_error(
                code="SSRF_BLOCKED",
                message="URL targets a blocked resource",
                details={"reason": e.blocked_reason},
                suggestions=[
                    "Use a publicly accessible URL",
                    "Contact administrator if internal access is required",
                ],
            )
            raise HTTPException(status_code=400, detail=error_response.model_dump())
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
            title=result.metadata.title,
            estimated_tokens=result.metadata.estimated_tokens,
            detected_language=result.metadata.detected_language,
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
