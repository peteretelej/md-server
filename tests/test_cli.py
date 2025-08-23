import socket
import subprocess
import sys
import time
import threading
from unittest.mock import patch
import pytest
import requests

from md_server.__main__ import is_port_available, main


class TestCLIUser:
    """Test CLI user workflows - command line invocation and server management."""

    def test_cli_startup(self):
        """Test basic CLI startup and argument parsing - core CLI user need."""
        # Test that we can import and call the main function
        # This validates the CLI entry point is functional

        # Mock uvicorn.run to prevent actual server startup in tests
        with (
            patch("md_server.__main__.uvicorn.run") as mock_run,
            patch("md_server.__main__.is_port_available", return_value=True),
            patch("sys.argv", ["md-server"]),
        ):
            main()

            # Verify uvicorn.run was called with defaults
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args

            # Check that app was passed
            from md_server.app import app

            assert args[0] is app

            # Check default host and port in kwargs
            assert kwargs.get("host") == "127.0.0.1"
            assert kwargs.get("port") == 8080

    def test_cli_port_validation(self):
        """Test port availability checking - CLI validation logic."""
        # Test port available
        available_port = self._find_available_port()
        assert is_port_available("127.0.0.1", available_port) is True

        # Test port unavailable - bind to it first
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", available_port))
            sock.listen(1)

            # Now the port should be unavailable
            assert is_port_available("127.0.0.1", available_port) is False

    def test_cli_argument_parsing(self):
        """Test CLI argument parsing - host/port customization."""
        with (
            patch("md_server.__main__.uvicorn.run") as mock_run,
            patch("md_server.__main__.is_port_available", return_value=True),
            patch("sys.argv", ["md-server", "--host", "0.0.0.0", "--port", "9090"]),
        ):
            main()

            # Verify custom arguments were parsed correctly
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args

            assert kwargs.get("host") == "0.0.0.0"
            assert kwargs.get("port") == 9090

    def test_cli_port_conflict(self):
        """Test port conflict handling - user experience for busy ports."""
        # Mock port as unavailable
        with (
            patch("md_server.__main__.is_port_available", return_value=False),
            patch("builtins.print") as mock_print,
            patch("sys.argv", ["md-server", "--port", "8080"]),
        ):
            # Should exit with code 1
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1

            # Verify helpful error messages were printed
            print_calls = [call[0][0] for call in mock_print.call_args_list]

            # Check for error message about port being in use
            assert any("Port 8080 is already in use" in call for call in print_calls)

            # Check for helpful suggestion
            assert any("Try using a different port" in call for call in print_calls)
            assert any("uvx md-server --port" in call for call in print_calls)

    def test_cli_server_startup(self):
        """Test full server startup from CLI - integration test."""
        # Find an available port for testing
        test_port = self._find_available_port()

        # Start server in background thread
        def run_server():
            with patch("sys.argv", ["md-server", "--port", str(test_port)]):
                main()

        # Mock uvicorn.run to simulate quick startup and shutdown
        server_started = threading.Event()

        def mock_uvicorn_run(app, host, port):
            server_started.set()
            time.sleep(0.1)  # Simulate brief server run

        with patch("md_server.__main__.uvicorn.run", side_effect=mock_uvicorn_run):
            server_thread = threading.Thread(target=run_server)
            server_thread.daemon = True
            server_thread.start()

            # Wait for server to start
            assert server_started.wait(timeout=2), (
                "Server should start within 2 seconds"
            )

            # Cleanup
            server_thread.join(timeout=1)

    def test_cli_graceful_shutdown(self):
        """Test graceful shutdown handling - CLI lifecycle management."""
        # This tests that the CLI doesn't hang or crash on shutdown
        test_port = self._find_available_port()

        shutdown_called = threading.Event()

        def mock_uvicorn_run(app, host, port):
            # Simulate server running briefly then shutting down
            time.sleep(0.1)
            shutdown_called.set()

        with (
            patch("md_server.__main__.uvicorn.run", side_effect=mock_uvicorn_run),
            patch("sys.argv", ["md-server", "--port", str(test_port)]),
        ):
            # Should complete without hanging
            main()

            # Verify shutdown was called
            assert shutdown_called.is_set()

    def test_cli_help_output(self):
        """Test CLI help output - user documentation."""
        with patch("sys.argv", ["md-server", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            # Help should exit with code 0
            assert exc_info.value.code == 0

    def test_cli_invalid_arguments(self):
        """Test CLI error handling for invalid arguments."""
        # Test invalid port (non-integer)
        with patch("sys.argv", ["md-server", "--port", "invalid"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            # Should exit with error code
            assert exc_info.value.code != 0

    def _find_available_port(self):
        """Find an available port for testing."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]


class TestCLIIntegration:
    """Integration tests for CLI functionality - end-to-end user workflows."""

    def test_cli_module_execution(self):
        """Test 'python -m md_server' execution - module entry point."""
        # Test that the module can be executed directly
        result = subprocess.run(
            [sys.executable, "-m", "md_server", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Should complete successfully and show help
        assert result.returncode == 0
        assert (
            "md-server: HTTP API for document-to-markdown conversion" in result.stdout
        )

    def test_cli_startup_with_real_server(self):
        """Test CLI starts real server that accepts requests - full integration."""
        test_port = self._find_available_port()

        # Start server process
        server_process = subprocess.Popen(
            [sys.executable, "-m", "md_server", "--port", str(test_port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        try:
            # Wait for server to start with retries
            server_ready = False
            for attempt in range(15):  # Try for up to 15 seconds
                time.sleep(1)
                try:
                    response = requests.get(
                        f"http://127.0.0.1:{test_port}/health", timeout=2
                    )
                    if response.status_code == 200:
                        server_ready = True
                        break
                except requests.exceptions.ConnectionError:
                    continue  # Server not ready yet

            if not server_ready:
                # Print server output for debugging
                server_process.terminate()
                try:
                    stdout, stderr = server_process.communicate(timeout=2)
                    print(f"Server stdout: {stdout.decode()}")
                    print(f"Server stderr: {stderr.decode()}")
                except subprocess.TimeoutExpired:
                    server_process.kill()
                    stdout, stderr = server_process.communicate()
                    print(f"Server stdout: {stdout.decode()}")
                    print(f"Server stderr: {stderr.decode()}")

                pytest.fail("Server failed to start within 15 seconds")

            # Test that server is responding
            response = requests.get(f"http://127.0.0.1:{test_port}/health", timeout=5)
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "healthy"

        finally:
            # Clean shutdown
            if server_process.poll() is None:
                server_process.terminate()
                try:
                    server_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server_process.kill()
                    server_process.wait()

    def test_cli_browser_detection_workflow(self):
        """Test browser detection during CLI startup - capability detection."""
        test_port = self._find_available_port()

        # Start server and capture startup logs
        server_process = subprocess.Popen(
            [sys.executable, "-m", "md_server", "--port", str(test_port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            # Give server time to start and run browser detection
            time.sleep(3)

            # Terminate and check output
            server_process.terminate()
            stdout, stderr = server_process.communicate(timeout=5)

            # Should have browser detection logs (info level)
            output = stdout + stderr

            # Browser detection should occur during startup
            # The exact message may vary, but should mention browser or capability
            assert any(
                word in output.lower()
                for word in ["browser", "crawl4ai", "capability", "available"]
            )

        finally:
            if server_process.poll() is None:
                server_process.kill()
                server_process.wait()

    def _find_available_port(self):
        """Find an available port for testing."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]


class TestCLIUserExperience:
    """Test CLI user experience and error scenarios."""

    def test_cli_port_suggestions(self):
        """Test helpful port suggestions when port is busy."""
        with (
            patch("md_server.__main__.is_port_available", return_value=False),
            patch("builtins.print") as mock_print,
            patch("sys.argv", ["md-server", "--port", "3000"]),
        ):
            with pytest.raises(SystemExit):
                main()

            # Check that suggestion includes next port
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            assert any("--port 3001" in call for call in print_calls)

    def test_cli_error_messages(self):
        """Test clear error messages for common CLI issues."""
        # Test port in use message
        with (
            patch("md_server.__main__.is_port_available", return_value=False),
            patch("builtins.print") as mock_print,
            patch("sys.argv", ["md-server"]),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1

            # Should have clear error message
            error_messages = [call[0][0] for call in mock_print.call_args_list]
            assert any("Error:" in msg for msg in error_messages)
            assert any("already in use" in msg for msg in error_messages)

    def test_cli_default_values(self):
        """Test CLI uses sensible defaults - user convenience."""
        with (
            patch("md_server.__main__.uvicorn.run") as mock_run,
            patch("md_server.__main__.is_port_available", return_value=True),
            patch("sys.argv", ["md-server"]),
        ):  # No arguments
            main()

            # Should use defaults
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args

            assert kwargs.get("host") == "127.0.0.1"  # Secure default
            assert kwargs.get("port") == 8080  # Standard HTTP port

    def test_cli_startup_failures(self):
        """Test CLI startup failure scenarios - comprehensive error handling."""
        # Test 1: Invalid host address
        with (
            patch("md_server.__main__.uvicorn.run") as mock_run,
            patch("md_server.__main__.is_port_available", return_value=True),
            patch("sys.argv", ["md-server", "--host", "999.999.999.999"]),
        ):
            # Mock uvicorn to simulate host resolution failure
            mock_run.side_effect = OSError("Invalid host address")

            with pytest.raises(OSError):
                main()

        # Test 2: Permission denied on privileged port (port 80)
        with (
            patch("md_server.__main__.is_port_available", return_value=True),
            patch("md_server.__main__.uvicorn.run") as mock_run,
            patch("sys.argv", ["md-server", "--port", "80"]),
        ):
            # Mock permission denied error
            mock_run.side_effect = PermissionError("Permission denied on port 80")

            with pytest.raises(PermissionError):
                main()

        # Test 3: Invalid port number (too high)
        with (
            patch("builtins.print"),
            patch("sys.argv", ["md-server", "--port", "99999"]),
        ):
            # Should raise OverflowError or SystemExit due to invalid port
            with pytest.raises((SystemExit, OverflowError)):
                main()

        # Test 4: Invalid port number (negative)
        with (
            patch("builtins.print"),
            patch("sys.argv", ["md-server", "--port", "-1"]),
        ):
            # Should raise OverflowError due to invalid port
            with pytest.raises((SystemExit, OverflowError)):
                main()

        # Test 5: Non-numeric port
        with patch("sys.argv", ["md-server", "--port", "not-a-number"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            # Should exit with error code for invalid argument
            assert exc_info.value.code != 0
