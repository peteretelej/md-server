"""Tests for MCP tool definitions."""

import pytest
from md_server.mcp.tools import READ_URL_TOOL, READ_FILE_TOOL, TOOLS


@pytest.mark.unit
class TestReadUrlTool:
    """Tests for READ_URL_TOOL definition."""

    def test_name(self):
        """Tool should be named 'read_url'."""
        assert READ_URL_TOOL.name == "read_url"

    def test_url_required(self):
        """URL should be a required parameter."""
        assert "url" in READ_URL_TOOL.inputSchema["required"]

    def test_render_js_optional(self):
        """render_js should not be required."""
        required = READ_URL_TOOL.inputSchema.get("required", [])
        assert "render_js" not in required

    def test_render_js_default_false(self):
        """render_js should default to False."""
        props = READ_URL_TOOL.inputSchema["properties"]
        assert props["render_js"]["default"] is False

    def test_url_has_format(self):
        """URL property should have uri format."""
        props = READ_URL_TOOL.inputSchema["properties"]
        assert props["url"]["format"] == "uri"

    def test_description_not_empty(self):
        """Description should not be empty."""
        assert READ_URL_TOOL.description
        assert len(READ_URL_TOOL.description) > 50

    def test_description_mentions_key_features(self):
        """Description should mention key features."""
        desc = READ_URL_TOOL.description.lower()
        assert "url" in desc
        assert "markdown" in desc
        assert "json" in desc

    def test_description_mentions_render_js(self):
        """Description should explain render_js option."""
        desc = READ_URL_TOOL.description.lower()
        assert "javascript" in desc or "render_js" in desc


@pytest.mark.unit
class TestReadFileTool:
    """Tests for READ_FILE_TOOL definition."""

    def test_name(self):
        """Tool should be named 'read_file'."""
        assert READ_FILE_TOOL.name == "read_file"

    def test_content_required(self):
        """content should be a required parameter."""
        assert "content" in READ_FILE_TOOL.inputSchema["required"]

    def test_filename_required(self):
        """filename should be a required parameter."""
        assert "filename" in READ_FILE_TOOL.inputSchema["required"]

    def test_description_not_empty(self):
        """Description should not be empty."""
        assert READ_FILE_TOOL.description
        assert len(READ_FILE_TOOL.description) > 50

    def test_description_mentions_formats(self):
        """Description should list supported formats."""
        desc = READ_FILE_TOOL.description.lower()
        assert "pdf" in desc
        assert "docx" in desc

    def test_description_mentions_ocr(self):
        """Description should mention OCR feature."""
        desc = READ_FILE_TOOL.description.lower()
        assert "ocr" in desc

    def test_description_mentions_images(self):
        """Description should mention image support."""
        desc = READ_FILE_TOOL.description.lower()
        assert "png" in desc or "jpg" in desc or "image" in desc


@pytest.mark.unit
class TestToolsList:
    """Tests for TOOLS list."""

    def test_contains_both_tools(self):
        """TOOLS should contain both read_url and read_file."""
        names = [t.name for t in TOOLS]
        assert "read_url" in names
        assert "read_file" in names

    def test_exactly_two_tools(self):
        """TOOLS should contain exactly 2 tools."""
        assert len(TOOLS) == 2

    def test_tools_are_tool_instances(self):
        """All items in TOOLS should be Tool instances."""
        from mcp.types import Tool

        for tool in TOOLS:
            assert isinstance(tool, Tool)

    def test_no_duplicate_names(self):
        """Tool names should be unique."""
        names = [t.name for t in TOOLS]
        assert len(names) == len(set(names))
