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

    args = parser.parse_args()

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
