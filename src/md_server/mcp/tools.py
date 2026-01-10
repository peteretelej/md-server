"""MCP tool definitions for md-server."""

from mcp.types import Tool

READ_URL_TOOL = Tool(
    name="read_url",
    description="""Fetch and read content from a URL, returning clean markdown.

Use this to read:
- Articles, blog posts, news, documentation
- Online PDFs and Google Docs (public)
- Dynamic web apps (set render_js: true)

Returns structured JSON with:
- title: Page title
- content: Markdown text
- word_count: Content length
- metadata: Author, date, description

For JavaScript-heavy pages (SPAs, dashboards), enable render_js.
This adds ~15-30 seconds but captures dynamically loaded content.""",
    inputSchema={
        "type": "object",
        "required": ["url"],
        "properties": {
            "url": {
                "type": "string",
                "format": "uri",
                "description": "URL to fetch (webpage, PDF link, document URL)",
            },
            "render_js": {
                "type": "boolean",
                "default": False,
                "description": (
                    "Execute JavaScript before reading. "
                    "Enable for SPAs and pages that load content dynamically. "
                    "Slower but more complete."
                ),
            },
        },
    },
)

READ_FILE_TOOL = Tool(
    name="read_file",
    description="""Read and extract content from a document file, returning clean markdown.

Supported formats:
- Documents: PDF, DOCX, DOC, RTF, ODT
- Spreadsheets: XLSX, XLS, CSV
- Presentations: PPTX, PPT, ODP
- Images: PNG, JPG, GIF, WebP, TIFF (auto-OCR)
- Web: HTML, XML
- Text: TXT, MD, JSON

Images automatically use OCR to extract visible text - no extra parameters needed.

Returns structured JSON with:
- title: Document title or filename
- content: Extracted markdown
- word_count: Content length
- metadata: Author, dates, page count""",
    inputSchema={
        "type": "object",
        "required": ["content", "filename"],
        "properties": {
            "content": {
                "type": "string",
                "description": "Base64-encoded file data",
            },
            "filename": {
                "type": "string",
                "description": (
                    "Filename with extension (e.g., 'report.pdf', 'chart.png'). "
                    "Used to determine processing method."
                ),
            },
        },
    },
)

# Export list of all tools
TOOLS = [READ_URL_TOOL, READ_FILE_TOOL]
