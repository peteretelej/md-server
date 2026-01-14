"""Tests for MCP tool handlers."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from md_server.mcp.handlers import (
    handle_read_url,
    handle_read_file,
    _extract_title_from_url,
)
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
    result.metadata.detected_format = "text/html"
    result.metadata.was_truncated = False
    result.metadata.original_length = None
    result.metadata.original_tokens = None
    result.metadata.truncation_mode = None
    return result


@pytest.mark.unit
class TestHandleReadUrl:
    """Tests for handle_read_url handler."""

    # --- Output Format Tests (table-driven) ---

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "output_format,expected_type,check_field",
        [
            (None, str, None),  # default is markdown
            ("markdown", str, None),
            ("json", MCPSuccessResponse, "success"),
        ],
        ids=["default_markdown", "explicit_markdown", "json"],
    )
    async def test_output_format_returns_correct_type(
        self,
        mock_converter,
        mock_conversion_result,
        output_format,
        expected_type,
        check_field,
    ):
        """Should return correct type based on output_format."""
        mock_converter.convert_url = AsyncMock(return_value=mock_conversion_result)

        kwargs = {"render_js": False}
        if output_format is not None:
            kwargs["output_format"] = output_format

        result = await handle_read_url(mock_converter, "https://example.com", **kwargs)

        assert isinstance(result, expected_type)
        if check_field:
            assert getattr(result, check_field) is True

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

    # --- Invalid URL Tests (table-driven) ---

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "url",
        [
            "example.com",  # no scheme
            "ftp://example.com",  # non-http scheme
        ],
        ids=["no_scheme", "ftp_scheme"],
    )
    async def test_invalid_url_rejected(self, mock_converter, url):
        """Should return error for invalid URLs."""
        result = await handle_read_url(mock_converter, url, render_js=False)

        assert isinstance(result, MCPErrorResponse)
        assert result.error.code == ErrorCode.INVALID_URL

    # --- Error Handling Tests (table-driven) ---

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "exception,expected_code",
        [
            (TimeoutError(), ErrorCode.TIMEOUT),
            (ConnectionError("Connection refused"), ErrorCode.CONNECTION_FAILED),
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
            (Exception("Something went wrong"), ErrorCode.CONVERSION_FAILED),
        ],
        ids=[
            "TimeoutError",
            "ConnectionError",
            "NotFound",
            "AccessDenied",
            "ServerError",
            "URLTimeout",
            "URLConnection",
            "HTTPFetch",
            "Conversion",
            "GenericException",
        ],
    )
    async def test_exception_handling(self, mock_converter, exception, expected_code):
        """Should return correct error code for various exceptions."""
        mock_converter.convert_url = AsyncMock(side_effect=exception)
        mock_converter.timeout = 30

        result = await handle_read_url(mock_converter, "https://example.com")

        assert isinstance(result, MCPErrorResponse)
        assert result.error.code == expected_code

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

    # --- Parameter Passing Tests (table-driven) ---

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "param_name,param_value,converter_key",
        [
            ("max_length", 100, "max_length"),
            ("max_tokens", 500, "max_tokens"),
            ("timeout", 60, "timeout"),
            ("truncate_mode", "sections", "truncate_mode"),
            ("truncate_limit", 5, "truncate_limit"),
        ],
        ids=["max_length", "max_tokens", "timeout", "truncate_mode", "truncate_limit"],
    )
    async def test_optional_param_passed_when_set(
        self,
        mock_converter,
        mock_conversion_result,
        param_name,
        param_value,
        converter_key,
    ):
        """Should pass optional parameters to converter when set."""
        mock_converter.convert_url = AsyncMock(return_value=mock_conversion_result)

        kwargs = {param_name: param_value}
        await handle_read_url(mock_converter, "https://example.com", **kwargs)

        mock_converter.convert_url.assert_called_once()
        call_kwargs = mock_converter.convert_url.call_args.kwargs
        assert call_kwargs[converter_key] == param_value

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "param_name",
        ["max_length", "max_tokens", "timeout", "truncate_mode", "truncate_limit"],
        ids=["max_length", "max_tokens", "timeout", "truncate_mode", "truncate_limit"],
    )
    async def test_optional_param_not_passed_when_none(
        self, mock_converter, mock_conversion_result, param_name
    ):
        """Should not pass optional parameters when None."""
        mock_converter.convert_url = AsyncMock(return_value=mock_conversion_result)

        await handle_read_url(mock_converter, "https://example.com")

        mock_converter.convert_url.assert_called_once()
        call_kwargs = mock_converter.convert_url.call_args.kwargs
        assert param_name not in call_kwargs

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
    @pytest.mark.parametrize(
        "include_frontmatter,expected",
        [(True, True), (False, False)],
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


@pytest.mark.unit
class TestHandleReadFile:
    """Tests for handle_read_file handler."""

    # --- Output Format Tests (table-driven) ---

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "output_format,expected_type",
        [
            (None, str),  # default is markdown
            ("markdown", str),
            ("json", MCPSuccessResponse),
        ],
        ids=["default_markdown", "explicit_markdown", "json"],
    )
    async def test_output_format_returns_correct_type(
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

    # --- OCR Auto-Enable Tests (table-driven) ---

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "filename,should_ocr",
        [
            ("screenshot.png", True),
            ("photo.jpg", True),
            ("photo.jpeg", True),
            ("doc.pdf", False),
        ],
        ids=["png", "jpg", "jpeg", "pdf"],
    )
    async def test_auto_ocr_by_extension(
        self, mock_converter, mock_conversion_result, filename, should_ocr
    ):
        """Should enable OCR for image files, not for others."""
        mock_converter.convert_content = AsyncMock(return_value=mock_conversion_result)

        await handle_read_file(mock_converter, b"fake content", filename)

        call_kwargs = mock_converter.convert_content.call_args.kwargs
        if should_ocr:
            assert call_kwargs["ocr_enabled"] is True
        else:
            assert call_kwargs.get("ocr_enabled") is not True

    # --- Parameter Passing Tests (table-driven) ---

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "param_name,param_value,converter_key",
        [
            ("max_length", 100, "max_length"),
            ("max_tokens", 500, "max_tokens"),
            ("timeout", 60, "timeout"),
            ("truncate_mode", "paragraphs", "truncate_mode"),
            ("truncate_limit", 3, "truncate_limit"),
        ],
        ids=["max_length", "max_tokens", "timeout", "truncate_mode", "truncate_limit"],
    )
    async def test_optional_param_passed_when_set(
        self,
        mock_converter,
        mock_conversion_result,
        param_name,
        param_value,
        converter_key,
    ):
        """Should pass optional parameters to converter when set."""
        mock_converter.convert_content = AsyncMock(return_value=mock_conversion_result)

        kwargs = {param_name: param_value}
        await handle_read_file(mock_converter, b"fake content", "doc.pdf", **kwargs)

        mock_converter.convert_content.assert_called_once()
        call_kwargs = mock_converter.convert_content.call_args.kwargs
        assert call_kwargs[converter_key] == param_value

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "param_name",
        ["max_length", "max_tokens", "timeout", "truncate_mode", "truncate_limit"],
        ids=["max_length", "max_tokens", "timeout", "truncate_mode", "truncate_limit"],
    )
    async def test_optional_param_not_passed_when_none(
        self, mock_converter, mock_conversion_result, param_name
    ):
        """Should not pass optional parameters when None."""
        mock_converter.convert_content = AsyncMock(return_value=mock_conversion_result)

        await handle_read_file(mock_converter, b"fake content", "doc.pdf")

        mock_converter.convert_content.assert_called_once()
        call_kwargs = mock_converter.convert_content.call_args.kwargs
        assert param_name not in call_kwargs

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "include_frontmatter,expected",
        [(True, True), (False, False)],
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

        mock_converter.convert_content.assert_called_once()
        call_kwargs = mock_converter.convert_content.call_args.kwargs
        assert call_kwargs["include_frontmatter"] is expected

    @pytest.mark.asyncio
    async def test_include_frontmatter_default_true(
        self, mock_converter, mock_conversion_result
    ):
        """Should default include_frontmatter to True."""
        mock_converter.convert_content = AsyncMock(return_value=mock_conversion_result)

        await handle_read_file(mock_converter, b"fake content", "doc.pdf")

        mock_converter.convert_content.assert_called_once()
        call_kwargs = mock_converter.convert_content.call_args.kwargs
        assert call_kwargs["include_frontmatter"] is True

    # --- Error Handling Tests (table-driven) ---

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "exception,expected_code",
        [
            (TimeoutError(), ErrorCode.TIMEOUT),
            (ValueError("Unsupported format"), ErrorCode.UNSUPPORTED_FORMAT),
            (ValueError("File too large to process"), ErrorCode.FILE_TOO_LARGE),
            (ValueError("Some random error occurred"), ErrorCode.CONVERSION_FAILED),
            (Exception("Something went wrong"), ErrorCode.CONVERSION_FAILED),
        ],
        ids=[
            "timeout",
            "unsupported",
            "too_large",
            "generic_valueerror",
            "generic_exception",
        ],
    )
    async def test_exception_handling(self, mock_converter, exception, expected_code):
        """Should return correct error code for various exceptions."""
        mock_converter.convert_content = AsyncMock(side_effect=exception)

        result = await handle_read_file(mock_converter, b"data", "file.pdf")

        assert isinstance(result, MCPErrorResponse)
        assert result.error.code == expected_code

    @pytest.mark.asyncio
    async def test_file_too_large(self, mock_converter):
        """Should return error for files exceeding size limit."""
        mock_converter.max_file_size_mb = 1
        large_content = b"x" * (2 * 1024 * 1024)  # 2MB

        result = await handle_read_file(mock_converter, large_content, "large.pdf")

        assert isinstance(result, MCPErrorResponse)
        assert result.error.code == ErrorCode.FILE_TOO_LARGE

    # --- Metadata Tests ---

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
    @pytest.mark.parametrize(
        "error_message,expected_code",
        [
            ("URL blocked by SSRF protection", ErrorCode.CONNECTION_FAILED),
            ("This URL is blocked", ErrorCode.CONNECTION_FAILED),
            ("Some other validation error", ErrorCode.CONVERSION_FAILED),
        ],
        ids=["ssrf_blocked", "blocked_keyword", "non_ssrf"],
    )
    async def test_ssrf_value_error_handling(
        self, mock_converter, error_message, expected_code
    ):
        """Should return correct error code for SSRF-related ValueErrors."""
        mock_converter.convert_url = AsyncMock(side_effect=ValueError(error_message))

        result = await handle_read_url(
            mock_converter, "https://example.com", render_js=False
        )

        assert isinstance(result, MCPErrorResponse)
        assert result.error.code == expected_code


@pytest.mark.unit
class TestExtractTitleFromUrl:
    """Tests for _extract_title_from_url helper."""

    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://example.com/my-article", "My Article"),
            ("https://example.com/page.html", "Page"),
            ("https://example.com/contact.php", "Contact"),
            ("https://example.com/my_cool_page", "My Cool Page"),
            ("https://example.com/", "example.com"),
            ("https://example.com", "example.com"),
            ("https://example.com/docs/api/getting-started", "Getting Started"),
            ("https://example.com/blog/", "Blog"),
            ("https://example.com/foo//", "Foo"),
        ],
        ids=[
            "path_with_hyphens",
            "html_extension",
            "php_extension",
            "underscores",
            "root_with_slash",
            "root_no_slash",
            "nested_path",
            "trailing_slash",
            "double_trailing_slash",
        ],
    )
    def test_extract_title_from_url(self, url, expected):
        """Should extract title correctly from various URL patterns."""
        assert _extract_title_from_url(url) == expected
