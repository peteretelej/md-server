from unittest.mock import patch
from litestar import Litestar, get
from litestar.testing import TestClient
from litestar.response import Response
from litestar.status_codes import HTTP_200_OK, HTTP_401_UNAUTHORIZED

from md_server.core.config import Settings
from md_server.middleware.auth import create_auth_middleware


@get("/test")
async def test_endpoint() -> Response:
    """Test endpoint that should require authentication"""
    return Response({"message": "authenticated"}, status_code=HTTP_200_OK)


@get("/healthz")
async def healthz() -> Response:
    """Health check endpoint that should not require authentication"""
    return Response({"status": "healthy"}, status_code=HTTP_200_OK)


class TestAPIKeyMiddleware:
    def create_app(self, api_key: str = None) -> Litestar:
        """Create test app with optional API key authentication"""
        settings = Settings(api_key=api_key)
        middleware = []
        auth_middleware = create_auth_middleware(settings)
        if auth_middleware:
            middleware.append(auth_middleware)

        return Litestar(
            route_handlers=[test_endpoint, healthz],
            middleware=middleware,
            state={"config": settings},
        )

    def test_no_auth_when_api_key_not_configured(self):
        """Test that no authentication is required when API key is not configured"""
        app = self.create_app(api_key=None)

        with TestClient(app=app) as client:
            # Both endpoints should be accessible without auth
            response = client.get("/test")
            assert response.status_code == HTTP_200_OK
            assert response.json() == {"message": "authenticated"}

            response = client.get("/healthz")
            assert response.status_code == HTTP_200_OK
            assert response.json() == {"status": "healthy"}

    def test_health_check_without_auth_when_api_key_configured(self):
        """Test that health check endpoint is accessible without auth even when API key is configured"""
        app = self.create_app(api_key="test-secret-key")

        with TestClient(app=app) as client:
            response = client.get("/healthz")
            assert response.status_code == HTTP_200_OK
            assert response.json() == {"status": "healthy"}

    def test_protected_endpoint_requires_auth_when_api_key_configured(self):
        """Test that protected endpoints require authentication when API key is configured"""
        app = self.create_app(api_key="test-secret-key")

        with TestClient(app=app) as client:
            # Should get 401 without authorization header
            response = client.get("/test")
            assert response.status_code == HTTP_401_UNAUTHORIZED

    def test_valid_api_key_grants_access(self):
        """Test that valid API key grants access to protected endpoints"""
        app = self.create_app(api_key="test-secret-key")

        with TestClient(app=app) as client:
            response = client.get(
                "/test", headers={"Authorization": "Bearer test-secret-key"}
            )
            assert response.status_code == HTTP_200_OK
            assert response.json() == {"message": "authenticated"}

    def test_invalid_api_key_denies_access(self):
        """Test that invalid API key denies access"""
        app = self.create_app(api_key="test-secret-key")

        with TestClient(app=app) as client:
            response = client.get(
                "/test", headers={"Authorization": "Bearer wrong-key"}
            )
            assert response.status_code == HTTP_401_UNAUTHORIZED

    def test_missing_authorization_header_denies_access(self):
        """Test that missing Authorization header denies access"""
        app = self.create_app(api_key="test-secret-key")

        with TestClient(app=app) as client:
            response = client.get("/test")
            assert response.status_code == HTTP_401_UNAUTHORIZED

    def test_invalid_authorization_format_denies_access(self):
        """Test that invalid Authorization header format denies access"""
        app = self.create_app(api_key="test-secret-key")

        with TestClient(app=app) as client:
            # Test with wrong format (should be "Bearer token")
            response = client.get(
                "/test", headers={"Authorization": "Basic test-secret-key"}
            )
            assert response.status_code == HTTP_401_UNAUTHORIZED

            response = client.get("/test", headers={"Authorization": "test-secret-key"})
            assert response.status_code == HTTP_401_UNAUTHORIZED

    def test_empty_bearer_token_denies_access(self):
        """Test that empty Bearer token denies access"""
        app = self.create_app(api_key="test-secret-key")

        with TestClient(app=app) as client:
            response = client.get("/test", headers={"Authorization": "Bearer "})
            assert response.status_code == HTTP_401_UNAUTHORIZED

    def test_case_sensitive_bearer_prefix(self):
        """Test that Bearer prefix is case sensitive"""
        app = self.create_app(api_key="test-secret-key")

        with TestClient(app=app) as client:
            response = client.get(
                "/test", headers={"Authorization": "bearer test-secret-key"}
            )
            assert response.status_code == HTTP_401_UNAUTHORIZED

    def test_api_key_from_environment(self):
        """Test API key loading from environment variables"""
        with patch.dict("os.environ", {"MD_SERVER_API_KEY": "env-secret-key"}):
            settings = Settings()
            assert settings.api_key == "env-secret-key"

            app = self.create_app(api_key=settings.api_key)

            with TestClient(app=app) as client:
                response = client.get(
                    "/test", headers={"Authorization": "Bearer env-secret-key"}
                )
                assert response.status_code == HTTP_200_OK
                assert response.json() == {"message": "authenticated"}
