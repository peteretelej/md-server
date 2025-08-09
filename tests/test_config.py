import os
from unittest.mock import patch
from md_server.core.config import Settings, get_settings


class TestSettings:
    def test_default_values(self):
        """Test that default values are set correctly."""
        settings = Settings()

        assert settings.host == "127.0.0.1"
        assert settings.port == 8080
        assert settings.api_key is None
        assert settings.max_file_size == 50 * 1024 * 1024
        assert settings.timeout_seconds == 30
        assert settings.debug is False
        assert settings.http_proxy is None
        assert settings.https_proxy is None
        assert "application/pdf" in settings.allowed_file_types
        assert "text/plain" in settings.allowed_file_types

    def test_env_prefix(self):
        """Test that MD_SERVER_ prefix is used for environment variables."""
        with patch.dict(
            os.environ,
            {
                "MD_SERVER_HOST": "0.0.0.0",
                "MD_SERVER_PORT": "9000",
                "MD_SERVER_API_KEY": "test-api-key",
                "MD_SERVER_MAX_FILE_SIZE": "10485760",
                "MD_SERVER_TIMEOUT_SECONDS": "60",
                "MD_SERVER_DEBUG": "true",
                "MD_SERVER_HTTP_PROXY": "http://proxy.example.com:8080",
                "MD_SERVER_HTTPS_PROXY": "https://proxy.example.com:8080",
            },
        ):
            settings = Settings()

            assert settings.host == "0.0.0.0"
            assert settings.port == 9000
            assert settings.api_key == "test-api-key"
            assert settings.max_file_size == 10485760
            assert settings.timeout_seconds == 60
            assert settings.debug is True
            assert settings.http_proxy == "http://proxy.example.com:8080"
            assert settings.https_proxy == "https://proxy.example.com:8080"

    def test_env_variable_override(self):
        """Test that environment variables override default values."""
        with patch.dict(os.environ, {"MD_SERVER_DEBUG": "true"}):
            settings = Settings()
            assert settings.debug is True

        with patch.dict(os.environ, {"MD_SERVER_DEBUG": "false"}):
            settings = Settings()
            assert settings.debug is False

    def test_api_key_optional(self):
        """Test that API key is optional and can be None."""
        settings = Settings()
        assert settings.api_key is None

        with patch.dict(os.environ, {"MD_SERVER_API_KEY": "secret-key"}):
            settings = Settings()
            assert settings.api_key == "secret-key"

    def test_proxy_configuration(self):
        """Test proxy configuration fields."""
        settings = Settings()
        assert settings.http_proxy is None
        assert settings.https_proxy is None

        with patch.dict(
            os.environ,
            {
                "MD_SERVER_HTTP_PROXY": "http://proxy:8080",
                "MD_SERVER_HTTPS_PROXY": "https://proxy:8080",
            },
        ):
            settings = Settings()
            assert settings.http_proxy == "http://proxy:8080"
            assert settings.https_proxy == "https://proxy:8080"

    def test_get_settings_function(self):
        """Test that get_settings returns a Settings instance."""
        settings = get_settings()
        assert isinstance(settings, Settings)
        assert settings.host == "127.0.0.1"

    def test_boolean_conversion(self):
        """Test boolean environment variable conversion."""
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("0", False),
        ]

        for env_value, expected in test_cases:
            with patch.dict(os.environ, {"MD_SERVER_DEBUG": env_value}):
                settings = Settings()
                assert settings.debug == expected

    def test_integer_conversion(self):
        """Test integer environment variable conversion."""
        with patch.dict(
            os.environ,
            {
                "MD_SERVER_PORT": "9999",
                "MD_SERVER_MAX_FILE_SIZE": "1048576",
                "MD_SERVER_TIMEOUT_SECONDS": "45",
            },
        ):
            settings = Settings()
            assert settings.port == 9999
            assert settings.max_file_size == 1048576
            assert settings.timeout_seconds == 45
