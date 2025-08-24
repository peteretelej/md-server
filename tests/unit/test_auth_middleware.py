import pytest
from unittest.mock import Mock
from litestar.exceptions import NotAuthorizedException
from litestar.connection import ASGIConnection
from litestar.types import ASGIApp

from md_server.middleware.auth import APIKeyMiddleware, create_auth_middleware
from md_server.core.config import Settings


class TestCreateAuthMiddleware:
    def test_auth_middleware_disabled_by_default(self):
        """Test create_auth_middleware returns None when no API key"""
        settings = Settings()
        assert settings.api_key is None
        middleware_class = create_auth_middleware(settings)
        assert middleware_class is None

    def test_auth_middleware_enabled_with_api_key(self):
        """Test middleware creation when API key configured"""
        settings = Settings(api_key="test-api-key-123")
        middleware_class = create_auth_middleware(settings)
        assert middleware_class is not None
        assert issubclass(middleware_class, APIKeyMiddleware)

    def test_configured_middleware_excludes_health_paths(self):
        """Test configured middleware excludes /health and /healthz"""
        settings = Settings(api_key="test-api-key-123")
        middleware_class = create_auth_middleware(settings)

        mock_app = Mock(spec=ASGIApp)
        middleware = middleware_class(mock_app)

        # The exclude pattern is a compiled regex, check if it matches health paths
        assert middleware.exclude.match("/health")
        assert middleware.exclude.match("/healthz")


class TestAPIKeyMiddleware:
    def create_mock_connection(self, headers=None, settings=None):
        """Helper to create mock connection"""
        mock_connection = Mock(spec=ASGIConnection)
        mock_connection.headers = headers or {}

        mock_app = Mock()
        mock_app.state = {"config": settings or Settings()}
        mock_connection.app = mock_app

        return mock_connection

    @pytest.mark.asyncio
    async def test_authentication_success_with_valid_key(self):
        """Test successful Bearer token authentication"""
        settings = Settings(api_key="valid-key-123")
        middleware = APIKeyMiddleware(Mock(spec=ASGIApp))

        connection = self.create_mock_connection(
            headers={"authorization": "Bearer valid-key-123"}, settings=settings
        )

        result = await middleware.authenticate_request(connection)
        assert result.user == "authenticated"
        assert result.auth == "valid-key-123"

    @pytest.mark.asyncio
    async def test_authentication_bypassed_when_no_api_key_configured(self):
        """Test authentication bypass when no API key in settings"""
        settings = Settings()  # No api_key set
        middleware = APIKeyMiddleware(Mock(spec=ASGIApp))

        connection = self.create_mock_connection(settings=settings)

        result = await middleware.authenticate_request(connection)
        assert result.user is None
        assert result.auth is None

    @pytest.mark.asyncio
    async def test_authentication_failure_missing_header(self):
        """Test missing Authorization header"""
        settings = Settings(api_key="test-key")
        middleware = APIKeyMiddleware(Mock(spec=ASGIApp))

        connection = self.create_mock_connection(
            headers={},  # No authorization header
            settings=settings,
        )

        with pytest.raises(NotAuthorizedException) as exc_info:
            await middleware.authenticate_request(connection)
        assert "Missing Authorization header" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_authentication_failure_invalid_format(self):
        """Test invalid Authorization header format"""
        settings = Settings(api_key="test-key")
        middleware = APIKeyMiddleware(Mock(spec=ASGIApp))

        connection = self.create_mock_connection(
            headers={"authorization": "Basic invalid-format"}, settings=settings
        )

        with pytest.raises(NotAuthorizedException) as exc_info:
            await middleware.authenticate_request(connection)
        assert "Invalid Authorization header format" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_authentication_failure_wrong_key(self):
        """Test wrong API key"""
        settings = Settings(api_key="correct-key")
        middleware = APIKeyMiddleware(Mock(spec=ASGIApp))

        connection = self.create_mock_connection(
            headers={"authorization": "Bearer wrong-key"}, settings=settings
        )

        with pytest.raises(NotAuthorizedException) as exc_info:
            await middleware.authenticate_request(connection)
        assert "Invalid API key" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_authentication_failure_empty_bearer_token(self):
        """Test empty Bearer token"""
        settings = Settings(api_key="test-key")
        middleware = APIKeyMiddleware(Mock(spec=ASGIApp))

        connection = self.create_mock_connection(
            headers={"authorization": "Bearer "}, settings=settings
        )

        with pytest.raises(NotAuthorizedException) as exc_info:
            await middleware.authenticate_request(connection)
        assert "Invalid API key" in str(exc_info.value)
