from unittest.mock import patch
from md_server.app import startup_browser_detection


class TestAppStartup:
    @patch("md_server.app.BrowserChecker.is_available")
    @patch("md_server.app.BrowserChecker.log_availability")
    @patch("md_server.app.provide_url_converter")
    async def test_startup_browser_detection_success(
        self, mock_provide_url_converter, mock_log_availability, mock_is_available
    ):
        """Test successful browser detection during startup"""
        mock_is_available.return_value = True

        await startup_browser_detection()

        mock_is_available.assert_called_once()
        mock_log_availability.assert_called_once_with(True)
        assert mock_provide_url_converter._browser_available is True

    @patch("md_server.app.BrowserChecker.is_available")
    @patch("md_server.app.BrowserChecker.log_availability")
    @patch("md_server.app.provide_url_converter")
    async def test_startup_browser_detection_unavailable(
        self, mock_provide_url_converter, mock_log_availability, mock_is_available
    ):
        """Test browser detection when browser is unavailable"""
        mock_is_available.return_value = False

        await startup_browser_detection()

        mock_is_available.assert_called_once()
        mock_log_availability.assert_called_once_with(False)
        assert mock_provide_url_converter._browser_available is False

    @patch("md_server.app.BrowserChecker.is_available")
    @patch("md_server.app.provide_url_converter")
    @patch("logging.error")
    async def test_startup_browser_detection_exception(
        self, mock_logging_error, mock_provide_url_converter, mock_is_available
    ):
        """Test exception handling during browser detection"""
        error_msg = "Browser detection failed"
        mock_is_available.side_effect = Exception(error_msg)

        await startup_browser_detection()

        mock_is_available.assert_called_once()
        mock_logging_error.assert_called_once_with(
            f"Startup browser detection failed: {error_msg}"
        )
        assert mock_provide_url_converter._browser_available is False
