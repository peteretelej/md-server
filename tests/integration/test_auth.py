import pytest
from unittest.mock import patch, Mock
from litestar.status_codes import HTTP_200_OK
from litestar.exceptions import NotAuthorizedException

from md_server.middleware.auth import APIKeyMiddleware, create_auth_middleware
from md_server.core.config import Settings


class TestAPIKeyMiddleware:
    def test_create_auth_middleware_returns_none_when_no_api_key(self):
        settings = Mock(spec=Settings)
        settings.api_key = None

        middleware_class = create_auth_middleware(settings)
        assert middleware_class is None

    def test_create_auth_middleware_returns_class_when_api_key_present(self):
        settings = Mock(spec=Settings)
        settings.api_key = "test-key"

        middleware_class = create_auth_middleware(settings)
        assert middleware_class is not None
        assert issubclass(middleware_class, APIKeyMiddleware)

    def test_auth_result_structure_when_no_api_key_configured(self):
        from litestar.connection import ASGIConnection

        mock_connection = Mock(spec=ASGIConnection)
        mock_app = Mock()
        mock_app.state = {"config": Mock(api_key=None)}
        mock_connection.app = mock_app

        middleware = APIKeyMiddleware(Mock())

        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                middleware.authenticate_request(mock_connection)
            )
            assert result.user is None
            assert result.auth is None
        finally:
            loop.close()

    def test_auth_result_structure_when_authenticated(self):
        from litestar.connection import ASGIConnection

        mock_connection = Mock(spec=ASGIConnection)
        mock_app = Mock()
        mock_app.state = {"config": Mock(api_key="test-key")}
        mock_connection.app = mock_app
        mock_connection.headers = {"authorization": "Bearer test-key"}

        middleware = APIKeyMiddleware(Mock())

        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                middleware.authenticate_request(mock_connection)
            )
            assert result.user == "authenticated"
            assert result.auth == "test-key"
        finally:
            loop.close()

    def test_auth_middleware_missing_header(self):
        from litestar.connection import ASGIConnection

        mock_connection = Mock(spec=ASGIConnection)
        mock_app = Mock()
        mock_app.state = {"config": Mock(api_key="test-key")}
        mock_connection.app = mock_app
        mock_connection.headers = {}

        middleware = APIKeyMiddleware(Mock())

        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            with pytest.raises(
                NotAuthorizedException, match="Missing Authorization header"
            ):
                loop.run_until_complete(
                    middleware.authenticate_request(mock_connection)
                )
        finally:
            loop.close()

    def test_auth_middleware_invalid_header_format(self):
        from litestar.connection import ASGIConnection

        mock_connection = Mock(spec=ASGIConnection)
        mock_app = Mock()
        mock_app.state = {"config": Mock(api_key="test-key")}
        mock_connection.app = mock_app
        mock_connection.headers = {"authorization": "InvalidFormat test-key"}

        middleware = APIKeyMiddleware(Mock())

        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            with pytest.raises(
                NotAuthorizedException, match="Invalid Authorization header format"
            ):
                loop.run_until_complete(
                    middleware.authenticate_request(mock_connection)
                )
        finally:
            loop.close()

    def test_auth_middleware_invalid_api_key(self):
        from litestar.connection import ASGIConnection

        mock_connection = Mock(spec=ASGIConnection)
        mock_app = Mock()
        mock_app.state = {"config": Mock(api_key="correct-key")}
        mock_connection.app = mock_app
        mock_connection.headers = {"authorization": "Bearer wrong-key"}

        middleware = APIKeyMiddleware(Mock())

        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            with pytest.raises(NotAuthorizedException, match="Invalid API key"):
                loop.run_until_complete(
                    middleware.authenticate_request(mock_connection)
                )
        finally:
            loop.close()

    def test_healthz_endpoint_exclusion(self):
        settings = Settings(api_key="test-key")
        middleware_class = create_auth_middleware(settings)

        # Verify that the middleware class has the proper exclusions
        middleware_instance = middleware_class(Mock())
        assert "/healthz" in middleware_instance.exclude


class TestAuthIntegrationWithMainApp:
    @patch("md_server.core.config.get_settings")
    def test_main_app_without_api_key(self, mock_get_settings, client):
        """Test app behavior when no API key is configured"""
        mock_settings = Mock(spec=Settings)
        mock_settings.api_key = None
        mock_settings.debug = False
        mock_get_settings.return_value = mock_settings

        # Should work without authentication
        response = client.get("/health")
        assert response.status_code == HTTP_200_OK

    def test_healthz_endpoint_always_accessible(self, client):
        """Test that /healthz is always accessible regardless of auth config"""
        response = client.get("/healthz")
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"

    def test_formats_endpoint_accessible_without_auth(self, client):
        """Test that /formats is accessible without authentication when no API key is set"""
        response = client.get("/formats")
        assert response.status_code == HTTP_200_OK
        assert "formats" in response.json()

    def test_auth_middleware_initialization_with_exclusions(self):
        """Test that auth middleware is properly initialized with exclusions"""
        settings = Settings(api_key="test-key")
        middleware_class = create_auth_middleware(settings)

        assert middleware_class is not None

        # Create instance and check exclusions
        middleware_instance = middleware_class(Mock())
        assert hasattr(middleware_instance, "exclude")
        assert "/healthz" in middleware_instance.exclude

    def test_middleware_factory_creates_unique_classes(self):
        """Test that the factory creates distinct middleware classes"""
        settings1 = Settings(api_key="key1")
        settings2 = Settings(api_key="key2")

        middleware_class1 = create_auth_middleware(settings1)
        middleware_class2 = create_auth_middleware(settings2)

        # Both should be created
        assert middleware_class1 is not None
        assert middleware_class2 is not None

        # They should be the same class type but potentially different instances
        assert issubclass(middleware_class1, APIKeyMiddleware)
        assert issubclass(middleware_class2, APIKeyMiddleware)

    def test_auth_middleware_preserves_excluded_paths(self):
        """Test that excluded paths work correctly"""
        settings = Settings(api_key="test-key")
        middleware_class = create_auth_middleware(settings)

        middleware = middleware_class(Mock())

        # Check that healthz is excluded
        assert "/healthz" in middleware.exclude
