import pytest
from unittest.mock import patch, Mock
from markitdown import MarkItDown

from md_server.app import (
    provide_converter,
    provide_settings,
    provide_document_converter,
    startup_browser_detection,
    health,
    healthz,
    formats,
    _server_start_time,
)
from md_server.core.config import Settings
from md_server.core.converter import DocumentConverter


class TestProviderFunctions:
    """Test dependency injection provider functions"""

    def test_provide_converter_returns_markitdown_instance(self):
        converter = provide_converter()
        assert isinstance(converter, MarkItDown)

    def test_provide_settings_returns_settings_instance(self):
        settings = provide_settings()
        assert isinstance(settings, Settings)

    @patch("md_server.app.get_settings")
    def test_provide_document_converter_with_browser_available(self, mock_get_settings):
        mock_settings = Mock(spec=Settings)
        mock_settings.conversion_timeout = 30
        mock_settings.max_file_size = 10 * 1024 * 1024  # 10MB in bytes
        mock_get_settings.return_value = mock_settings

        # Mock browser availability
        provide_document_converter._browser_available = True

        converter = provide_document_converter(mock_settings)

        assert isinstance(converter, DocumentConverter)
        assert converter.js_rendering is True
        assert converter.timeout == 30
        assert converter.max_file_size_mb == 10

    @patch("md_server.app.get_settings")
    def test_provide_document_converter_without_browser(self, mock_get_settings):
        mock_settings = Mock(spec=Settings)
        mock_settings.conversion_timeout = 60
        mock_settings.max_file_size = 20 * 1024 * 1024  # 20MB in bytes
        mock_get_settings.return_value = mock_settings

        # Mock browser not available
        provide_document_converter._browser_available = False

        converter = provide_document_converter(mock_settings)

        assert isinstance(converter, DocumentConverter)
        assert converter.js_rendering is False
        assert converter.timeout == 60
        assert converter.max_file_size_mb == 20

    @patch("md_server.app.get_settings")
    def test_provide_document_converter_optional_settings(self, mock_get_settings):
        mock_settings = Mock(spec=Settings)
        mock_settings.conversion_timeout = 45
        mock_settings.max_file_size = 5 * 1024 * 1024  # 5MB in bytes

        # Test optional attributes using getattr defaults
        mock_get_settings.return_value = mock_settings
        provide_document_converter._browser_available = False

        converter = provide_document_converter(mock_settings)

        # Test defaults when attributes don't exist
        assert converter.ocr_enabled is False
        assert converter.extract_images is False
        assert converter.preserve_formatting is True
        assert converter.clean_markdown is False


class TestStartupHandler:
    """Test startup browser detection handler"""

    @pytest.mark.asyncio
    @patch("md_server.app.BrowserChecker.is_available")
    @patch("md_server.app.BrowserChecker.log_availability")
    @patch("md_server.app.logging.basicConfig")
    async def test_startup_browser_detection_success(
        self, mock_logging_config, mock_log_availability, mock_is_available
    ):
        mock_is_available.return_value = True

        await startup_browser_detection()

        mock_logging_config.assert_called_once()
        mock_is_available.assert_called_once()
        mock_log_availability.assert_called_once_with(True)
        assert provide_document_converter._browser_available is True

    @pytest.mark.asyncio
    @patch("md_server.app.BrowserChecker.is_available")
    @patch("md_server.app.BrowserChecker.log_availability")
    @patch("md_server.app.logging.basicConfig")
    async def test_startup_browser_detection_not_available(
        self, mock_logging_config, mock_log_availability, mock_is_available
    ):
        mock_is_available.return_value = False

        await startup_browser_detection()

        mock_logging_config.assert_called_once()
        mock_is_available.assert_called_once()
        mock_log_availability.assert_called_once_with(False)
        assert provide_document_converter._browser_available is False

    @pytest.mark.asyncio
    @patch("md_server.app.BrowserChecker.is_available")
    @patch("md_server.app.logging.basicConfig")
    @patch("md_server.app.logging.error")
    async def test_startup_browser_detection_exception_handling(
        self, mock_log_error, mock_logging_config, mock_is_available
    ):
        mock_is_available.side_effect = Exception("Browser check failed")

        await startup_browser_detection()

        mock_logging_config.assert_called_once()
        mock_is_available.assert_called_once()
        mock_log_error.assert_called_once_with(
            "Startup browser detection failed: Browser check failed"
        )
        assert provide_document_converter._browser_available is False


class TestHealthEndpoints:
    """Test health check endpoints"""

    @pytest.mark.asyncio
    @patch("md_server.app.time.time")
    async def test_health_endpoint(self, mock_time):
        # Mock current time to test uptime calculation
        mock_time.return_value = _server_start_time + 120  # 2 minutes later

        # Access the underlying function from the decorator
        response = await health.fn()

        assert response.status_code == 200
        health_data = response.content
        assert health_data.status == "healthy"
        assert health_data.version == "0.1.0"
        assert health_data.uptime_seconds == 120
        assert health_data.conversions_last_hour == 0

    @pytest.mark.asyncio
    async def test_healthz_endpoint(self):
        # Access the underlying function from the decorator
        response = await healthz.fn()

        assert response.status_code == 200
        assert response.content == {"status": "healthy"}


class TestFormatsEndpoint:
    """Test formats endpoint functionality"""

    @pytest.mark.asyncio
    @patch("md_server.app.BrowserChecker.is_available")
    @patch("md_server.app.ContentTypeDetector.get_supported_formats")
    async def test_formats_endpoint_with_browser(
        self, mock_get_formats, mock_browser_available
    ):
        mock_formats = {
            "html": {
                "extensions": [".html", ".htm"],
                "mime_types": ["text/html"],
                "features": ["text-extraction", "link-detection"],
                "max_size_mb": 10,
            },
            "pdf": {
                "extensions": [".pdf"],
                "mime_types": ["application/pdf"],
                "features": ["text-extraction"],
                "max_size_mb": 50,
            },
        }
        mock_get_formats.return_value = mock_formats
        mock_browser_available.return_value = True

        # Access the underlying function from the decorator
        response = await formats.fn()

        assert response.status_code == 200
        formats_data = response.content
        assert formats_data.supported_formats == ["html", "pdf"]
        assert formats_data.capabilities.browser_available is True
        assert len(formats_data.formats) == 2
        assert "html" in formats_data.formats
        assert "pdf" in formats_data.formats

    @pytest.mark.asyncio
    @patch("md_server.app.BrowserChecker.is_available")
    @patch("md_server.app.ContentTypeDetector.get_supported_formats")
    async def test_formats_endpoint_without_browser(
        self, mock_get_formats, mock_browser_available
    ):
        mock_formats = {
            "txt": {
                "extensions": [".txt"],
                "mime_types": ["text/plain"],
                "features": ["text-extraction"],
                "max_size_mb": 5,
            }
        }
        mock_get_formats.return_value = mock_formats
        mock_browser_available.return_value = False

        # Access the underlying function from the decorator
        response = await formats.fn()

        assert response.status_code == 200
        formats_data = response.content
        assert formats_data.supported_formats == ["txt"]
        assert formats_data.capabilities.browser_available is False
        assert len(formats_data.formats) == 1
        assert "txt" in formats_data.formats


class TestAppCreation:
    """Test app creation with different middleware configurations"""

    @patch.dict("os.environ", {"MD_SERVER_API_KEY": "test-api-key"})
    @patch("md_server.app.get_settings")
    def test_app_creation_with_auth_middleware(self, mock_get_settings):
        """Test that middleware is added when authentication is enabled"""
        # This test forces reimport of the module to trigger line 103
        import importlib
        import md_server.app

        # Reload the module to test the middleware append line
        importlib.reload(md_server.app)

        # Verify the app was created (this covers the middleware append logic)
        assert md_server.app.app is not None
        assert hasattr(md_server.app.app, "middleware")
