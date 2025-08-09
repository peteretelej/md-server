import os
from unittest.mock import patch, MagicMock
import requests
from md_server.app import create_requests_session, provide_converter
from md_server.core.config import Settings
from markitdown import MarkItDown


class TestProxyConfiguration:
    def test_create_requests_session_no_proxy(self):
        """Test requests session creation without proxy configuration."""
        settings = Settings()
        session = create_requests_session(settings)

        assert isinstance(session, requests.Session)
        assert not session.proxies

    def test_create_requests_session_with_http_proxy(self):
        """Test requests session creation with HTTP proxy."""
        settings = Settings(http_proxy="http://proxy.example.com:8080")

        with patch.dict(os.environ, {}, clear=False):
            session = create_requests_session(settings)

            assert session.proxies["http"] == "http://proxy.example.com:8080"
            assert os.environ.get("HTTP_PROXY") == "http://proxy.example.com:8080"

    def test_create_requests_session_with_https_proxy(self):
        """Test requests session creation with HTTPS proxy."""
        settings = Settings(https_proxy="https://proxy.example.com:8080")

        with patch.dict(os.environ, {}, clear=False):
            session = create_requests_session(settings)

            assert session.proxies["https"] == "https://proxy.example.com:8080"
            assert os.environ.get("HTTPS_PROXY") == "https://proxy.example.com:8080"

    def test_create_requests_session_with_both_proxies(self):
        """Test requests session creation with both HTTP and HTTPS proxies."""
        settings = Settings(
            http_proxy="http://proxy.example.com:8080",
            https_proxy="https://proxy.example.com:8443",
        )

        with patch.dict(os.environ, {}, clear=False):
            session = create_requests_session(settings)

            assert session.proxies["http"] == "http://proxy.example.com:8080"
            assert session.proxies["https"] == "https://proxy.example.com:8443"
            assert os.environ.get("HTTP_PROXY") == "http://proxy.example.com:8080"
            assert os.environ.get("HTTPS_PROXY") == "https://proxy.example.com:8443"

    @patch("md_server.app.get_settings")
    @patch("md_server.app.create_requests_session")
    def test_provide_converter_uses_proxy_session(
        self, mock_create_session, mock_get_settings
    ):
        """Test that provide_converter creates MarkItDown with proxy-configured session."""
        mock_settings = Settings(http_proxy="http://proxy.example.com:8080")
        mock_session = MagicMock(spec=requests.Session)

        mock_get_settings.return_value = mock_settings
        mock_create_session.return_value = mock_session

        converter = provide_converter()

        assert isinstance(converter, MarkItDown)
        mock_create_session.assert_called_once_with(mock_settings)

    def test_environment_variables_from_settings(self):
        """Test that proxy environment variables are set from settings."""
        with patch.dict(
            os.environ,
            {
                "MD_SERVER_HTTP_PROXY": "http://env.proxy:8080",
                "MD_SERVER_HTTPS_PROXY": "https://env.proxy:8443",
            },
        ):
            settings = Settings()

            # Clear any existing proxy env vars
            with patch.dict(os.environ, {}, clear=False):
                session = create_requests_session(settings)

                assert os.environ.get("HTTP_PROXY") == "http://env.proxy:8080"
                assert os.environ.get("HTTPS_PROXY") == "https://env.proxy:8443"
                assert session.proxies["http"] == "http://env.proxy:8080"
                assert session.proxies["https"] == "https://env.proxy:8443"
