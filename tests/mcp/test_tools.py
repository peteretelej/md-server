import pytest
from md_server.mcp.tools import CONVERT_TOOL


@pytest.mark.unit
class TestMCPToolDefinition:
    """Test MCP tool schema."""

    def test_tool_name(self):
        assert CONVERT_TOOL.name == "convert"

    def test_tool_has_description(self):
        assert len(CONVERT_TOOL.description) > 50

    def test_schema_has_url_property(self):
        props = CONVERT_TOOL.inputSchema["properties"]
        assert "url" in props
        assert props["url"]["type"] == "string"

    def test_schema_has_content_property(self):
        props = CONVERT_TOOL.inputSchema["properties"]
        assert "content" in props
        assert props["content"]["type"] == "string"

    def test_schema_has_text_property(self):
        props = CONVERT_TOOL.inputSchema["properties"]
        assert "text" in props
        assert props["text"]["type"] == "string"

    def test_schema_has_filename_property(self):
        props = CONVERT_TOOL.inputSchema["properties"]
        assert "filename" in props

    def test_schema_has_js_rendering_property(self):
        props = CONVERT_TOOL.inputSchema["properties"]
        assert "js_rendering" in props
        assert props["js_rendering"]["type"] == "boolean"

    def test_schema_has_include_frontmatter_property(self):
        props = CONVERT_TOOL.inputSchema["properties"]
        assert "include_frontmatter" in props
        assert props["include_frontmatter"]["type"] == "boolean"

    def test_schema_requires_one_input(self):
        assert "oneOf" in CONVERT_TOOL.inputSchema
        one_of = CONVERT_TOOL.inputSchema["oneOf"]
        assert len(one_of) == 3
        required_fields = [item["required"][0] for item in one_of]
        assert set(required_fields) == {"url", "content", "text"}
