import base64
import pytest
from md_server.mcp.server import call_tool, list_tools


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
