from mcp.types import Tool

CONVERT_TOOL = Tool(
    name="convert",
    description=(
        "Convert a document, URL, or text to Markdown. "
        "Supports PDF, DOCX, XLSX, PPTX, HTML, images, and more. "
        "Use for reading web pages, documents, or any content that needs text extraction."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL to fetch and convert (e.g., https://example.com/page.html)",
            },
            "content": {
                "type": "string",
                "description": "Base64-encoded file content (for binary files like PDF, DOCX)",
            },
            "text": {
                "type": "string",
                "description": "Raw text or HTML to convert",
            },
            "filename": {
                "type": "string",
                "description": "Filename hint for format detection (e.g., 'document.pdf')",
            },
            "js_rendering": {
                "type": "boolean",
                "default": False,
                "description": "Enable JavaScript rendering for dynamic web pages",
            },
            "ocr_enabled": {
                "type": "boolean",
                "default": False,
                "description": "Enable OCR for images and scanned PDFs",
            },
            "include_frontmatter": {
                "type": "boolean",
                "default": False,
                "description": "Include YAML frontmatter with metadata",
            },
        },
        "oneOf": [
            {"required": ["url"]},
            {"required": ["content"]},
            {"required": ["text"]},
        ],
    },
)
