import threading
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socket
import time


class TestRequestHandler(SimpleHTTPRequestHandler):
    """Custom request handler for testing specific scenarios"""

    def do_GET(self):
        # Handle special test endpoints
        if self.path == "/timeout":
            # Simulate timeout by taking too long
            time.sleep(10)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Timeout Test</h1></body></html>")
            return
        elif self.path == "/forbidden":
            # Simulate blocked/forbidden access
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"<html><body><h1>403 Forbidden</h1></body></html>")
            return
        elif self.path == "/server-error":
            # Simulate server error
            self.send_response(500)
            self.end_headers()
            self.wfile.write(
                b"<html><body><h1>500 Internal Server Error</h1></body></html>"
            )
            return
        elif self.path == "/bad-request":
            # Simulate bad request
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"<html><body><h1>400 Bad Request</h1></body></html>")
            return

        # Default behavior for normal files
        super().do_GET()


class TestHTTPServer:
    """Simple HTTP server for testing URL conversions locally"""

    def __init__(self, port: int = 0, directory: Path = None):
        self.port = port
        self.directory = directory or Path(__file__).parent / "html_files"
        self.server = None
        self.thread = None
        self.actual_port = None

    def start(self):
        """Start the test server in a background thread"""
        if self.server is not None:
            return self.actual_port

        # Change to test directory
        original_dir = Path.cwd()

        def run_server():
            import os

            os.chdir(self.directory)

            with HTTPServer(("127.0.0.1", self.port), TestRequestHandler) as httpd:
                httpd.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.actual_port = httpd.server_address[1]
                self.server = httpd
                try:
                    httpd.serve_forever()
                except Exception:
                    pass
                finally:
                    os.chdir(original_dir)

        self.thread = threading.Thread(target=run_server, daemon=True)
        self.thread.start()

        # Wait for server to start
        import time

        timeout = 5
        while timeout > 0 and self.actual_port is None:
            time.sleep(0.1)
            timeout -= 0.1

        return self.actual_port

    def stop(self):
        """Stop the test server"""
        if self.server:
            self.server.shutdown()
            self.server = None
        if self.thread:
            self.thread.join(timeout=1)
            self.thread = None
        self.actual_port = None

    def url(self, path: str = "") -> str:
        """Get URL for a path on the test server"""
        if self.actual_port is None:
            raise RuntimeError("Server not started")
        return f"http://127.0.0.1:{self.actual_port}/{path.lstrip('/')}"

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


def get_free_port() -> int:
    """Get a free port for testing in the safe range 50111-65535"""
    import random

    # Try to find a free port in the safe high range
    for attempt in range(100):  # Try up to 100 times
        port = random.randint(50111, 60000)  # Safe high port range
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue

    # Fallback to system-assigned port if nothing available in range
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
