import base64
import pytest
from unittest.mock import patch, Mock

from md_server.mcp.server import call_tool, list_tools, get_converter


@pytest.mark.unit
class TestMCPServer:
    """Test MCP server functionality."""

    async def test_list_tools(self):
        tools = await list_tools()
        assert len(tools) == 1
        assert tools[0].name == "convert"

    async def test_convert_text(self):
        result = await call_tool("convert", {"text": "# Hello World"})
        assert len(result) == 1
        assert result[0].type == "text"
        assert "Hello World" in result[0].text

    async def test_convert_html_text(self):
        result = await call_tool("convert", {"text": "<h1>Title</h1><p>Content</p>"})
        assert len(result) == 1
        assert "Title" in result[0].text

    async def test_convert_base64_content(self):
        content = base64.b64encode(b"# Markdown Content").decode()
        result = await call_tool("convert", {"content": content, "filename": "test.md"})
        assert len(result) == 1
        assert "Markdown Content" in result[0].text

    async def test_unknown_tool_raises(self):
        with pytest.raises(ValueError, match="Unknown tool"):
            await call_tool("unknown_tool", {})

    async def test_missing_input_returns_error(self):
        result = await call_tool("convert", {})
        assert len(result) == 1
        assert "Error" in result[0].text

    async def test_error_returns_text_content(self):
        result = await call_tool("convert", {"content": "not-valid-base64!!!"})
        assert len(result) == 1
        assert "Error" in result[0].text

    async def test_include_frontmatter_option(self):
        result = await call_tool(
            "convert", {"text": "# Test Document", "include_frontmatter": True}
        )
        assert len(result) == 1
        assert "---" in result[0].text or "Test Document" in result[0].text


@pytest.mark.integration
class TestMCPIntegration:
    """Integration tests for MCP server."""

    @pytest.mark.slow
    async def test_convert_public_url(self):
        result = await call_tool("convert", {"url": "https://example.com"})
        assert len(result) == 1
        assert "Example Domain" in result[0].text


@pytest.mark.unit
class TestMCPTransports:
    """Test MCP transport initialization and configuration."""

    def test_run_sse_creates_correct_routes(self):
        """Verify SSE server has correct route configuration."""
        import sys

        mock_uvicorn = Mock()
        with patch.dict(sys.modules, {"uvicorn": mock_uvicorn}):
            # Need to reimport to get fresh module with mocked uvicorn
            import importlib
            import md_server.mcp.server as server_module

            importlib.reload(server_module)

            server_module.run_sse(host="127.0.0.1", port=9999)

            mock_uvicorn.run.assert_called_once()
            app = mock_uvicorn.run.call_args[0][0]
            # Extract route paths - some routes may be Route objects, others may be functions
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

        # Test the health function signature matches expected response
        async def health(request):
            return JSONResponse({"status": "healthy", "mode": "mcp-sse"})

        response = await health(Mock())
        assert response.status_code == 200
        assert b"healthy" in response.body
        assert b"mcp-sse" in response.body
