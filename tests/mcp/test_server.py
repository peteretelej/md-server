"""Tests for MCP server functionality."""

import base64
import json
import pytest
from unittest.mock import patch, Mock, AsyncMock, MagicMock

from md_server.mcp.server import convert_to_markdown, get_converter, mcp


def _get_tool():
    """Get the convert_to_markdown tool from FastMCP."""
    tools = mcp._tool_manager.list_tools()
    return next(t for t in tools if t.name == "convert_to_markdown")


@pytest.mark.unit
class TestMCPServer:
    """Test MCP server functionality."""

    def test_tool_is_registered(self):
        """convert_to_markdown should be registered as a tool."""
        tools = mcp._tool_manager.list_tools()
        names = [t.name for t in tools]
        assert "convert_to_markdown" in names

    def test_tool_has_no_output_schema(self):
        """Tool should not have an output schema (avoids Claude Code bug)."""
        tool = _get_tool()
        assert tool.output_schema is None

    def test_tool_has_readonly_annotation(self):
        """Tool should have readOnlyHint annotation."""
        tool = _get_tool()
        assert tool.annotations is not None
        assert tool.annotations.readOnlyHint is True

    def test_tool_has_expected_parameters(self):
        """Tool should have all expected input parameters."""
        tool = _get_tool()
        props = tool.parameters.get("properties", {})
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

    def test_tool_has_output_format_default(self):
        """Tool should have output_format with default 'markdown'."""
        tool = _get_tool()
        props = tool.parameters.get("properties", {})
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
