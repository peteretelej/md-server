"""MCP tool definitions for md-server."""

from mcp.types import Tool

READ_RESOURCE_TOOL = Tool(
    name="read_resource",
    description="""Read a URL or file and convert to markdown.

Provide ONE of:
- url: Webpage, online PDF, or Google Doc
- file_content + filename: Base64-encoded file

Supported formats: PDF, DOCX, XLSX, PPTX, HTML, images (OCR), and more.

For JavaScript-heavy pages (SPAs, dashboards), set render_js: true.
This adds ~15-30 seconds but captures dynamically loaded content.

Returns markdown by default, or structured JSON with metadata (set output_format: "json").""",
    inputSchema={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "format": "uri",
                "description": "URL to fetch (webpage, PDF link, document URL)",
            },
            "file_content": {
                "type": "string",
                "description": "Base64-encoded file data",
            },
            "filename": {
                "type": "string",
                "description": (
                    "Filename with extension (e.g., 'report.pdf', 'chart.png'). "
                    "Required with file_content."
                ),
            },
            "render_js": {
                "type": "boolean",
                "default": False,
                "description": (
                    "Execute JavaScript before reading (URLs only). "
                    "Enable for SPAs and pages that load content dynamically."
                ),
            },
            "max_length": {
                "type": "integer",
                "description": "Maximum characters to return. Content is truncated if exceeded.",
            },
            "max_tokens": {
                "type": "integer",
                "description": "Maximum tokens to return (uses tiktoken cl100k_base encoding).",
            },
            "truncate_mode": {
                "type": "string",
                "enum": ["chars", "tokens", "sections", "paragraphs"],
                "description": (
                    "Truncation mode: chars (character limit), tokens (token limit), "
                    "sections (first N ## headings), paragraphs (first N paragraphs)."
                ),
            },
            "truncate_limit": {
                "type": "integer",
                "description": (
                    "Limit for truncation mode (character count, token count, "
                    "section count, or paragraph count)."
                ),
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds for the conversion operation.",
            },
            "include_frontmatter": {
                "type": "boolean",
                "default": True,
                "description": "Include YAML frontmatter with metadata (title, description, etc.)",
            },
            "output_format": {
                "type": "string",
                "enum": ["markdown", "json"],
                "default": "markdown",
                "description": (
                    "Output format: markdown (default) returns raw markdown, "
                    "json returns structured response with metadata."
                ),
            },
        },
    },
)

# Export list of all tools
TOOLS = [READ_RESOURCE_TOOL]
