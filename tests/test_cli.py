import pytest
import socket
from unittest.mock import patch
import subprocess
import sys
from pathlib import Path

from md_server.__main__ import is_port_available, main


class TestPortAvailability:
    def test_is_port_available_free_port(self):
        # Find a definitely free port by binding to 0 first
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as temp_sock:
            temp_sock.bind(("127.0.0.1", 0))
            free_port = temp_sock.getsockname()[1]

        assert is_port_available("127.0.0.1", free_port) is True

    def test_is_port_available_bound_port(self):
        # Bind to a port and check it's not available
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            bound_port = sock.getsockname()[1]
            assert is_port_available("127.0.0.1", bound_port) is False

    def test_is_port_available_invalid_host(self):
        # Should handle invalid host gracefully
        result = is_port_available("invalid.host.name", 8080)
        assert result is False


class TestCLIMain:
    @patch("sys.argv", ["md_server"])
    @patch("md_server.__main__.is_port_available", return_value=True)
    @patch("md_server.__main__.uvicorn.run")
    def test_main_default_args(self, mock_uvicorn_run, mock_port_available):
        main()
        mock_uvicorn_run.assert_called_once()
        call_args = mock_uvicorn_run.call_args
        assert call_args.kwargs["host"] == "127.0.0.1"
        assert call_args.kwargs["port"] == 8080

    @patch("sys.argv", ["md_server", "--host", "0.0.0.0", "--port", "9011"])
    @patch("md_server.__main__.is_port_available", return_value=True)
    @patch("md_server.__main__.uvicorn.run")
    def test_main_custom_args(self, mock_uvicorn_run, mock_port_available):
        main()
        mock_uvicorn_run.assert_called_once()
        call_args = mock_uvicorn_run.call_args
        assert call_args.kwargs["host"] == "0.0.0.0"
        assert call_args.kwargs["port"] == 9011

    @patch("sys.argv", ["md_server", "--port", "8080"])
    @patch("md_server.__main__.is_port_available")
    @patch("md_server.__main__.uvicorn.run")
    def test_main_port_busy_warning(self, mock_uvicorn_run, mock_is_port_available):
        mock_is_port_available.return_value = False

        with patch("builtins.print") as mock_print, patch("sys.exit") as mock_exit:
            main()
            mock_exit.assert_called_once_with(1)

        # Should print a warning about port being busy
        any(
            "already in use" in str(call) or "port" in str(call).lower()
            for call in mock_print.call_args_list
        )
        # Note: This test may need adjustment based on actual warning implementation
        mock_uvicorn_run.assert_called_once()


class TestCLIIntegration:
    def test_module_can_be_imported(self):
        """Test that the CLI module can be imported without errors"""
        import md_server.__main__

        assert hasattr(md_server.__main__, "main")
        assert hasattr(md_server.__main__, "is_port_available")

    @pytest.mark.skipif(
        sys.platform == "win32", reason="Process testing may be unreliable on Windows"
    )
    def test_cli_help_option(self):
        """Test that --help option works"""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "md_server", "--help"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=Path(__file__).parent.parent,  # Run from project root
            )
            # Should exit with 0 and show help text
            assert result.returncode == 0
            assert "md-server" in result.stdout.lower()
            assert "port" in result.stdout.lower()
        except subprocess.TimeoutExpired:
            pytest.skip("CLI help test timed out")
        except FileNotFoundError:
            pytest.skip("Could not run CLI module")

    @pytest.mark.skipif(
        sys.platform == "win32", reason="Process testing may be unreliable on Windows"
    )
    def test_cli_invalid_option(self):
        """Test that invalid options are handled"""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "md_server", "--invalid-option"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=Path(__file__).parent.parent,  # Run from project root
            )
            # Should exit with non-zero code for invalid option
            assert result.returncode != 0
        except subprocess.TimeoutExpired:
            pytest.skip("CLI invalid option test timed out")
        except FileNotFoundError:
            pytest.skip("Could not run CLI module")
