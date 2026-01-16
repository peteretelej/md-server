"""Integration tests for MCP server."""

import pytest
import json
import base64
from unittest.mock import patch, AsyncMock, MagicMock


@pytest.mark.unit
class TestMCPServerIntegration:
    """Integration tests for MCP server tool calls."""

    @pytest.mark.asyncio
    async def test_list_tools_returns_read_resource(self):
        """list_tools should return read_resource tool."""
        from md_server.mcp.server import list_tools

        tools = await list_tools()
        names = [t.name for t in tools]

        assert "read_resource" in names
        assert len(tools) == 1

    @pytest.mark.asyncio
    async def test_call_read_resource_url_success(self):
        """call_tool should handle read_resource with url successfully."""
        from md_server.mcp.server import call_tool

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

            result = await call_tool(
                "read_resource",
                {"url": "https://example.com", "output_format": "json"},
            )

            assert len(result) == 1
            data = json.loads(result[0].text)
            assert data["success"] is True
            assert data["title"] == "Test Page"

    @pytest.mark.asyncio
    async def test_call_read_resource_with_render_js(self):
        """call_tool should pass render_js to handler."""
        from md_server.mcp.server import call_tool

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

            await call_tool(
                "read_resource", {"url": "https://example.com", "render_js": True}
            )

            call_kwargs = mock_conv.convert_url.call_args.kwargs
            assert call_kwargs["js_rendering"] is True

    @pytest.mark.asyncio
    async def test_call_read_resource_file_success(self):
        """call_tool should handle read_resource with file_content successfully."""
        from md_server.mcp.server import call_tool

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
            result = await call_tool(
                "read_resource",
                {
                    "file_content": content_b64,
                    "filename": "test.pdf",
                    "output_format": "json",
                },
            )

            data = json.loads(result[0].text)
            assert data["success"] is True
            assert data["source"] == "test.pdf"

    # --- Input Validation Error Tests (consolidated) ---

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "args,test_id",
        [
            ({}, "missing_both"),  # neither url nor file_content
            (
                {"file_content": base64.b64encode(b"data").decode()},
                "missing_filename",
            ),  # missing filename
            (
                {
                    "url": "https://example.com",
                    "file_content": base64.b64encode(b"data").decode(),
                    "filename": "test.pdf",
                },
                "both_url_and_file",
            ),  # both url and file_content
            (
                {"file_content": "not-valid-base64!!!", "filename": "test.pdf"},
                "invalid_base64",
            ),  # invalid base64
        ],
        ids=["missing_both", "missing_filename", "both_url_and_file", "invalid_base64"],
    )
    async def test_invalid_input_returns_error(self, args, test_id):
        """call_tool should return error for invalid inputs."""
        from md_server.mcp.server import call_tool

        result = await call_tool("read_resource", args)

        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_call_unknown_tool(self):
        """call_tool should return error for unknown tool."""
        from md_server.mcp.server import call_tool

        result = await call_tool("unknown_tool", {})

        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "UNKNOWN_TOOL"
        assert "read_resource" in str(data["error"]["suggestions"])

    @pytest.mark.asyncio
    async def test_response_is_json_string(self):
        """call_tool should return JSON string in TextContent."""
        from md_server.mcp.server import call_tool

        result = await call_tool("unknown_tool", {})

        assert len(result) == 1
        assert result[0].type == "text"
        # Should be valid JSON
        data = json.loads(result[0].text)
        assert isinstance(data, dict)


@pytest.mark.unit
class TestMCPResponseFormat:
    """Tests for MCP response format consistency."""

    @pytest.mark.asyncio
    async def test_success_response_structure(self):
        """Success responses (JSON format) should have consistent structure."""
        from md_server.mcp.server import call_tool

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

            result = await call_tool(
                "read_resource",
                {"url": "https://example.com", "output_format": "json"},
            )

            data = json.loads(result[0].text)
            # Check required fields
            assert "success" in data
            assert "title" in data
            assert "markdown" in data
            assert "source" in data
            assert "word_count" in data
            assert "metadata" in data

    @pytest.mark.asyncio
    async def test_error_response_structure(self):
        """Error responses should have consistent structure."""
        from md_server.mcp.server import call_tool

        result = await call_tool("unknown_tool", {})

        data = json.loads(result[0].text)
        # Check required fields
        assert "success" in data
        assert data["success"] is False
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert "suggestions" in data["error"]
