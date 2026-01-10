import asyncio
import base64
import logging
from typing import Any

from mcp.server import Server
from mcp.types import TextContent, Tool

from ..core.converter import DocumentConverter
from ..core.config import get_settings
from .tools import CONVERT_TOOL

logger = logging.getLogger(__name__)

server = Server("md-server")


def get_converter() -> DocumentConverter:
    """Create DocumentConverter with current settings."""
    settings = get_settings()
    return DocumentConverter(
        timeout=settings.conversion_timeout,
        max_file_size_mb=settings.max_file_size // (1024 * 1024),
    )


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Return available MCP tools."""
    return [CONVERT_TOOL]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """
    Handle MCP tool calls.

    Args:
        name: Tool name (only "convert" supported)
        arguments: Tool arguments

    Returns:
        List of TextContent with conversion result
    """
    if name != "convert":
        raise ValueError(f"Unknown tool: {name}")

    converter = get_converter()

    try:
        js_rendering = arguments.get("js_rendering", False)
        include_frontmatter = arguments.get("include_frontmatter", False)

        if "url" in arguments:
            result = await converter.convert_url(
                arguments["url"],
                js_rendering=js_rendering,
                include_frontmatter=include_frontmatter,
            )
        elif "content" in arguments:
            content = base64.b64decode(arguments["content"])
            filename = arguments.get("filename")
            result = await converter.convert_content(
                content,
                filename=filename,
                include_frontmatter=include_frontmatter,
            )
        elif "text" in arguments:
            text = arguments["text"]
            mime_type = "text/html" if text.lstrip()[:1] == "<" else "text/plain"
            result = await converter.convert_text(
                text,
                mime_type,
                include_frontmatter=include_frontmatter,
            )
        else:
            raise ValueError("Must provide url, content, or text")

        return [TextContent(type="text", text=result.markdown)]

    except Exception as e:
        logger.error("Conversion failed: %s", e)
        error_message = f"Error: {type(e).__name__} - {str(e)}"
        return [TextContent(type="text", text=error_message)]


def run_stdio() -> None:
    """
    Run MCP server over stdin/stdout.

    Used for local IDE integration (Claude Desktop, Cursor).
    """
    from mcp.server.stdio import stdio_server

    async def main() -> None:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        logger.info("Starting md-server MCP (stdio transport)")

        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )

    asyncio.run(main())


def run_sse(host: str = "0.0.0.0", port: int = 8080) -> None:
    """
    Run MCP server over Server-Sent Events.

    Used for network-based AI agents.

    Args:
        host: Bind host
        port: Bind port
    """
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Route
    from starlette.responses import JSONResponse
    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.info("Starting md-server MCP (SSE transport) on %s:%d", host, port)

    sse_transport = SseServerTransport("/messages")

    async def handle_sse(request: Any) -> None:
        async with sse_transport.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await server.run(
                streams[0],
                streams[1],
                server.create_initialization_options(),
            )

    async def health(request: Any) -> JSONResponse:
        return JSONResponse({"status": "healthy", "mode": "mcp-sse"})

    app = Starlette(
        routes=[
            Route("/health", endpoint=health, methods=["GET"]),
            Route("/sse", endpoint=handle_sse),
            sse_transport.handle_post_message,
        ]
    )

    uvicorn.run(app, host=host, port=port)
