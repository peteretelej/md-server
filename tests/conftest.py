import asyncio
import os
import socket
import subprocess
import sys
import time
import threading
import http.server
import socketserver
import pytest
import requests
from pathlib import Path
from typing import Generator

from md_server.core.config import Settings


def find_free_port() -> int:
    """Find and return an available port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="session")
def server_port() -> int:
    """Session-scoped free port for test server."""
    return find_free_port()


@pytest.fixture(scope="session")
def auth_port() -> int:
    """Session-scoped free port for authenticated test server."""
    return find_free_port()


@pytest.fixture(scope="session")
def test_server(server_port: int) -> Generator[str, None, None]:
    """Session-scoped real server fixture without authentication."""
    server_process = subprocess.Popen(
        [sys.executable, "-m", "md_server", "--port", str(server_port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "MD_SERVER_DEBUG": "false"}
    )

    server_url = f"http://127.0.0.1:{server_port}"
    server_ready = False

    # Wait for server startup with timeout
    for attempt in range(30):  # 30 second timeout
        time.sleep(1)
        try:
            response = requests.get(f"{server_url}/health", timeout=2)
            if response.status_code == 200:
                server_ready = True
                break
        except requests.exceptions.ConnectionError:
            pass

    if not server_ready:
        server_process.terminate()
        server_process.wait()
        raise RuntimeError(f"Test server failed to start on port {server_port}")

    yield server_url

    # Cleanup
    server_process.terminate()
    server_process.wait()


@pytest.fixture(scope="session")
def auth_server(auth_port: int) -> Generator[tuple[str, str], None, None]:
    """Session-scoped real server fixture with API key authentication."""
    api_key = "test-api-key-12345"
    
    server_process = subprocess.Popen(
        [sys.executable, "-m", "md_server", "--port", str(auth_port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={
            **os.environ, 
            "MD_SERVER_API_KEY": api_key,
            "MD_SERVER_DEBUG": "false"
        }
    )

    server_url = f"http://127.0.0.1:{auth_port}"
    server_ready = False

    # Wait for server startup with timeout
    for attempt in range(30):  # 30 second timeout
        time.sleep(1)
        try:
            # Test health endpoint (should work without auth)
            response = requests.get(f"{server_url}/health", timeout=2)
            if response.status_code == 200:
                server_ready = True
                break
        except requests.exceptions.ConnectionError:
            pass

    if not server_ready:
        server_process.terminate()
        server_process.wait()
        raise RuntimeError(f"Authenticated test server failed to start on port {auth_port}")

    yield server_url, api_key

    # Cleanup
    server_process.terminate()
    server_process.wait()


@pytest.fixture
def test_settings() -> Settings:
    """Provide test-specific settings configuration."""
    return Settings(
        debug=True,
        max_file_size=10 * 1024 * 1024,  # 10MB for tests
        timeout_seconds=10,
        conversion_timeout=30,
    )


@pytest.fixture
def auth_test_settings() -> Settings:
    """Provide test-specific settings with authentication enabled."""
    return Settings(
        debug=True,
        api_key="test-api-key-12345",
        max_file_size=10 * 1024 * 1024,  # 10MB for tests
        timeout_seconds=10,
        conversion_timeout=30,
    )


@pytest.fixture
def test_data_dir() -> Path:
    """Return path to test data directory."""
    return Path(__file__).parent / "test_data"


@pytest.fixture
def sample_pdf(test_data_dir: Path) -> Path:
    """Return path to sample PDF file."""
    return test_data_dir / "test.pdf"


@pytest.fixture
def sample_docx(test_data_dir: Path) -> Path:
    """Return path to sample DOCX file."""
    return test_data_dir / "test.docx"


@pytest.fixture
def sample_html(test_data_dir: Path) -> Path:
    """Return path to sample HTML file."""
    return test_data_dir / "test_blog.html"


@pytest.fixture
def sample_image(test_data_dir: Path) -> Path:
    """Return path to sample image file."""
    return test_data_dir / "test.jpg"


class DelayedHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler that adds delays for timeout testing."""
    
    def do_GET(self):
        if self.path == "/delay.html":
            # Add a 2-second delay for timeout testing
            time.sleep(2)
        super().do_GET()


@pytest.fixture(scope="session")
def http_test_server() -> Generator[str, None, None]:
    """Session-scoped HTTP server serving test files from test_data directory."""
    test_data_dir = Path(__file__).parent / "test_data"
    
    # Change to test_data directory for serving files
    original_cwd = os.getcwd()
    os.chdir(test_data_dir)
    
    try:
        port = find_free_port()
        handler = DelayedHTTPRequestHandler
        
        with socketserver.TCPServer(("127.0.0.1", port), handler) as httpd:
            # Start server in background thread
            server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            server_thread.start()
            
            # Wait for server to be ready
            server_url = f"http://127.0.0.1:{port}"
            server_ready = False
            
            for attempt in range(10):  # 10 second timeout
                time.sleep(0.5)
                try:
                    response = requests.get(f"{server_url}/simple.html", timeout=1)
                    if response.status_code == 200:
                        server_ready = True
                        break
                except requests.exceptions.RequestException:
                    pass
            
            if not server_ready:
                httpd.shutdown()
                raise RuntimeError(f"HTTP test server failed to start on port {port}")
            
            yield server_url
            
            # Cleanup
            httpd.shutdown()
            server_thread.join(timeout=5)
    
    finally:
        # Restore original working directory
        os.chdir(original_cwd)


# Event loop fixture for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()