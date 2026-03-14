"""MCP server implementation for md-server using FastMCP."""

import base64
import logging

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from ..core.converter import DocumentConverter
from ..core.config import get_settings
from .handlers import handle_read_resource
from .models import MCPErrorResponse

logger = logging.getLogger(__name__)

mcp = FastMCP("md-server")


def get_converter() -> DocumentConverter:
    """Create DocumentConverter with current settings."""
    settings = get_settings()
    return DocumentConverter(
        timeout=settings.conversion_timeout,
        max_file_size_mb=settings.max_file_size // (1024 * 1024),
    )


@mcp.tool(
    annotations={"readOnlyHint": True},
    structured_output=False,
)
async def convert_to_markdown(
    url: str | None = None,
    file_content: str | None = None,
    filename: str | None = None,
    render_js: bool = False,
    max_length: int | None = None,
    max_tokens: int | None = None,
    truncate_mode: str | None = None,
    truncate_limit: int | None = None,
    timeout: int | None = None,
    include_frontmatter: bool = True,
    output_format: str = "markdown",
) -> str:
    """Read a URL or file and convert to markdown.

    Provide ONE of:
    - url: Webpage, online PDF, or Google Doc
    - file_content + filename: Base64-encoded file

    Supported formats: PDF, DOCX, XLSX, PPTX, HTML, images (OCR), and more.

    For JavaScript-heavy pages (SPAs, dashboards), set render_js: true.
    This adds ~15-30 seconds but captures dynamically loaded content.

    Returns markdown by default, or structured JSON with metadata (set output_format: "json").
    """
    converter = get_converter()

    # Decode base64 file_content if present
    decoded_content = None
    if file_content is not None:
        try:
            decoded_content = base64.b64decode(file_content)
        except Exception:
            raise ToolError(
                "Invalid base64 file_content. Content must be base64-encoded."
            )

    result = await handle_read_resource(
        converter=converter,
        url=url,
        file_content=decoded_content,
        filename=filename,
        render_js=render_js,
        max_length=max_length,
        max_tokens=max_tokens,
        truncate_mode=truncate_mode,
        truncate_limit=truncate_limit,
        timeout=timeout,
        include_frontmatter=include_frontmatter,
        output_format=output_format,
    )

    # If the handler returned an error response, raise it as a ToolError
    # so FastMCP sets isError: true on the MCP response
    if isinstance(result, MCPErrorResponse):
        msg = result.error.message
        if result.error.suggestions:
            msg += "\n\nSuggestions:\n" + "\n".join(
                f"- {s}" for s in result.error.suggestions
            )
        raise ToolError(msg)

    # For markdown output, result is a plain string
    if isinstance(result, str):
        return result

    # For JSON output, serialize the MCPSuccessResponse
    return result.model_dump_json()


def run_stdio() -> None:
    """Run MCP server over stdin/stdout."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.info("Starting md-server MCP (stdio transport)")
    mcp.run(transport="stdio")
