"""Integration tests for MCP server."""

import pytest
import json
import base64
from unittest.mock import patch, AsyncMock, MagicMock

from mcp.server.fastmcp.exceptions import ToolError


@pytest.mark.unit
class TestMCPServerIntegration:
    """Integration tests for MCP server tool calls."""

    def test_tool_is_registered(self):
        """Tool listing should include convert_to_markdown."""
        from md_server.mcp.server import mcp

        tools = mcp._tool_manager.list_tools()
        names = [t.name for t in tools]

        assert "convert_to_markdown" in names
        assert len(tools) == 1

    @pytest.mark.asyncio
    async def test_convert_url_success(self):
        """convert_to_markdown should handle url successfully."""
        from md_server.mcp.server import convert_to_markdown

        with patch("md_server.mcp.server.get_converter") as mock_get:
            mock_conv = MagicMock()
            mock_conv.timeout = 60
            mock_metadata = MagicMock(
                title="Test Page",
                detected_language="en",
                was_truncated=False,
                original_length=None,
                original_tokens=None,
                truncation_mode=None,
            )
            mock_conv.convert_url = AsyncMock(
                return_value=MagicMock(
                    markdown="# Test content with more than five words here",
                    metadata=mock_metadata,
                )
            )
            mock_get.return_value = mock_conv

            result = await convert_to_markdown(
                url="https://example.com", output_format="json"
            )

            data = json.loads(result)
            assert data["success"] is True
            assert data["title"] == "Test Page"

    @pytest.mark.asyncio
    async def test_convert_with_render_js(self):
        """convert_to_markdown should pass render_js to handler."""
        from md_server.mcp.server import convert_to_markdown

        with patch("md_server.mcp.server.get_converter") as mock_get:
            mock_conv = MagicMock()
            mock_conv.timeout = 60
            mock_conv.convert_url = AsyncMock(
                return_value=MagicMock(
                    markdown="# Content with more than five words here today",
                    metadata=MagicMock(title="Page", detected_language=None),
                )
            )
            mock_get.return_value = mock_conv

            await convert_to_markdown(url="https://example.com", render_js=True)

            call_kwargs = mock_conv.convert_url.call_args.kwargs
            assert call_kwargs["js_rendering"] is True

    @pytest.mark.asyncio
    async def test_convert_file_success(self):
        """convert_to_markdown should handle file_content successfully."""
        from md_server.mcp.server import convert_to_markdown

        with patch("md_server.mcp.server.get_converter") as mock_get:
            mock_conv = MagicMock()
            mock_conv.timeout = 60
            mock_conv.max_file_size_mb = 50
            mock_metadata = MagicMock(
                title="Document",
                detected_language=None,
                detected_format="application/pdf",
                was_truncated=False,
                original_length=None,
                original_tokens=None,
                truncation_mode=None,
            )
            mock_conv.convert_content = AsyncMock(
                return_value=MagicMock(
                    markdown="# PDF Content with enough words here",
                    metadata=mock_metadata,
                )
            )
            mock_get.return_value = mock_conv

            content_b64 = base64.b64encode(b"fake pdf data").decode()
            result = await convert_to_markdown(
                file_content=content_b64,
                filename="test.pdf",
                output_format="json",
            )

            data = json.loads(result)
            assert data["success"] is True
            assert data["source"] == "test.pdf"

    # --- Input Validation Error Tests ---

    @pytest.mark.asyncio
    async def test_error_missing_input(self):
        """Should raise ToolError when no input provided."""
        from md_server.mcp.server import convert_to_markdown

        with pytest.raises(ToolError):
            await convert_to_markdown()

    @pytest.mark.asyncio
    async def test_error_missing_filename(self):
        """Should raise ToolError when file_content without filename."""
        from md_server.mcp.server import convert_to_markdown

        content = base64.b64encode(b"data").decode()
        with pytest.raises(ToolError):
            await convert_to_markdown(file_content=content)

    @pytest.mark.asyncio
    async def test_error_both_inputs(self):
        """Should raise ToolError when both url and file_content provided."""
        from md_server.mcp.server import convert_to_markdown

        content = base64.b64encode(b"data").decode()
        with pytest.raises(ToolError):
            await convert_to_markdown(
                url="https://example.com",
                file_content=content,
                filename="test.pdf",
            )

    @pytest.mark.asyncio
    async def test_error_invalid_base64(self):
        """Should raise ToolError for invalid base64."""
        from md_server.mcp.server import convert_to_markdown

        with pytest.raises(ToolError, match="base64"):
            await convert_to_markdown(
                file_content="not-valid-base64!!!",
                filename="test.pdf",
            )

    @pytest.mark.asyncio
    async def test_unknown_tool_error_suggests_convert(self):
        """Unknown tool error should suggest convert_to_markdown."""
        from md_server.mcp.errors import unknown_tool_error

        result = unknown_tool_error("bad_tool")
        assert "convert_to_markdown" in str(result.error.suggestions)


@pytest.mark.unit
class TestMCPResponseFormat:
    """Tests for MCP response format consistency."""

    @pytest.mark.asyncio
    async def test_success_response_structure(self):
        """Success responses (JSON format) should have consistent structure."""
        from md_server.mcp.server import convert_to_markdown

        with patch("md_server.mcp.server.get_converter") as mock_get:
            mock_conv = MagicMock()
            mock_conv.timeout = 60
            mock_metadata = MagicMock(
                title="Title",
                detected_language="en",
                was_truncated=False,
                original_length=None,
                original_tokens=None,
                truncation_mode=None,
            )
            mock_conv.convert_url = AsyncMock(
                return_value=MagicMock(
                    markdown="# Content with more than five words today",
                    metadata=mock_metadata,
                )
            )
            mock_get.return_value = mock_conv

            result = await convert_to_markdown(
                url="https://example.com", output_format="json"
            )

            data = json.loads(result)
            # Check required fields
            assert "success" in data
            assert "title" in data
            assert "markdown" in data
            assert "source" in data
            assert "word_count" in data
            assert "metadata" in data

    @pytest.mark.asyncio
    async def test_error_raises_tool_error(self):
        """Errors should raise ToolError (not return JSON error response)."""
        from md_server.mcp.server import convert_to_markdown

        with pytest.raises(ToolError):
            await convert_to_markdown()
