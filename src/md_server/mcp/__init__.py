"""MCP server module for md-server.

Public API:
    run_stdio: Run the MCP server over stdin/stdout.

Note: SSE transport (run_sse), READ_RESOURCE_TOOL, and TOOLS were intentionally
removed as part of the FastMCP modernization. The server now uses FastMCP's
decorator-based tool registration instead of manual tool definitions.
"""

from .server import run_stdio

__all__ = ["run_stdio"]
