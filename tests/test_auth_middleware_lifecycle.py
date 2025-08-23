import pytest
from litestar import Litestar
from litestar.testing import TestClient
from unittest.mock import patch, MagicMock
from litestar.connection import ASGIConnection
from litestar.types import ASGIApp

from md_server.core.config import Settings
from md_server.middleware.auth import APIKeyMiddleware, create_auth_middleware


class TestAuthMiddlewareLifecycle:
    """Test authentication middleware setup and lifecycle"""

    def test_middleware_creation_with_api_key(self):
        """Test middleware creation with API key configured"""
        settings = Settings(api_key="test-key")
        
        middleware_class = create_auth_middleware(settings)
        
        assert middleware_class is not None
        assert issubclass(middleware_class, APIKeyMiddleware)
        
        # Test middleware instantiation
        mock_app = MagicMock(spec=ASGIApp)
        middleware = middleware_class(mock_app)
        assert middleware is not None

    def test_middleware_creation_without_api_key(self):
        """Test middleware creation without API key configured"""
        settings = Settings()  # No API key
        
        middleware_class = create_auth_middleware(settings)
        
        assert middleware_class is None

    def test_middleware_creation_with_empty_api_key(self):
        """Test middleware creation with empty API key"""
        settings = Settings(api_key="")
        
        middleware_class = create_auth_middleware(settings)
        
        assert middleware_class is None

    def test_middleware_creation_with_none_api_key(self):
        """Test middleware creation with None API key"""
        settings = Settings(api_key=None)
        
        middleware_class = create_auth_middleware(settings)
        
        assert middleware_class is None

    def test_excluded_paths_configuration(self):
        """Test excluded paths are properly configured"""
        settings = Settings(api_key="test-key")
        
        middleware_class = create_auth_middleware(settings)
        mock_app = MagicMock(spec=ASGIApp)
        middleware = middleware_class(mock_app)
        
        # The ConfiguredAPIKeyMiddleware should exclude /health and /healthz
        # The exclude attribute is a regex pattern
        exclude_pattern = middleware.exclude.pattern
        assert "/health" in exclude_pattern
        assert "/healthz" in exclude_pattern

    def test_health_endpoint_bypasses_authentication(self):
        """Test health endpoint bypasses authentication"""
        settings = Settings(api_key="test-api-key")
        
        with patch('md_server.core.config.get_settings') as mock_settings:
            mock_settings.return_value = settings
            
            from md_server.app import health, healthz, formats, ConvertController
            from md_server.app import provide_converter, provide_md_converter
            from litestar.di import Provide
            
            def provide_settings():
                return settings
            
            middleware = []
            auth_middleware_class = create_auth_middleware(settings)
            if auth_middleware_class:
                middleware.append(auth_middleware_class)
            
            app = Litestar(
                route_handlers=[health, healthz, formats, ConvertController],
                dependencies={
                    "converter": Provide(provide_converter, sync_to_thread=False),
                    "settings": Provide(provide_settings, sync_to_thread=False),
                    "md_converter": Provide(provide_md_converter, sync_to_thread=False),
                },
                middleware=middleware,
                debug=False,
                state={"config": settings},
            )
            
            client = TestClient(app)
            
            # Health endpoint should work without authentication
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"

    def test_healthz_endpoint_bypasses_authentication(self):
        """Test legacy healthz endpoint bypasses authentication"""
        settings = Settings(api_key="test-api-key")
        
        with patch('md_server.core.config.get_settings') as mock_settings:
            mock_settings.return_value = settings
            
            from md_server.app import health, healthz, formats, ConvertController
            from md_server.app import provide_converter, provide_md_converter
            from litestar.di import Provide
            
            def provide_settings():
                return settings
            
            middleware = []
            auth_middleware_class = create_auth_middleware(settings)
            if auth_middleware_class:
                middleware.append(auth_middleware_class)
            
            app = Litestar(
                route_handlers=[health, healthz, formats, ConvertController],
                dependencies={
                    "converter": Provide(provide_converter, sync_to_thread=False),
                    "settings": Provide(provide_settings, sync_to_thread=False),
                    "md_converter": Provide(provide_md_converter, sync_to_thread=False),
                },
                middleware=middleware,
                debug=False,
                state={"config": settings},
            )
            
            client = TestClient(app)
            
            # Healthz endpoint should work without authentication
            response = client.get("/healthz")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"

    def test_formats_endpoint_requires_authentication(self):
        """Test formats endpoint requires authentication when auth is enabled"""
        settings = Settings(api_key="test-api-key")
        
        with patch('md_server.core.config.get_settings') as mock_settings:
            mock_settings.return_value = settings
            
            from md_server.app import health, healthz, formats, ConvertController
            from md_server.app import provide_converter, provide_md_converter
            from litestar.di import Provide
            
            def provide_settings():
                return settings
            
            middleware = []
            auth_middleware_class = create_auth_middleware(settings)
            if auth_middleware_class:
                middleware.append(auth_middleware_class)
            
            app = Litestar(
                route_handlers=[health, healthz, formats, ConvertController],
                dependencies={
                    "converter": Provide(provide_converter, sync_to_thread=False),
                    "settings": Provide(provide_settings, sync_to_thread=False),
                    "md_converter": Provide(provide_md_converter, sync_to_thread=False),
                },
                middleware=middleware,
                debug=False,
                state={"config": settings},
            )
            
            client = TestClient(app)
            
            # Formats endpoint should require authentication
            response = client.get("/formats")
            assert response.status_code == 401
            
            # With valid auth, should work
            response = client.get("/formats", headers={"Authorization": "Bearer test-api-key"})
            assert response.status_code == 200
            data = response.json()
            assert "formats" in data

    def test_convert_endpoint_requires_authentication(self):
        """Test convert endpoint requires authentication when auth is enabled"""
        settings = Settings(api_key="test-api-key")
        
        with patch('md_server.core.config.get_settings') as mock_settings:
            mock_settings.return_value = settings
            
            from md_server.app import health, healthz, formats, ConvertController
            from md_server.app import provide_converter, provide_md_converter
            from litestar.di import Provide
            
            def provide_settings():
                return settings
            
            middleware = []
            auth_middleware_class = create_auth_middleware(settings)
            if auth_middleware_class:
                middleware.append(auth_middleware_class)
            
            app = Litestar(
                route_handlers=[health, healthz, formats, ConvertController],
                dependencies={
                    "converter": Provide(provide_converter, sync_to_thread=False),
                    "settings": Provide(provide_settings, sync_to_thread=False),
                    "md_converter": Provide(provide_md_converter, sync_to_thread=False),
                },
                middleware=middleware,
                debug=False,
                state={"config": settings},
            )
            
            client = TestClient(app)
            
            # Convert endpoint should require authentication
            response = client.post("/convert", json={"text": "test", "mime_type": "text/plain"})
            assert response.status_code == 401
            
            # With valid auth, should work
            response = client.post(
                "/convert",
                json={"text": "test", "mime_type": "text/plain"},
                headers={"Authorization": "Bearer test-api-key"}
            )
            assert response.status_code == 200

    def test_api_key_middleware_initialization(self):
        """Test APIKeyMiddleware initialization"""
        mock_app = MagicMock(spec=ASGIApp)
        
        # Test with default exclude paths
        middleware = APIKeyMiddleware(mock_app)
        # Default is empty set, which becomes a pattern that matches nothing
        assert hasattr(middleware.exclude, 'pattern')
        
        # Test with custom exclude paths
        exclude_paths = {"/health", "/status"}
        middleware = APIKeyMiddleware(mock_app, exclude_paths=exclude_paths)
        exclude_pattern = middleware.exclude.pattern
        assert "/health" in exclude_pattern
        assert "/status" in exclude_pattern

    def test_authentication_result_structure(self):
        """Test authentication result structure"""
        settings = Settings(api_key="test-key")
        mock_app = MagicMock(spec=ASGIApp)
        middleware = APIKeyMiddleware(mock_app)
        
        # Mock connection with valid auth
        mock_connection = MagicMock(spec=ASGIConnection)
        mock_connection.app.state = {"config": settings}
        mock_connection.headers.get.return_value = "Bearer test-key"
        
        import asyncio
        result = asyncio.run(middleware.authenticate_request(mock_connection))
        
        assert result.user == "authenticated"
        assert result.auth == "test-key"

    def test_authentication_without_api_key_configured(self):
        """Test authentication when no API key is configured in settings"""
        settings = Settings()  # No API key
        mock_app = MagicMock(spec=ASGIApp)
        middleware = APIKeyMiddleware(mock_app)
        
        # Mock connection without API key requirement
        mock_connection = MagicMock(spec=ASGIConnection)
        mock_connection.app.state = {"config": settings}
        
        import asyncio
        result = asyncio.run(middleware.authenticate_request(mock_connection))
        
        assert result.user is None
        assert result.auth is None

    def test_app_integration_without_api_key(self):
        """Test app runs normally without API key configured"""
        settings = Settings()  # No API key
        
        with patch('md_server.core.config.get_settings') as mock_settings:
            mock_settings.return_value = settings
            
            from md_server.app import health, healthz, formats, ConvertController
            from md_server.app import provide_converter, provide_md_converter
            from litestar.di import Provide
            
            def provide_settings():
                return settings
            
            middleware = []
            auth_middleware_class = create_auth_middleware(settings)
            # Should be None, so no middleware added
            if auth_middleware_class:
                middleware.append(auth_middleware_class)
            
            app = Litestar(
                route_handlers=[health, healthz, formats, ConvertController],
                dependencies={
                    "converter": Provide(provide_converter, sync_to_thread=False),
                    "settings": Provide(provide_settings, sync_to_thread=False),
                    "md_converter": Provide(provide_md_converter, sync_to_thread=False),
                },
                middleware=middleware,  # Should be empty
                debug=False,
                state={"config": settings},
            )
            
            client = TestClient(app)
            
            # All endpoints should work without authentication
            response = client.get("/health")
            assert response.status_code == 200
            
            response = client.get("/formats")
            assert response.status_code == 200
            
            response = client.post("/convert", json={"text": "test", "mime_type": "text/plain"})
            assert response.status_code == 200

    def test_middleware_error_handling_on_invalid_app_state(self):
        """Test middleware handles missing app state gracefully"""
        mock_app = MagicMock(spec=ASGIApp)
        middleware = APIKeyMiddleware(mock_app)
        
        # Mock connection with missing state
        mock_connection = MagicMock(spec=ASGIConnection)
        mock_connection.app.state = {}  # Missing 'config'
        
        import asyncio
        with pytest.raises(KeyError):
            asyncio.run(middleware.authenticate_request(mock_connection))

    def test_middleware_custom_exclude_paths(self):
        """Test middleware with custom exclude paths"""
        # Create custom middleware class with different exclude paths
        class CustomAPIKeyMiddleware(APIKeyMiddleware):
            def __init__(self, app: ASGIApp):
                super().__init__(app, exclude_paths={"/custom", "/healthz"})
        
        mock_app = MagicMock(spec=ASGIApp)
        middleware = CustomAPIKeyMiddleware(mock_app)
        
        exclude_pattern = middleware.exclude.pattern
        assert "/custom" in exclude_pattern
        assert "/healthz" in exclude_pattern