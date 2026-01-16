"""MCP server implementation for md-server."""

import asyncio
import base64
import logging
from typing import Any

from mcp.server import Server
from mcp.types import TextContent, Tool

from ..core.converter import DocumentConverter
from ..core.config import get_settings
from .tools import TOOLS
from .handlers import handle_read_resource
from .errors import unknown_tool_error, invalid_input_error

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
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """
    Handle MCP tool calls.

    Args:
        name: Tool name ("read_resource")
        arguments: Tool arguments

    Returns:
        List of TextContent with response (raw markdown or JSON)
    """
    converter = get_converter()
    output_format = arguments.get("output_format", "markdown")

    if name == "read_resource":
        # Extract file_content and decode if present
        file_content_b64 = arguments.get("file_content")
        file_content = None

        if file_content_b64 is not None:
            try:
                file_content = base64.b64decode(file_content_b64)
            except Exception:
                result = invalid_input_error(
                    "Invalid base64 file_content. Content must be base64-encoded."
                )
                return [TextContent(type="text", text=result.model_dump_json())]

        result = await handle_read_resource(
            converter=converter,
            url=arguments.get("url"),
            file_content=file_content,
            filename=arguments.get("filename"),
            render_js=arguments.get("render_js", False),
            max_length=arguments.get("max_length"),
            max_tokens=arguments.get("max_tokens"),
            truncate_mode=arguments.get("truncate_mode"),
            truncate_limit=arguments.get("truncate_limit"),
            timeout=arguments.get("timeout"),
            include_frontmatter=arguments.get("include_frontmatter", True),
            output_format=output_format,
        )
    else:
        result = unknown_tool_error(name)

    # Return raw markdown string or JSON-serialized response
    if isinstance(result, str):
        return [TextContent(type="text", text=result)]
    return [TextContent(type="text", text=result.model_dump_json())]


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
