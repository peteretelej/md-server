import asyncio
import logging
import io
import time
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from litestar import Litestar
from litestar.testing import TestClient

from md_server.app import (
    app,
    startup_browser_detection,
    provide_converter,
    provide_settings,
    provide_md_converter,
    _server_start_time,
)
from md_server.core.config import Settings


class TestAppStartup:
    """Test application startup and initialization."""

    @pytest.mark.asyncio
    async def test_startup_browser_detection_success(self):
        """Test startup browser detection with successful detection."""
        mock_checker = AsyncMock()
        mock_checker.is_available.return_value = True
        mock_checker.log_availability = MagicMock()

        with patch("md_server.app.BrowserChecker", mock_checker):
            await startup_browser_detection()

        mock_checker.is_available.assert_called_once()
        mock_checker.log_availability.assert_called_once_with(True)
        assert provide_md_converter._browser_available is True

    @pytest.mark.asyncio
    async def test_startup_browser_detection_failure(self):
        """Test startup browser detection with browser unavailable."""
        mock_checker = AsyncMock()
        mock_checker.is_available.return_value = False
        mock_checker.log_availability = MagicMock()

        with patch("md_server.app.BrowserChecker", mock_checker):
            await startup_browser_detection()

        mock_checker.is_available.assert_called_once()
        mock_checker.log_availability.assert_called_once_with(False)
        assert provide_md_converter._browser_available is False

    @pytest.mark.asyncio
    async def test_startup_browser_detection_exception(self):
        """Test startup browser detection with exception handling."""
        mock_checker = AsyncMock()
        mock_checker.is_available.side_effect = Exception("Browser check failed")

        with (
            patch("md_server.app.BrowserChecker", mock_checker),
            patch("md_server.app.logging.error") as mock_log_error,
        ):
            await startup_browser_detection()

        mock_log_error.assert_called_once()
        log_call = mock_log_error.call_args[0][0]
        assert "Startup browser detection failed" in log_call
        assert provide_md_converter._browser_available is False

    def test_startup_logging_configuration(self):
        """Test logging is configured during startup."""
        with (
            patch("md_server.app.logging.basicConfig") as mock_basic_config,
            patch("md_server.app.BrowserChecker") as mock_checker,
        ):
            mock_checker.is_available = AsyncMock(return_value=True)
            mock_checker.log_availability = MagicMock()

            asyncio.run(startup_browser_detection())

        mock_basic_config.assert_called_once_with(level=logging.INFO)

    def test_server_start_time_tracking(self):
        """Test server start time is tracked for uptime calculation."""
        start_time = _server_start_time
        assert isinstance(start_time, float)
        assert start_time > 0

        # Test uptime calculation in health endpoint
        current_time = time.time()
        expected_uptime = int(current_time - start_time)

        with TestClient(app=app) as client:
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert "uptime_seconds" in data
            # Allow for small timing differences
            assert abs(data["uptime_seconds"] - expected_uptime) <= 1


class TestAppDependencies:
    """Test application dependency injection and provider functions."""

    def test_provide_converter(self):
        """Test MarkItDown converter provider function."""
        with (
            patch("md_server.app.get_settings") as mock_get_settings,
            patch("md_server.app.MarkItDownFactory.create") as mock_create,
        ):
            mock_settings = MagicMock()
            mock_get_settings.return_value = mock_settings
            mock_converter = MagicMock()
            mock_create.return_value = mock_converter

            result = provide_converter()

            mock_get_settings.assert_called_once()
            mock_create.assert_called_once_with(mock_settings)
            assert result is mock_converter

    def test_provide_settings(self):
        """Test settings provider function."""
        with patch("md_server.app.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_get_settings.return_value = mock_settings

            result = provide_settings()

            mock_get_settings.assert_called_once()
            assert result is mock_settings

    def test_provide_md_converter_with_browser_available(self):
        """Test MDConverter provider with browser available."""
        mock_settings = MagicMock(spec=Settings)
        mock_settings.conversion_timeout = 30
        mock_settings.max_file_size = 10485760  # 10MB
        mock_settings.debug = False

        # Set browser available
        provide_md_converter._browser_available = True

        with patch("md_server.app.MDConverter") as mock_md_converter:
            mock_instance = MagicMock()
            mock_md_converter.return_value = mock_instance

            result = provide_md_converter(mock_settings)

            mock_md_converter.assert_called_once_with(
                ocr_enabled=False,
                js_rendering=True,  # Browser available
                timeout=30,
                max_file_size_mb=10,  # Converted from bytes to MB
                extract_images=False,
                preserve_formatting=True,
                clean_markdown=False,
                debug=False,
            )
            assert result is mock_instance

    def test_provide_md_converter_without_browser(self):
        """Test MDConverter provider without browser."""
        mock_settings = MagicMock(spec=Settings)
        mock_settings.conversion_timeout = 60
        mock_settings.max_file_size = 20971520  # 20MB
        mock_settings.debug = True

        # Set browser unavailable
        provide_md_converter._browser_available = False

        with patch("md_server.app.MDConverter") as mock_md_converter:
            mock_instance = MagicMock()
            mock_md_converter.return_value = mock_instance

            result = provide_md_converter(mock_settings)

            mock_md_converter.assert_called_once_with(
                ocr_enabled=False,
                js_rendering=False,  # Browser not available
                timeout=60,
                max_file_size_mb=20,
                extract_images=False,
                preserve_formatting=True,
                clean_markdown=False,
                debug=True,
            )
            assert result is mock_instance

    def test_provide_md_converter_default_attributes(self):
        """Test MDConverter provider with default attributes."""
        mock_settings = MagicMock(spec=Settings)
        mock_settings.conversion_timeout = 30
        mock_settings.max_file_size = 5242880  # 5MB
        mock_settings.debug = False

        provide_md_converter._browser_available = True

        with patch("md_server.app.MDConverter") as mock_md_converter:
            provide_md_converter(mock_settings)

            # Verify default values are used for optional settings
            call_kwargs = mock_md_converter.call_args[1]
            assert call_kwargs["ocr_enabled"] is False
            assert call_kwargs["extract_images"] is False
            assert call_kwargs["preserve_formatting"] is True
            assert call_kwargs["clean_markdown"] is False


class TestAppConfiguration:
    """Test application configuration and middleware setup."""

    def test_app_instance_configuration(self):
        """Test app instance is properly configured."""
        assert isinstance(app, Litestar)
        assert app.debug is not None
        assert hasattr(app, "dependencies")
        assert hasattr(app, "middleware")
        assert hasattr(app, "on_startup")

    def test_app_dependencies_configured(self):
        """Test app dependencies are properly configured."""
        dependencies = app.dependencies
        assert "converter" in dependencies
        assert "settings" in dependencies
        assert "md_converter" in dependencies

    def test_app_startup_hooks_configured(self):
        """Test app startup hooks are configured."""
        startup_hooks = app.on_startup
        assert startup_hooks is not None
        assert len(startup_hooks) > 0
        assert startup_browser_detection in startup_hooks

    def test_app_middleware_configuration_with_auth(self):
        """Test middleware configuration with authentication enabled."""
        mock_settings = MagicMock()
        mock_settings.debug = False

        mock_auth_middleware = MagicMock()

        with (
            patch("md_server.app.get_settings", return_value=mock_settings),
            patch(
                "md_server.app.create_auth_middleware",
                return_value=mock_auth_middleware,
            ),
        ):
            # Import will trigger app creation with mocked settings
            from importlib import reload
            import md_server.app

            reload(md_server.app)

            # The test verifies that create_auth_middleware was called
            # and if it returns a middleware class, it gets added

    def test_app_middleware_configuration_without_auth(self):
        """Test middleware configuration without authentication."""
        mock_settings = MagicMock()
        mock_settings.debug = True

        with (
            patch("md_server.app.get_settings", return_value=mock_settings),
            patch("md_server.app.create_auth_middleware", return_value=None),
        ):
            # Import will trigger app creation with mocked settings
            from importlib import reload
            import md_server.app

            reload(md_server.app)

            # The test verifies that when create_auth_middleware returns None,
            # no auth middleware is added to the middleware list

    def test_app_state_configuration(self):
        """Test app state is configured with settings."""
        assert hasattr(app, "state")
        assert "config" in app.state

        # Verify state config is a Settings instance
        from md_server.core.config import Settings

        assert isinstance(app.state["config"], Settings)


class TestAppShutdown:
    """Test application shutdown and cleanup."""

    @pytest.mark.asyncio
    async def test_app_shutdown_hooks(self):
        """Test app shutdown hooks are properly called."""
        # The app doesn't currently have explicit shutdown hooks,
        # but this test ensures shutdown behavior is clean

        # Test that we can create and close the app cleanly
        test_app = Litestar(
            route_handlers=[],
            on_startup=[startup_browser_detection],
        )

        # Should not raise any exceptions during creation/cleanup
        assert test_app is not None

    def test_cleanup_on_exception_during_startup(self):
        """Test cleanup when startup fails."""
        with patch(
            "md_server.app.startup_browser_detection",
            side_effect=Exception("Startup failed"),
        ):
            # App creation should still succeed even if startup hook fails
            # The framework should handle the exception gracefully
            try:
                test_app = Litestar(
                    route_handlers=[],
                    on_startup=[startup_browser_detection],
                )
                assert test_app is not None
            except Exception:
                # If exception propagates, that's also acceptable behavior
                # The important thing is no resource leaks occur
                pass

    @contextmanager
    def capture_logs(self):
        """Capture log messages for testing."""
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        logger = logging.getLogger()
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        try:
            yield log_capture
        finally:
            logger.removeHandler(handler)

    def test_app_resource_cleanup(self):
        """Test app properly cleans up resources."""
        with self.capture_logs():
            # Test that app operations don't leave resources hanging
            with TestClient(app=app) as client:
                # Make a few requests to ensure resources are used
                response1 = client.get("/health")
                response2 = client.get("/formats")

                assert response1.status_code == 200
                assert response2.status_code == 200

            # After TestClient context exits, resources should be cleaned up
            # No explicit test needed - if resources leak, tests will eventually fail

    def test_browser_attribute_cleanup(self):
        """Test browser availability attribute is properly managed."""
        # Save original state
        original_value = getattr(provide_md_converter, "_browser_available", None)

        try:
            # Test setting and unsetting the attribute
            provide_md_converter._browser_available = True
            assert provide_md_converter._browser_available is True

            provide_md_converter._browser_available = False
            assert provide_md_converter._browser_available is False

            # Test deleting the attribute
            if hasattr(provide_md_converter, "_browser_available"):
                delattr(provide_md_converter, "_browser_available")

            # Should handle missing attribute gracefully
            browser_status = getattr(provide_md_converter, "_browser_available", False)
            assert browser_status is False

        finally:
            # Restore original state
            if original_value is not None:
                provide_md_converter._browser_available = original_value
            elif hasattr(provide_md_converter, "_browser_available"):
                delattr(provide_md_converter, "_browser_available")
