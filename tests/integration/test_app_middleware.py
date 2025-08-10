from unittest.mock import patch
from md_server.core.config import Settings
import importlib
import sys


class TestAppMiddlewareIntegration:
    @patch("md_server.core.config.get_settings")
    def test_middleware_added_when_auth_configured(self, mock_get_settings):
        """Test that middleware is added when auth is configured"""
        # Configure settings with API key
        mock_settings = Settings(api_key="test-api-key")
        mock_get_settings.return_value = mock_settings

        # Reload app module to trigger middleware creation with new settings
        if "md_server.app" in sys.modules:
            importlib.reload(sys.modules["md_server.app"])

        import md_server.app as app_module

        # Verify middleware list contains auth middleware when API key is set
        assert len(app_module.middleware) > 0

    @patch("md_server.core.config.get_settings")
    def test_no_middleware_when_auth_not_configured(self, mock_get_settings):
        """Test that no middleware is added when auth is not configured"""
        # Configure settings without API key
        mock_settings = Settings()
        mock_get_settings.return_value = mock_settings

        # Reload app module to trigger middleware creation with new settings
        if "md_server.app" in sys.modules:
            importlib.reload(sys.modules["md_server.app"])

        import md_server.app as app_module

        # Verify middleware list is empty when no API key is set
        assert len(app_module.middleware) == 0
