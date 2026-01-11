"""Tests for MCP server functionality."""

import base64
import json
import pytest
from unittest.mock import patch, Mock, AsyncMock, MagicMock

from md_server.mcp.server import call_tool, list_tools, get_converter


@pytest.mark.unit
class TestMCPServer:
    """Test MCP server functionality."""

    @pytest.mark.asyncio
    async def test_list_tools_returns_two(self):
        """list_tools should return read_url and read_file tools."""
        tools = await list_tools()
        assert len(tools) == 2
        names = [t.name for t in tools]
        assert "read_url" in names
        assert "read_file" in names

    @pytest.mark.asyncio
    async def test_list_tools_have_output_format(self):
        """Tools should have output_format parameter."""
        tools = await list_tools()
        for tool in tools:
            props = tool.inputSchema.get("properties", {})
            assert "output_format" in props
            assert props["output_format"]["default"] == "markdown"
            assert props["output_format"]["enum"] == ["markdown", "json"]

    @pytest.mark.asyncio
    async def test_list_tools_have_new_options(self):
        """Tools should have max_length, timeout, include_frontmatter parameters."""
        tools = await list_tools()
        for tool in tools:
            props = tool.inputSchema.get("properties", {})
            assert "max_length" in props, f"{tool.name} missing max_length"
            assert "timeout" in props, f"{tool.name} missing timeout"
            assert "include_frontmatter" in props, (
                f"{tool.name} missing include_frontmatter"
            )
            assert props["include_frontmatter"]["default"] is True

    # --- Output Format Tests (consolidated) ---

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
    async def test_read_url_output_format(self, output_format, is_json):
        """read_url should return correct format based on output_format."""
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

            args = {"url": "https://example.com"}
            if output_format is not None:
                args["output_format"] = output_format

            result = await call_tool("read_url", args)

            assert len(result) == 1
            assert result[0].type == "text"
            if is_json:
                data = json.loads(result[0].text)
                assert data["success"] is True
            else:
                assert result[0].text.startswith("# Hello World")

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
    async def test_read_file_output_format(self, output_format, is_json):
        """read_file should return correct format based on output_format."""
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
            args = {"content": content, "filename": "test.pdf"}
            if output_format is not None:
                args["output_format"] = output_format

            result = await call_tool("read_file", args)

            assert len(result) == 1
            if is_json:
                data = json.loads(result[0].text)
                assert data["success"] is True
            else:
                assert result[0].text.startswith("# Markdown Content")

    # --- Parameter Passing Tests ---

    @pytest.mark.asyncio
    async def test_read_url_passes_new_options(self):
        """read_url should pass max_length, timeout, include_frontmatter to handler."""
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

            await call_tool(
                "read_url",
                {
                    "url": "https://example.com",
                    "max_length": 100,
                    "timeout": 30,
                    "include_frontmatter": False,
                },
            )

            mock_conv.convert_url.assert_called_once()
            call_kwargs = mock_conv.convert_url.call_args.kwargs
            assert call_kwargs["max_length"] == 100
            assert call_kwargs["timeout"] == 30
            assert call_kwargs["include_frontmatter"] is False

    @pytest.mark.asyncio
    async def test_read_file_passes_new_options(self):
        """read_file should pass max_length, timeout, include_frontmatter to handler."""
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
            await call_tool(
                "read_file",
                {
                    "content": content,
                    "filename": "test.pdf",
                    "max_length": 200,
                    "timeout": 45,
                    "include_frontmatter": False,
                },
            )

            mock_conv.convert_content.assert_called_once()
            call_kwargs = mock_conv.convert_content.call_args.kwargs
            assert call_kwargs["max_length"] == 200
            assert call_kwargs["timeout"] == 45
            assert call_kwargs["include_frontmatter"] is False

    # --- Error Handling Tests (consolidated) ---

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "tool_name,args,expected_code",
        [
            ("read_url", {}, "INVALID_INPUT"),  # missing url
            ("read_url", {"output_format": "markdown"}, "INVALID_INPUT"),  # missing url
            ("read_file", {"filename": "test.pdf"}, "INVALID_INPUT"),  # missing content
            (
                "read_file",
                {"content": base64.b64encode(b"data").decode()},
                "INVALID_INPUT",
            ),  # missing filename
            (
                "read_file",
                {"content": "not-valid-base64!!!", "filename": "test.pdf"},
                "INVALID_INPUT",
            ),  # invalid base64
            ("unknown_tool", {}, "UNKNOWN_TOOL"),
        ],
        ids=[
            "missing_url",
            "missing_url_with_format",
            "missing_content",
            "missing_filename",
            "invalid_base64",
            "unknown_tool",
        ],
    )
    async def test_error_responses(self, tool_name, args, expected_code):
        """Should return correct error code for invalid inputs."""
        result = await call_tool(tool_name, args)

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == expected_code

    @pytest.mark.asyncio
    async def test_unknown_tool_suggests_alternatives(self):
        """Unknown tool error should suggest available tools."""
        result = await call_tool("unknown_tool", {})

        data = json.loads(result[0].text)
        assert "read_url" in str(data["error"]["suggestions"])
        assert "read_file" in str(data["error"]["suggestions"])


@pytest.mark.unit
class TestMCPTransports:
    """Test MCP transport initialization and configuration."""

    def test_run_sse_creates_correct_routes(self):
        """Verify SSE server has correct route configuration."""
        import sys

        mock_uvicorn = Mock()
        with patch.dict(sys.modules, {"uvicorn": mock_uvicorn}):
            import importlib
            import md_server.mcp.server as server_module

            importlib.reload(server_module)

            server_module.run_sse(host="127.0.0.1", port=9999)

            mock_uvicorn.run.assert_called_once()
            app = mock_uvicorn.run.call_args[0][0]
            route_paths = []
            for r in app.routes:
                if hasattr(r, "path"):
                    route_paths.append(r.path)
            assert "/health" in route_paths
            assert "/sse" in route_paths

    def test_run_sse_passes_host_port(self):
        """Verify host and port are passed to uvicorn."""
        import sys

        mock_uvicorn = Mock()
        with patch.dict(sys.modules, {"uvicorn": mock_uvicorn}):
            import importlib
            import md_server.mcp.server as server_module

            importlib.reload(server_module)

            server_module.run_sse(host="0.0.0.0", port=8080)

            call_kwargs = mock_uvicorn.run.call_args[1]
            assert call_kwargs["host"] == "0.0.0.0"
            assert call_kwargs["port"] == 8080

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

    @pytest.mark.asyncio
    async def test_sse_health_endpoint_response(self):
        """Verify health endpoint returns correct response format."""
        from starlette.responses import JSONResponse

        async def health(request):
            return JSONResponse({"status": "healthy", "mode": "mcp-sse"})

        response = await health(Mock())
        assert response.status_code == 200
        assert b"healthy" in response.body
        assert b"mcp-sse" in response.body
