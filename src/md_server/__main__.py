import argparse
import socket
import sys
import uvicorn
from .app import app


def is_port_available(host: str, port: int) -> bool:
    """Check if a port is available for binding."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((host, port))
            return True
    except OSError:
        return False


def main():
    parser = argparse.ArgumentParser(
        description="md-server: HTTP API for document-to-markdown conversion"
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=8080, help="Port to bind to (default: 8080)"
    )

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--http",
        action="store_const",
        const="http",
        dest="mode",
        help="Run as HTTP server (default)",
    )
    mode_group.add_argument(
        "--mcp-stdio",
        action="store_const",
        const="mcp-stdio",
        dest="mode",
        help="Run as MCP server (stdio transport)",
    )
    mode_group.add_argument(
        "--mcp-sse",
        action="store_const",
        const="mcp-sse",
        dest="mode",
        help="Run as MCP server (SSE transport)",
    )

    parser.set_defaults(mode="http")

    args = parser.parse_args()

    if args.mode == "mcp-stdio":
        try:
            from .mcp.server import run_stdio
        except ImportError:
            print(
                "MCP dependencies not installed. Install with: pip install md-server[mcp]",
                file=sys.stderr,
            )
            sys.exit(1)
        run_stdio()

    elif args.mode == "mcp-sse":
        try:
            from .mcp.server import run_sse
        except ImportError:
            print(
                "MCP dependencies not installed. Install with: pip install md-server[mcp]",
                file=sys.stderr,
            )
            sys.exit(1)
        run_sse(host=args.host, port=args.port)

    else:
        if not is_port_available(args.host, args.port):
            print(f"Error: Port {args.port} is already in use on {args.host}")
            print(
                "  Try using a different port with --port <PORT_NUMBER> or the env variable MD_SERVER_PORT"
            )
            print(f"  Example: uvx md-server --port {args.port + 1}")
            sys.exit(1)

        uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
