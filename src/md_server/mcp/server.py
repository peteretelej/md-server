"""MCP server implementation for md-server using FastMCP."""

import base64
import logging
import time

from mcp.server.fastmcp import FastMCP, Context
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
    ctx: Context | None = None,
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
    start_time = time.monotonic()
    input_type = "url" if url else "file"
    logger.info(
        "convert_to_markdown: input_type=%s, render_js=%s", input_type, render_js
    )

    if render_js and ctx:
        await ctx.info("Converting URL with JS rendering, this may take 15-30s...")

    converter = get_converter()

    # Decode base64 file_content if present
    decoded_content = None
    if file_content is not None:
        # Estimate decoded size before allocating memory
        estimated_size = len(file_content) * 3 / 4
        settings = get_settings()
        if estimated_size > settings.max_file_size:
            raise ToolError(
                f"File too large: ~{estimated_size / 1048576:.1f}MB exceeds "
                f"{settings.max_file_size / 1048576:.0f}MB limit"
            )
        try:
            decoded_content = base64.b64decode(file_content)
        except Exception:
            raise ToolError(
                "Invalid base64 file_content. Content must be base64-encoded."
            )

    try:
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
    except Exception:
        duration_ms = int((time.monotonic() - start_time) * 1000)
        logger.error(
            "convert_to_markdown: error, input_type=%s, duration_ms=%d",
            input_type,
            duration_ms,
        )
        raise

    duration_ms = int((time.monotonic() - start_time) * 1000)

    # If the handler returned an error response, raise it as a ToolError
    # so FastMCP sets isError: true on the MCP response
    if isinstance(result, MCPErrorResponse):
        logger.warning(
            "convert_to_markdown: error_code=%s, input_type=%s, duration_ms=%d",
            result.error.code,
            input_type,
            duration_ms,
        )
        msg = result.error.message
        if result.error.suggestions:
            msg += "\n\nSuggestions:\n" + "\n".join(
                f"- {s}" for s in result.error.suggestions
            )
        if ctx:
            await ctx.error(f"Conversion failed: {result.error.message}")
        raise ToolError(msg)

    # For markdown output, result is a plain string
    if isinstance(result, str):
        logger.info(
            "convert_to_markdown: success, input_type=%s, duration_ms=%d, length=%d",
            input_type,
            duration_ms,
            len(result),
        )
        return result

    # For JSON output, serialize the MCPSuccessResponse
    response_json = result.model_dump_json()
    logger.info(
        "convert_to_markdown: success, input_type=%s, duration_ms=%d, format=json",
        input_type,
        duration_ms,
    )
    return response_json


def run_stdio() -> None:
    """Run MCP server over stdin/stdout."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.info("Starting md-server MCP (stdio transport)")
    mcp.run(transport="stdio")
