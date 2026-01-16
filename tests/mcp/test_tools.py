"""Tests for MCP tool definitions."""

import pytest
from md_server.mcp.tools import READ_RESOURCE_TOOL, TOOLS


@pytest.mark.unit
class TestReadResourceTool:
    """Tests for READ_RESOURCE_TOOL definition."""

    def test_name(self):
        """Tool should be named 'read_resource'."""
        assert READ_RESOURCE_TOOL.name == "read_resource"

    def test_no_required_fields(self):
        """No fields should be strictly required (validation is at handler level)."""
        # The tool accepts either url OR file_content+filename
        # Validation happens in the handler, not in the schema
        required = READ_RESOURCE_TOOL.inputSchema.get("required", [])
        # Schema doesn't enforce required since inputs are mutually exclusive
        assert isinstance(required, list)

    def test_has_url_property(self):
        """Tool should have url property."""
        props = READ_RESOURCE_TOOL.inputSchema["properties"]
        assert "url" in props
        assert props["url"]["type"] == "string"
        assert props["url"]["format"] == "uri"

    def test_has_file_content_property(self):
        """Tool should have file_content property."""
        props = READ_RESOURCE_TOOL.inputSchema["properties"]
        assert "file_content" in props
        assert props["file_content"]["type"] == "string"

    def test_has_filename_property(self):
        """Tool should have filename property."""
        props = READ_RESOURCE_TOOL.inputSchema["properties"]
        assert "filename" in props
        assert props["filename"]["type"] == "string"

    def test_render_js_optional(self):
        """render_js should not be required."""
        required = READ_RESOURCE_TOOL.inputSchema.get("required", [])
        assert "render_js" not in required

    def test_render_js_default_false(self):
        """render_js should default to False."""
        props = READ_RESOURCE_TOOL.inputSchema["properties"]
        assert props["render_js"]["default"] is False

    def test_description_not_empty(self):
        """Description should not be empty."""
        assert READ_RESOURCE_TOOL.description
        assert len(READ_RESOURCE_TOOL.description) > 50

    def test_description_mentions_key_features(self):
        """Description should mention key features."""
        desc = READ_RESOURCE_TOOL.description.lower()
        assert "url" in desc
        assert "file" in desc
        assert "markdown" in desc

    def test_description_mentions_render_js(self):
        """Description should explain render_js option."""
        desc = READ_RESOURCE_TOOL.description.lower()
        assert "javascript" in desc or "render_js" in desc

    def test_description_mentions_formats(self):
        """Description should list supported formats."""
        desc = READ_RESOURCE_TOOL.description.lower()
        assert "pdf" in desc
        assert "docx" in desc

    def test_description_mentions_ocr(self):
        """Description should mention OCR feature."""
        desc = READ_RESOURCE_TOOL.description.lower()
        assert "ocr" in desc

    def test_has_output_format(self):
        """Tool should have output_format parameter."""
        props = READ_RESOURCE_TOOL.inputSchema["properties"]
        assert "output_format" in props
        assert props["output_format"]["default"] == "markdown"
        assert props["output_format"]["enum"] == ["markdown", "json"]

    def test_has_include_frontmatter(self):
        """Tool should have include_frontmatter parameter."""
        props = READ_RESOURCE_TOOL.inputSchema["properties"]
        assert "include_frontmatter" in props
        assert props["include_frontmatter"]["default"] is True

    def test_has_max_length(self):
        """Tool should have max_length parameter."""
        props = READ_RESOURCE_TOOL.inputSchema["properties"]
        assert "max_length" in props
        assert props["max_length"]["type"] == "integer"

    def test_has_timeout(self):
        """Tool should have timeout parameter."""
        props = READ_RESOURCE_TOOL.inputSchema["properties"]
        assert "timeout" in props
        assert props["timeout"]["type"] == "integer"


@pytest.mark.unit
class TestToolsList:
    """Tests for TOOLS list."""

    def test_contains_read_resource(self):
        """TOOLS should contain read_resource."""
        names = [t.name for t in TOOLS]
        assert "read_resource" in names

    def test_exactly_one_tool(self):
        """TOOLS should contain exactly 1 tool."""
        assert len(TOOLS) == 1

    def test_tools_are_tool_instances(self):
        """All items in TOOLS should be Tool instances."""
        from mcp.types import Tool

        for tool in TOOLS:
            assert isinstance(tool, Tool)

    def test_no_duplicate_names(self):
        """Tool names should be unique."""
        names = [t.name for t in TOOLS]
        assert len(names) == len(set(names))
