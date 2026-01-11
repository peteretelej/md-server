"""Tests for MCP tool handlers."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from md_server.mcp.handlers import handle_read_url, handle_read_file
from md_server.mcp.models import MCPSuccessResponse, MCPErrorResponse
from md_server.mcp.errors import ErrorCode
from md_server.core.errors import (
    NotFoundError,
    AccessDeniedError,
    ServerError,
    URLTimeoutError,
    URLConnectionError,
    HTTPFetchError,
    ConversionError,
    ErrorCode as CoreErrorCode,
)


@pytest.fixture
def mock_converter():
    """Create a mock DocumentConverter."""
    converter = MagicMock()
    converter.timeout = 60
    converter.max_file_size_mb = 50
    return converter


@pytest.fixture
def mock_conversion_result():
    """Create a mock ConversionResult."""
    result = MagicMock()
    result.markdown = "# Title\n\nThis is some content with more than five words."
    result.metadata = MagicMock()
    result.metadata.title = "Test Title"
    result.metadata.detected_language = "en"
    return result


@pytest.mark.unit
class TestHandleReadUrl:
    """Tests for handle_read_url handler."""

    @pytest.mark.asyncio
    async def test_success_default_markdown(
        self, mock_converter, mock_conversion_result
    ):
        """Should return raw markdown by default."""
        mock_converter.convert_url = AsyncMock(return_value=mock_conversion_result)

        result = await handle_read_url(
            mock_converter, "https://example.com", render_js=False
        )

        assert isinstance(result, str)
        assert "# Title" in result

    @pytest.mark.asyncio
    async def test_success_explicit_markdown(
        self, mock_converter, mock_conversion_result
    ):
        """Should return raw markdown when output_format=markdown."""
        mock_converter.convert_url = AsyncMock(return_value=mock_conversion_result)

        result = await handle_read_url(
            mock_converter,
            "https://example.com",
            render_js=False,
            output_format="markdown",
        )

        assert isinstance(result, str)
        assert "# Title" in result

    @pytest.mark.asyncio
    async def test_success_json_format(self, mock_converter, mock_conversion_result):
        """Should return MCPSuccessResponse when output_format=json."""
        mock_converter.convert_url = AsyncMock(return_value=mock_conversion_result)

        result = await handle_read_url(
            mock_converter,
            "https://example.com",
            render_js=False,
            output_format="json",
        )

        assert isinstance(result, MCPSuccessResponse)
        assert result.success is True
        assert result.title == "Test Title"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "output_format,expected_type",
        [
            ("markdown", str),
            ("json", MCPSuccessResponse),
            (None, str),  # default should be markdown (handled by default param)
        ],
        ids=["markdown", "json", "default"],
    )
    async def test_output_format_types(
        self, mock_converter, mock_conversion_result, output_format, expected_type
    ):
        """Should return correct type based on output_format."""
        mock_converter.convert_url = AsyncMock(return_value=mock_conversion_result)

        kwargs = {"render_js": False}
        if output_format is not None:
            kwargs["output_format"] = output_format

        result = await handle_read_url(mock_converter, "https://example.com", **kwargs)

        assert isinstance(result, expected_type)

    @pytest.mark.asyncio
    async def test_error_always_json(self, mock_converter):
        """Error responses should always be JSON regardless of output_format."""
        result = await handle_read_url(
            mock_converter,
            "invalid-url",
            render_js=False,
            output_format="markdown",
        )

        assert isinstance(result, MCPErrorResponse)
        assert result.error.code == ErrorCode.INVALID_URL

    @pytest.mark.asyncio
    async def test_success(self, mock_converter, mock_conversion_result):
        """Should return success response for valid URL (JSON format)."""
        mock_converter.convert_url = AsyncMock(return_value=mock_conversion_result)

        result = await handle_read_url(
            mock_converter, "https://example.com", render_js=False, output_format="json"
        )

        assert isinstance(result, MCPSuccessResponse)
        assert result.success is True
        assert result.title == "Test Title"

    @pytest.mark.asyncio
    async def test_invalid_url_no_scheme(self, mock_converter):
        """Should return error for URL without scheme."""
        result = await handle_read_url(mock_converter, "example.com", render_js=False)

        assert isinstance(result, MCPErrorResponse)
        assert result.error.code == ErrorCode.INVALID_URL

    @pytest.mark.asyncio
    async def test_invalid_url_ftp_scheme(self, mock_converter):
        """Should return error for non-http schemes."""
        result = await handle_read_url(
            mock_converter, "ftp://example.com", render_js=False
        )

        assert isinstance(result, MCPErrorResponse)
        assert result.error.code == ErrorCode.INVALID_URL

    @pytest.mark.asyncio
    async def test_timeout_error(self, mock_converter):
        """Should return timeout error when conversion times out."""
        mock_converter.convert_url = AsyncMock(side_effect=TimeoutError())

        result = await handle_read_url(
            mock_converter, "https://slow.com", render_js=False
        )

        assert isinstance(result, MCPErrorResponse)
        assert result.error.code == ErrorCode.TIMEOUT

    @pytest.mark.asyncio
    async def test_connection_error(self, mock_converter):
        """Should return connection error when URL unreachable."""
        mock_converter.convert_url = AsyncMock(
            side_effect=ConnectionError("Connection refused")
        )

        result = await handle_read_url(
            mock_converter, "https://unreachable.com", render_js=False
        )

        assert isinstance(result, MCPErrorResponse)
        assert result.error.code == ErrorCode.CONNECTION_FAILED

    @pytest.mark.asyncio
    async def test_empty_content(self, mock_converter):
        """Should return content empty error for minimal content."""
        mock_result = MagicMock()
        mock_result.markdown = "..."
        mock_result.metadata = MagicMock()
        mock_result.metadata.title = "Empty"
        mock_result.metadata.detected_language = None
        mock_converter.convert_url = AsyncMock(return_value=mock_result)

        result = await handle_read_url(
            mock_converter, "https://spa.com", render_js=False
        )

        assert isinstance(result, MCPErrorResponse)
        assert result.error.code == ErrorCode.CONTENT_EMPTY

    @pytest.mark.asyncio
    async def test_render_js_passed_to_converter(
        self, mock_converter, mock_conversion_result
    ):
        """Should pass render_js to converter."""
        mock_converter.convert_url = AsyncMock(return_value=mock_conversion_result)

        await handle_read_url(mock_converter, "https://example.com", render_js=True)

        mock_converter.convert_url.assert_called_once()
        call_kwargs = mock_converter.convert_url.call_args.kwargs
        assert call_kwargs["js_rendering"] is True

    @pytest.mark.asyncio
    async def test_max_length_passed_to_converter(
        self, mock_converter, mock_conversion_result
    ):
        """Should pass max_length to converter."""
        mock_converter.convert_url = AsyncMock(return_value=mock_conversion_result)

        await handle_read_url(mock_converter, "https://example.com", max_length=100)

        mock_converter.convert_url.assert_called_once()
        call_kwargs = mock_converter.convert_url.call_args.kwargs
        assert call_kwargs["max_length"] == 100

    @pytest.mark.asyncio
    async def test_max_length_none_not_passed(
        self, mock_converter, mock_conversion_result
    ):
        """Should not pass max_length when None."""
        mock_converter.convert_url = AsyncMock(return_value=mock_conversion_result)

        await handle_read_url(mock_converter, "https://example.com")

        mock_converter.convert_url.assert_called_once()
        call_kwargs = mock_converter.convert_url.call_args.kwargs
        assert "max_length" not in call_kwargs

    @pytest.mark.asyncio
    async def test_timeout_passed_to_converter(
        self, mock_converter, mock_conversion_result
    ):
        """Should pass timeout to converter."""
        mock_converter.convert_url = AsyncMock(return_value=mock_conversion_result)

        await handle_read_url(mock_converter, "https://example.com", timeout=60)

        mock_converter.convert_url.assert_called_once()
        call_kwargs = mock_converter.convert_url.call_args.kwargs
        assert call_kwargs["timeout"] == 60

    @pytest.mark.asyncio
    async def test_timeout_none_not_passed(
        self, mock_converter, mock_conversion_result
    ):
        """Should not pass timeout when None."""
        mock_converter.convert_url = AsyncMock(return_value=mock_conversion_result)

        await handle_read_url(mock_converter, "https://example.com")

        mock_converter.convert_url.assert_called_once()
        call_kwargs = mock_converter.convert_url.call_args.kwargs
        assert "timeout" not in call_kwargs

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "include_frontmatter,expected",
        [
            (True, True),
            (False, False),
        ],
        ids=["with_frontmatter", "without_frontmatter"],
    )
    async def test_include_frontmatter_passed_to_converter(
        self, mock_converter, mock_conversion_result, include_frontmatter, expected
    ):
        """Should pass include_frontmatter to converter."""
        mock_converter.convert_url = AsyncMock(return_value=mock_conversion_result)

        await handle_read_url(
            mock_converter,
            "https://example.com",
            include_frontmatter=include_frontmatter,
        )

        mock_converter.convert_url.assert_called_once()
        call_kwargs = mock_converter.convert_url.call_args.kwargs
        assert call_kwargs["include_frontmatter"] is expected

    @pytest.mark.asyncio
    async def test_include_frontmatter_default_true(
        self, mock_converter, mock_conversion_result
    ):
        """Should default include_frontmatter to True."""
        mock_converter.convert_url = AsyncMock(return_value=mock_conversion_result)

        await handle_read_url(mock_converter, "https://example.com")

        mock_converter.convert_url.assert_called_once()
        call_kwargs = mock_converter.convert_url.call_args.kwargs
        assert call_kwargs["include_frontmatter"] is True

    @pytest.mark.asyncio
    async def test_word_count_calculated(self, mock_converter, mock_conversion_result):
        """Should calculate word count from content (JSON format)."""
        mock_converter.convert_url = AsyncMock(return_value=mock_conversion_result)

        result = await handle_read_url(
            mock_converter, "https://example.com", output_format="json"
        )

        assert isinstance(result, MCPSuccessResponse)
        assert result.word_count > 0

    @pytest.mark.asyncio
    async def test_generic_exception(self, mock_converter):
        """Should return conversion error for generic exceptions."""
        mock_converter.convert_url = AsyncMock(
            side_effect=Exception("Something went wrong")
        )

        result = await handle_read_url(mock_converter, "https://example.com")

        assert isinstance(result, MCPErrorResponse)
        assert result.error.code == ErrorCode.CONVERSION_FAILED

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "exception,expected_code",
        [
            (NotFoundError("https://x.com"), ErrorCode.NOT_FOUND),
            (AccessDeniedError("https://x.com", 403), ErrorCode.ACCESS_DENIED),
            (ServerError("https://x.com", 500), ErrorCode.SERVER_ERROR),
            (URLTimeoutError("https://x.com", 30), ErrorCode.TIMEOUT),
            (
                URLConnectionError("https://x.com", "refused"),
                ErrorCode.CONNECTION_FAILED,
            ),
            (
                HTTPFetchError("err", CoreErrorCode.CONNECTION_FAILED),
                ErrorCode.CONVERSION_FAILED,
            ),
            (ConversionError("failed"), ErrorCode.CONVERSION_FAILED),
        ],
        ids=[
            "NotFound",
            "AccessDenied",
            "ServerError",
            "Timeout",
            "Connection",
            "HTTPFetch",
            "Conversion",
        ],
    )
    async def test_typed_exception_handling(
        self, mock_converter, exception, expected_code
    ):
        """Should return correct error code for typed exceptions."""
        mock_converter.convert_url = AsyncMock(side_effect=exception)
        mock_converter.timeout = 30

        result = await handle_read_url(mock_converter, "https://example.com")

        assert isinstance(result, MCPErrorResponse)
        assert result.error.code == expected_code


@pytest.mark.unit
class TestHandleReadFile:
    """Tests for handle_read_file handler."""

    @pytest.mark.asyncio
    async def test_success_default_markdown(
        self, mock_converter, mock_conversion_result
    ):
        """Should return raw markdown by default."""
        mock_converter.convert_content = AsyncMock(return_value=mock_conversion_result)

        result = await handle_read_file(
            mock_converter, b"fake pdf content", "report.pdf"
        )

        assert isinstance(result, str)
        assert "# Title" in result

    @pytest.mark.asyncio
    async def test_success_explicit_markdown(
        self, mock_converter, mock_conversion_result
    ):
        """Should return raw markdown when output_format=markdown."""
        mock_converter.convert_content = AsyncMock(return_value=mock_conversion_result)

        result = await handle_read_file(
            mock_converter,
            b"fake pdf content",
            "report.pdf",
            output_format="markdown",
        )

        assert isinstance(result, str)
        assert "# Title" in result

    @pytest.mark.asyncio
    async def test_success_json_format(self, mock_converter, mock_conversion_result):
        """Should return MCPSuccessResponse when output_format=json."""
        mock_converter.convert_content = AsyncMock(return_value=mock_conversion_result)

        result = await handle_read_file(
            mock_converter,
            b"fake pdf content",
            "report.pdf",
            output_format="json",
        )

        assert isinstance(result, MCPSuccessResponse)
        assert result.success is True

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "output_format,expected_type",
        [
            ("markdown", str),
            ("json", MCPSuccessResponse),
            (None, str),  # default should be markdown
        ],
        ids=["markdown", "json", "default"],
    )
    async def test_output_format_types(
        self, mock_converter, mock_conversion_result, output_format, expected_type
    ):
        """Should return correct type based on output_format."""
        mock_converter.convert_content = AsyncMock(return_value=mock_conversion_result)

        kwargs = {}
        if output_format is not None:
            kwargs["output_format"] = output_format

        result = await handle_read_file(
            mock_converter, b"fake content", "file.pdf", **kwargs
        )

        assert isinstance(result, expected_type)

    @pytest.mark.asyncio
    async def test_error_always_json(self, mock_converter):
        """Error responses should always be JSON regardless of output_format."""
        mock_converter.max_file_size_mb = 1
        large_content = b"x" * (2 * 1024 * 1024)  # 2MB

        result = await handle_read_file(
            mock_converter,
            large_content,
            "large.pdf",
            output_format="markdown",
        )

        assert isinstance(result, MCPErrorResponse)
        assert result.error.code == ErrorCode.FILE_TOO_LARGE

    @pytest.mark.asyncio
    async def test_success_pdf(self, mock_converter, mock_conversion_result):
        """Should return success for PDF conversion (JSON format)."""
        mock_converter.convert_content = AsyncMock(return_value=mock_conversion_result)

        result = await handle_read_file(
            mock_converter, b"fake pdf content", "report.pdf", output_format="json"
        )

        assert isinstance(result, MCPSuccessResponse)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_auto_ocr_for_png(self, mock_converter, mock_conversion_result):
        """Should enable OCR for PNG images."""
        mock_converter.convert_content = AsyncMock(return_value=mock_conversion_result)

        await handle_read_file(mock_converter, b"fake image", "screenshot.png")

        call_kwargs = mock_converter.convert_content.call_args.kwargs
        assert call_kwargs["ocr_enabled"] is True

    @pytest.mark.asyncio
    async def test_auto_ocr_for_jpg(self, mock_converter, mock_conversion_result):
        """Should enable OCR for JPG images."""
        mock_converter.convert_content = AsyncMock(return_value=mock_conversion_result)

        await handle_read_file(mock_converter, b"fake image", "photo.jpg")

        call_kwargs = mock_converter.convert_content.call_args.kwargs
        assert call_kwargs["ocr_enabled"] is True

    @pytest.mark.asyncio
    async def test_auto_ocr_for_jpeg(self, mock_converter, mock_conversion_result):
        """Should enable OCR for JPEG images."""
        mock_converter.convert_content = AsyncMock(return_value=mock_conversion_result)

        await handle_read_file(mock_converter, b"fake image", "photo.jpeg")

        call_kwargs = mock_converter.convert_content.call_args.kwargs
        assert call_kwargs["ocr_enabled"] is True

    @pytest.mark.asyncio
    async def test_no_ocr_for_pdf(self, mock_converter, mock_conversion_result):
        """Should not enable OCR for PDF files."""
        mock_converter.convert_content = AsyncMock(return_value=mock_conversion_result)

        await handle_read_file(mock_converter, b"pdf content", "doc.pdf")

        call_kwargs = mock_converter.convert_content.call_args.kwargs
        assert call_kwargs.get("ocr_enabled") is not True

    @pytest.mark.asyncio
    async def test_max_length_passed_to_converter(
        self, mock_converter, mock_conversion_result
    ):
        """Should pass max_length to converter."""
        mock_converter.convert_content = AsyncMock(return_value=mock_conversion_result)

        await handle_read_file(
            mock_converter, b"fake content", "doc.pdf", max_length=100
        )

        call_kwargs = mock_converter.convert_content.call_args.kwargs
        assert call_kwargs["max_length"] == 100

    @pytest.mark.asyncio
    async def test_max_length_none_not_passed(
        self, mock_converter, mock_conversion_result
    ):
        """Should not pass max_length when None."""
        mock_converter.convert_content = AsyncMock(return_value=mock_conversion_result)

        await handle_read_file(mock_converter, b"fake content", "doc.pdf")

        call_kwargs = mock_converter.convert_content.call_args.kwargs
        assert "max_length" not in call_kwargs

    @pytest.mark.asyncio
    async def test_timeout_passed_to_converter(
        self, mock_converter, mock_conversion_result
    ):
        """Should pass timeout to converter."""
        mock_converter.convert_content = AsyncMock(return_value=mock_conversion_result)

        await handle_read_file(mock_converter, b"fake content", "doc.pdf", timeout=60)

        call_kwargs = mock_converter.convert_content.call_args.kwargs
        assert call_kwargs["timeout"] == 60

    @pytest.mark.asyncio
    async def test_timeout_none_not_passed(
        self, mock_converter, mock_conversion_result
    ):
        """Should not pass timeout when None."""
        mock_converter.convert_content = AsyncMock(return_value=mock_conversion_result)

        await handle_read_file(mock_converter, b"fake content", "doc.pdf")

        call_kwargs = mock_converter.convert_content.call_args.kwargs
        assert "timeout" not in call_kwargs

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "include_frontmatter,expected",
        [
            (True, True),
            (False, False),
        ],
        ids=["with_frontmatter", "without_frontmatter"],
    )
    async def test_include_frontmatter_passed_to_converter(
        self, mock_converter, mock_conversion_result, include_frontmatter, expected
    ):
        """Should pass include_frontmatter to converter."""
        mock_converter.convert_content = AsyncMock(return_value=mock_conversion_result)

        await handle_read_file(
            mock_converter,
            b"fake content",
            "doc.pdf",
            include_frontmatter=include_frontmatter,
        )

        call_kwargs = mock_converter.convert_content.call_args.kwargs
        assert call_kwargs["include_frontmatter"] is expected

    @pytest.mark.asyncio
    async def test_include_frontmatter_default_true(
        self, mock_converter, mock_conversion_result
    ):
        """Should default include_frontmatter to True."""
        mock_converter.convert_content = AsyncMock(return_value=mock_conversion_result)

        await handle_read_file(mock_converter, b"fake content", "doc.pdf")

        call_kwargs = mock_converter.convert_content.call_args.kwargs
        assert call_kwargs["include_frontmatter"] is True

    @pytest.mark.asyncio
    async def test_timeout_error(self, mock_converter):
        """Should return timeout error when conversion times out."""
        mock_converter.convert_content = AsyncMock(side_effect=TimeoutError())

        result = await handle_read_file(mock_converter, b"data", "file.pdf")

        assert isinstance(result, MCPErrorResponse)
        assert result.error.code == ErrorCode.TIMEOUT

    @pytest.mark.asyncio
    async def test_file_too_large(self, mock_converter):
        """Should return error for files exceeding size limit."""
        mock_converter.max_file_size_mb = 1
        large_content = b"x" * (2 * 1024 * 1024)  # 2MB

        result = await handle_read_file(mock_converter, large_content, "large.pdf")

        assert isinstance(result, MCPErrorResponse)
        assert result.error.code == ErrorCode.FILE_TOO_LARGE

    @pytest.mark.asyncio
    async def test_unsupported_format(self, mock_converter):
        """Should return error for unsupported formats."""
        mock_converter.convert_content = AsyncMock(
            side_effect=ValueError("Unsupported format")
        )

        result = await handle_read_file(mock_converter, b"data", "file.xyz")

        assert isinstance(result, MCPErrorResponse)
        assert result.error.code == ErrorCode.UNSUPPORTED_FORMAT

    @pytest.mark.asyncio
    async def test_ocr_applied_in_metadata(
        self, mock_converter, mock_conversion_result
    ):
        """Should set ocr_applied in metadata for images (JSON format)."""
        mock_converter.convert_content = AsyncMock(return_value=mock_conversion_result)

        result = await handle_read_file(
            mock_converter, b"image", "photo.png", output_format="json"
        )

        assert isinstance(result, MCPSuccessResponse)
        assert result.metadata.ocr_applied is True

    @pytest.mark.asyncio
    async def test_source_is_filename(self, mock_converter, mock_conversion_result):
        """Should use filename as source (JSON format)."""
        mock_converter.convert_content = AsyncMock(return_value=mock_conversion_result)

        result = await handle_read_file(
            mock_converter, b"data", "myfile.pdf", output_format="json"
        )

        assert isinstance(result, MCPSuccessResponse)
        assert result.source == "myfile.pdf"

    @pytest.mark.asyncio
    async def test_generic_exception(self, mock_converter):
        """Should return conversion error for generic exceptions."""
        mock_converter.convert_content = AsyncMock(
            side_effect=Exception("Something went wrong")
        )

        result = await handle_read_file(mock_converter, b"data", "file.pdf")

        assert isinstance(result, MCPErrorResponse)
        assert result.error.code == ErrorCode.CONVERSION_FAILED

    @pytest.mark.asyncio
    async def test_value_error_too_large(self, mock_converter):
        """Should return file too large error for 'too large' ValueError."""
        mock_converter.convert_content = AsyncMock(
            side_effect=ValueError("File too large to process")
        )

        result = await handle_read_file(mock_converter, b"data", "file.pdf")

        assert isinstance(result, MCPErrorResponse)
        assert result.error.code == ErrorCode.FILE_TOO_LARGE


@pytest.mark.unit
class TestHandleReadUrlSsrf:
    """Tests for SSRF handling in handle_read_url."""

    @pytest.fixture
    def mock_converter(self):
        """Create a mock DocumentConverter."""
        converter = MagicMock()
        converter.timeout = 60
        return converter

    @pytest.mark.asyncio
    async def test_ssrf_blocked_url(self, mock_converter):
        """Should return connection error for SSRF blocked URLs."""
        mock_converter.convert_url = AsyncMock(
            side_effect=ValueError("URL blocked by SSRF protection")
        )

        result = await handle_read_url(
            mock_converter, "https://169.254.169.254/metadata", render_js=False
        )

        assert isinstance(result, MCPErrorResponse)
        assert result.error.code == ErrorCode.CONNECTION_FAILED

    @pytest.mark.asyncio
    async def test_ssrf_blocked_lowercase(self, mock_converter):
        """Should handle 'blocked' keyword in error message."""
        mock_converter.convert_url = AsyncMock(
            side_effect=ValueError("This URL is blocked")
        )

        result = await handle_read_url(
            mock_converter, "https://internal.local", render_js=False
        )

        assert isinstance(result, MCPErrorResponse)
        assert result.error.code == ErrorCode.CONNECTION_FAILED

    @pytest.mark.asyncio
    async def test_value_error_non_ssrf(self, mock_converter):
        """Should return conversion error for non-SSRF ValueError."""
        mock_converter.convert_url = AsyncMock(
            side_effect=ValueError("Some other validation error")
        )

        result = await handle_read_url(
            mock_converter, "https://example.com", render_js=False
        )

        assert isinstance(result, MCPErrorResponse)
        assert result.error.code == ErrorCode.CONVERSION_FAILED


@pytest.mark.unit
class TestExtractTitleFromUrl:
    """Tests for _extract_title_from_url helper."""

    def test_title_from_path_segment(self):
        """Should extract title from URL path."""
        from md_server.mcp.handlers import _extract_title_from_url

        result = _extract_title_from_url("https://example.com/my-article")
        assert result == "My Article"

    def test_title_from_path_with_html_extension(self):
        """Should strip .html extension."""
        from md_server.mcp.handlers import _extract_title_from_url

        result = _extract_title_from_url("https://example.com/page.html")
        assert result == "Page"

    def test_title_from_path_with_php_extension(self):
        """Should strip .php extension."""
        from md_server.mcp.handlers import _extract_title_from_url

        result = _extract_title_from_url("https://example.com/contact.php")
        assert result == "Contact"

    def test_title_underscores_to_spaces(self):
        """Should convert underscores to spaces."""
        from md_server.mcp.handlers import _extract_title_from_url

        result = _extract_title_from_url("https://example.com/my_cool_page")
        assert result == "My Cool Page"

    def test_fallback_to_domain(self):
        """Should fall back to domain when path is empty."""
        from md_server.mcp.handlers import _extract_title_from_url

        result = _extract_title_from_url("https://example.com/")
        assert result == "example.com"

    def test_fallback_to_domain_no_trailing_slash(self):
        """Should fall back to domain when path is root."""
        from md_server.mcp.handlers import _extract_title_from_url

        result = _extract_title_from_url("https://example.com")
        assert result == "example.com"

    def test_nested_path(self):
        """Should extract last segment from nested path."""
        from md_server.mcp.handlers import _extract_title_from_url

        result = _extract_title_from_url("https://example.com/docs/api/getting-started")
        assert result == "Getting Started"

    def test_path_ending_with_slash_then_segment(self):
        """Should handle paths with multiple slashes."""
        from md_server.mcp.handlers import _extract_title_from_url

        result = _extract_title_from_url("https://example.com/blog/")
        assert result == "Blog"

    def test_path_with_trailing_slashes(self):
        """Should handle paths with trailing slashes."""
        from md_server.mcp.handlers import _extract_title_from_url

        # Trailing slashes are stripped, so /foo// becomes /foo
        result = _extract_title_from_url("https://example.com/foo//")
        assert result == "Foo"


@pytest.mark.unit
class TestHandleReadFileValueError:
    """Additional tests for ValueError handling in handle_read_file."""

    @pytest.fixture
    def mock_converter(self):
        """Create a mock DocumentConverter."""
        converter = MagicMock()
        converter.timeout = 60
        converter.max_file_size_mb = 50
        return converter

    @pytest.mark.asyncio
    async def test_value_error_generic(self, mock_converter):
        """Should return conversion error for generic ValueError."""
        mock_converter.convert_content = AsyncMock(
            side_effect=ValueError("Some random error occurred")
        )

        result = await handle_read_file(mock_converter, b"data", "file.pdf")

        assert isinstance(result, MCPErrorResponse)
        assert result.error.code == ErrorCode.CONVERSION_FAILED
