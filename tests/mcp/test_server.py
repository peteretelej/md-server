"""Tests for MCP server functionality."""

import base64
import json
import logging
import pytest
from unittest.mock import patch, Mock, AsyncMock, MagicMock

from mcp.server.fastmcp.exceptions import ToolError

from md_server.mcp.server import convert_to_markdown, get_converter, mcp


async def _get_tool():
    """Get the convert_to_markdown tool from FastMCP."""
    tools = await mcp.list_tools()
    return next(t for t in tools if t.name == "convert_to_markdown")


@pytest.mark.unit
class TestMCPServer:
    """Test MCP server functionality."""

    @pytest.mark.asyncio
    async def test_tool_is_registered(self):
        """convert_to_markdown should be registered as a tool."""
        tools = await mcp.list_tools()
        names = [t.name for t in tools]
        assert "convert_to_markdown" in names

    @pytest.mark.asyncio
    async def test_tool_has_no_output_schema(self):
        """Tool should not have an output schema (avoids Claude Code bug)."""
        tool = await _get_tool()
        assert tool.outputSchema is None

    @pytest.mark.asyncio
    async def test_tool_has_readonly_annotation(self):
        """Tool should have readOnlyHint annotation."""
        tool = await _get_tool()
        assert tool.annotations is not None
        assert tool.annotations.readOnlyHint is True

    @pytest.mark.asyncio
    async def test_tool_has_expected_parameters(self):
        """Tool should have all expected input parameters."""
        tool = await _get_tool()
        props = tool.inputSchema.get("properties", {})
        expected = [
            "url",
            "file_content",
            "filename",
            "render_js",
            "max_length",
            "max_tokens",
            "truncate_mode",
            "truncate_limit",
            "timeout",
            "include_frontmatter",
            "output_format",
        ]
        for param in expected:
            assert param in props, f"missing parameter: {param}"

    @pytest.mark.asyncio
    async def test_tool_has_output_format_default(self):
        """Tool should have output_format with default 'markdown'."""
        tool = await _get_tool()
        props = tool.inputSchema.get("properties", {})
        assert "output_format" in props
        assert props["output_format"]["default"] == "markdown"

    # --- Output Format Tests ---

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "output_format,is_json",
        [
            (None, False),  # default is markdown
            ("markdown", False),
            ("json", True),
        ],
        ids=["default_markdown", "explicit_markdown", "json"],
    )
    async def test_url_output_format(self, output_format, is_json):
        """convert_to_markdown with url should return correct format."""
        with patch("md_server.mcp.server.get_converter") as mock_get:
            mock_conv = MagicMock()
            mock_conv.timeout = 60
            mock_metadata = MagicMock(
                title="Hello World",
                detected_language="en",
                was_truncated=False,
                original_length=None,
                original_tokens=None,
                truncation_mode=None,
            )
            mock_conv.convert_url = AsyncMock(
                return_value=MagicMock(
                    markdown="# Hello World with more than five words",
                    metadata=mock_metadata,
                )
            )
            mock_get.return_value = mock_conv

            kwargs = {"url": "https://example.com"}
            if output_format is not None:
                kwargs["output_format"] = output_format

            result = await convert_to_markdown(**kwargs)

            assert isinstance(result, str)
            if is_json:
                data = json.loads(result)
                assert data["success"] is True
            else:
                assert result.startswith("# Hello World")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "output_format,is_json",
        [
            (None, False),
            ("markdown", False),
            ("json", True),
        ],
        ids=["default_markdown", "explicit_markdown", "json"],
    )
    async def test_file_output_format(self, output_format, is_json):
        """convert_to_markdown with file_content should return correct format."""
        with patch("md_server.mcp.server.get_converter") as mock_get:
            mock_metadata = MagicMock()
            mock_metadata.title = "Doc"
            mock_metadata.detected_language = "en"
            mock_metadata.detected_format = "application/pdf"
            mock_metadata.was_truncated = False
            mock_metadata.original_length = None
            mock_metadata.original_tokens = None
            mock_metadata.truncation_mode = None

            mock_conv = MagicMock()
            mock_conv.timeout = 60
            mock_conv.max_file_size_mb = 50
            mock_conv.convert_content = AsyncMock(
                return_value=MagicMock(
                    markdown="# Markdown Content with more than five words here",
                    metadata=mock_metadata,
                )
            )
            mock_get.return_value = mock_conv

            content = base64.b64encode(b"fake pdf content").decode()
            kwargs = {"file_content": content, "filename": "test.pdf"}
            if output_format is not None:
                kwargs["output_format"] = output_format

            result = await convert_to_markdown(**kwargs)

            assert isinstance(result, str)
            if is_json:
                data = json.loads(result)
                assert data["success"] is True
            else:
                assert result.startswith("# Markdown Content")

    # --- Parameter Passing Tests ---

    @pytest.mark.asyncio
    async def test_url_passes_new_options(self):
        """convert_to_markdown with url should pass options to handler."""
        with patch("md_server.mcp.server.get_converter") as mock_get:
            mock_conv = MagicMock()
            mock_conv.timeout = 60
            mock_conv.convert_url = AsyncMock(
                return_value=MagicMock(
                    markdown="# Hello World with more than five words",
                    metadata=MagicMock(title="Hello World", detected_language="en"),
                )
            )
            mock_get.return_value = mock_conv

            await convert_to_markdown(
                url="https://example.com",
                max_length=100,
                timeout=30,
                include_frontmatter=False,
            )

            mock_conv.convert_url.assert_called_once()
            call_kwargs = mock_conv.convert_url.call_args.kwargs
            assert call_kwargs["max_length"] == 100
            assert call_kwargs["timeout"] == 30
            assert call_kwargs["include_frontmatter"] is False

    @pytest.mark.asyncio
    async def test_file_passes_new_options(self):
        """convert_to_markdown with file_content should pass options to handler."""
        with patch("md_server.mcp.server.get_converter") as mock_get:
            mock_metadata = MagicMock()
            mock_metadata.title = "Doc"
            mock_metadata.detected_language = "en"
            mock_metadata.detected_format = "application/pdf"

            mock_conv = MagicMock()
            mock_conv.timeout = 60
            mock_conv.max_file_size_mb = 50
            mock_conv.convert_content = AsyncMock(
                return_value=MagicMock(
                    markdown="# Markdown Content with more than five words here",
                    metadata=mock_metadata,
                )
            )
            mock_get.return_value = mock_conv

            content = base64.b64encode(b"fake pdf content").decode()
            await convert_to_markdown(
                file_content=content,
                filename="test.pdf",
                max_length=200,
                timeout=45,
                include_frontmatter=False,
            )

            mock_conv.convert_content.assert_called_once()
            call_kwargs = mock_conv.convert_content.call_args.kwargs
            assert call_kwargs["max_length"] == 200
            assert call_kwargs["timeout"] == 45
            assert call_kwargs["include_frontmatter"] is False

    # --- Error Handling Tests ---

    @pytest.mark.asyncio
    async def test_error_missing_input(self):
        """Should raise ToolError when neither url nor file_content provided."""
        from mcp.server.fastmcp.exceptions import ToolError

        with pytest.raises(ToolError):
            await convert_to_markdown()

    @pytest.mark.asyncio
    async def test_error_both_inputs(self):
        """Should raise ToolError when both url and file_content provided."""
        from mcp.server.fastmcp.exceptions import ToolError

        content = base64.b64encode(b"data").decode()
        with pytest.raises(ToolError):
            await convert_to_markdown(
                url="https://example.com",
                file_content=content,
                filename="test.pdf",
            )

    @pytest.mark.asyncio
    async def test_error_missing_filename(self):
        """Should raise ToolError when file_content without filename."""
        from mcp.server.fastmcp.exceptions import ToolError

        content = base64.b64encode(b"data").decode()
        with pytest.raises(ToolError):
            await convert_to_markdown(file_content=content)

    @pytest.mark.asyncio
    async def test_error_invalid_base64(self):
        """Should raise ToolError for invalid base64."""
        from mcp.server.fastmcp.exceptions import ToolError

        with pytest.raises(ToolError, match="base64"):
            await convert_to_markdown(
                file_content="not-valid-base64!!!", filename="test.pdf"
            )


@pytest.mark.unit
class TestMCPTransports:
    """Test MCP transport and configuration."""

    def test_get_converter_uses_settings(self):
        """Verify converter is created with correct settings."""
        with patch("md_server.mcp.server.get_settings") as mock_settings:
            mock_settings.return_value = Mock(
                conversion_timeout=60,
                max_file_size=100 * 1024 * 1024,  # 100MB
            )
            converter = get_converter()
            assert converter.timeout == 60
            assert converter.max_file_size_mb == 100


@pytest.mark.unit
class TestBase64SizeValidation:
    """Tests for base64 pre-decode size estimation."""

    @pytest.mark.asyncio
    async def test_oversized_base64_rejected(self):
        """Should reject base64 input that would exceed max file size."""
        # Create a base64 string that decodes to ~75 bytes
        # but pretend max_file_size is very small
        large_b64 = base64.b64encode(b"x" * 100).decode()

        with patch("md_server.mcp.server.get_settings") as mock_settings:
            mock_settings.return_value = Mock(
                max_file_size=10,  # 10 bytes limit
                conversion_timeout=60,
            )
            with pytest.raises(ToolError, match="File too large"):
                await convert_to_markdown(file_content=large_b64, filename="test.pdf")

    @pytest.mark.asyncio
    async def test_base64_just_under_limit(self):
        """Should accept base64 input just under the size limit."""
        small_content = b"x" * 10
        small_b64 = base64.b64encode(small_content).decode()

        with (
            patch("md_server.mcp.server.get_converter") as mock_get,
            patch("md_server.mcp.server.get_settings") as mock_settings,
        ):
            mock_settings.return_value = Mock(
                max_file_size=1024 * 1024,  # 1MB
                conversion_timeout=60,
            )
            mock_conv = MagicMock()
            mock_conv.timeout = 60
            mock_conv.max_file_size_mb = 1
            mock_conv.convert_content = AsyncMock(
                return_value=MagicMock(
                    markdown="# Small file content with five words minimum",
                    metadata=MagicMock(
                        title="Doc",
                        detected_language="en",
                        detected_format="text/plain",
                    ),
                )
            )
            mock_get.return_value = mock_conv

            result = await convert_to_markdown(
                file_content=small_b64, filename="test.txt"
            )
            assert isinstance(result, str)


@pytest.mark.unit
class TestLogging:
    """Tests for logging output during tool invocation."""

    @pytest.mark.asyncio
    async def test_successful_conversion_logs(self, caplog):
        """Should log invocation start and success with duration."""
        with patch("md_server.mcp.server.get_converter") as mock_get:
            mock_conv = MagicMock()
            mock_conv.timeout = 60
            mock_conv.convert_url = AsyncMock(
                return_value=MagicMock(
                    markdown="# Content with more than five words here",
                    metadata=MagicMock(title="Page", detected_language="en"),
                )
            )
            mock_get.return_value = mock_conv

            with caplog.at_level(logging.INFO, logger="md_server.mcp.server"):
                await convert_to_markdown(url="https://example.com")

            log_text = caplog.text
            assert "convert_to_markdown" in log_text
            assert "input_type=url" in log_text
            assert "duration_ms=" in log_text
            assert "success" in log_text

    @pytest.mark.asyncio
    async def test_error_conversion_logs(self, caplog):
        """Should log error with duration on failure."""
        with caplog.at_level(logging.WARNING, logger="md_server.mcp.server"):
            with pytest.raises(ToolError):
                await convert_to_markdown()

        log_text = caplog.text
        assert "convert_to_markdown" in log_text


@pytest.mark.unit
class TestTruncation:
    """Tests for truncation parameters through the MCP tool function."""

    @pytest.mark.asyncio
    async def test_max_tokens_passed_to_converter(self):
        """max_tokens should be passed through to the converter."""
        with patch("md_server.mcp.server.get_converter") as mock_get:
            mock_conv = MagicMock()
            mock_conv.timeout = 60
            mock_conv.convert_url = AsyncMock(
                return_value=MagicMock(
                    markdown="# Truncated content with five words here",
                    metadata=MagicMock(
                        title="Page",
                        detected_language="en",
                        was_truncated=True,
                        original_length=5000,
                        original_tokens=1000,
                        truncation_mode="tokens",
                    ),
                )
            )
            mock_get.return_value = mock_conv

            result = await convert_to_markdown(
                url="https://example.com",
                max_tokens=100,
                output_format="json",
            )

            data = json.loads(result)
            assert data["success"] is True
            assert data["metadata"]["was_truncated"] is True
            assert data["metadata"]["truncation_mode"] == "tokens"

    @pytest.mark.asyncio
    async def test_truncate_limit_passed_to_converter(self):
        """truncate_limit and truncate_mode should be passed through."""
        with patch("md_server.mcp.server.get_converter") as mock_get:
            mock_conv = MagicMock()
            mock_conv.timeout = 60
            mock_conv.convert_url = AsyncMock(
                return_value=MagicMock(
                    markdown="# Section content with five words here",
                    metadata=MagicMock(title="Page", detected_language="en"),
                )
            )
            mock_get.return_value = mock_conv

            await convert_to_markdown(
                url="https://example.com",
                truncate_mode="sections",
                truncate_limit=3,
            )

            call_kwargs = mock_conv.convert_url.call_args.kwargs
            assert call_kwargs["truncate_mode"] == "sections"
            assert call_kwargs["truncate_limit"] == 3
