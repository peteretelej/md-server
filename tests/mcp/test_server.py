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
    async def test_read_url_success(self):
        """read_url should return JSON response on success."""
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

            result = await call_tool("read_url", {"url": "https://example.com"})

            assert len(result) == 1
            assert result[0].type == "text"
            data = json.loads(result[0].text)
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_read_file_success(self):
        """read_file should return JSON response on success."""
        with patch("md_server.mcp.server.get_converter") as mock_get:
            mock_metadata = MagicMock()
            mock_metadata.title = "Doc"
            mock_metadata.detected_language = "en"
            mock_metadata.detected_format = "application/pdf"
            mock_metadata.get = MagicMock(return_value=None)

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
            result = await call_tool(
                "read_file", {"content": content, "filename": "test.pdf"}
            )

            assert len(result) == 1
            data = json.loads(result[0].text)
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self):
        """Unknown tool should return error response, not raise."""
        result = await call_tool("unknown_tool", {})

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "UNKNOWN_TOOL"

    @pytest.mark.asyncio
    async def test_missing_url_returns_error(self):
        """read_url without url should return error."""
        result = await call_tool("read_url", {})

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_missing_content_returns_error(self):
        """read_file without content should return error."""
        result = await call_tool("read_file", {"filename": "test.pdf"})

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_invalid_base64_returns_error(self):
        """read_file with invalid base64 should return error."""
        result = await call_tool(
            "read_file", {"content": "not-valid-base64!!!", "filename": "test.pdf"}
        )

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"


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
