import pytest
from litestar import Litestar
from litestar.testing import TestClient
from unittest.mock import patch

from md_server.core.config import Settings
from md_server.middleware.auth import create_auth_middleware


class TestAuthMiddlewareRealFlow:
    """Test real authentication flow end-to-end with actual middleware"""

    @pytest.fixture
    def auth_app(self):
        """Create app instance with authentication enabled"""
        test_api_key = "test-key-123"

        with patch("md_server.core.config.get_settings") as mock_settings:
            settings = Settings(api_key=test_api_key)
            mock_settings.return_value = settings

            # Import app fresh with mocked settings
            from md_server.app import health, healthz, formats, ConvertController
            from md_server.app import provide_converter, provide_md_converter
            from litestar.di import Provide

            def provide_settings():
                return settings

            middleware = []
            auth_middleware_class = create_auth_middleware(settings)
            if auth_middleware_class:
                middleware.append(auth_middleware_class)

            test_app = Litestar(
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

            yield test_app, test_api_key

    @pytest.fixture
    def client(self, auth_app):
        """Test client with authentication middleware"""
        app, api_key = auth_app
        return TestClient(app), api_key

    def test_missing_authorization_header_returns_401(self, client):
        """Test missing Authorization header returns 401"""
        test_client, _ = client

        response = test_client.post(
            "/convert", json={"text": "test content", "mime_type": "text/plain"}
        )

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "Missing Authorization header" in str(data["detail"])

    def test_invalid_bearer_format_returns_401(self, client):
        """Test invalid Bearer format (e.g., Basic auth) returns 401"""
        test_client, _ = client

        # Test Basic auth instead of Bearer
        response = test_client.post(
            "/convert",
            json={"text": "test content", "mime_type": "text/plain"},
            headers={"Authorization": "Basic dXNlcjpwYXNzd29yZA=="},
        )

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "Invalid Authorization header format" in str(data["detail"])

    def test_empty_bearer_token_returns_401(self, client):
        """Test empty Bearer token returns 401"""
        test_client, _ = client

        response = test_client.post(
            "/convert",
            json={"text": "test content", "mime_type": "text/plain"},
            headers={"Authorization": "Bearer "},
        )

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "Invalid API key" in str(data["detail"])

    def test_malformed_authorization_header_returns_401(self, client):
        """Test malformed authorization header returns 401"""
        test_client, _ = client

        test_cases = [
            "Bearer",  # No space after Bearer
            "NotBearer token",  # Wrong scheme
            "Bearer\ttoken",  # Tab instead of space
            "",  # Empty header
        ]

        for auth_header in test_cases:
            response = test_client.post(
                "/convert",
                json={"text": "test content", "mime_type": "text/plain"},
                headers={"Authorization": auth_header},
            )

            assert response.status_code == 401
            data = response.json()
            assert "detail" in data

    def test_wrong_api_key_returns_401(self, client):
        """Test wrong API key returns 401"""
        test_client, api_key = client
        wrong_key = "wrong-" + api_key

        response = test_client.post(
            "/convert",
            json={"text": "test content", "mime_type": "text/plain"},
            headers={"Authorization": f"Bearer {wrong_key}"},
        )

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "Invalid API key" in str(data["detail"])

    def test_correct_api_key_returns_200(self, client):
        """Test correct API key returns 200"""
        test_client, api_key = client

        response = test_client.post(
            "/convert",
            json={"text": "test content", "mime_type": "text/plain"},
            headers={"Authorization": f"Bearer {api_key}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "markdown" in data
        assert data["markdown"] == "test content"

    def test_api_key_case_sensitivity(self, client):
        """Test API key is case sensitive"""
        test_client, api_key = client
        wrong_case_key = api_key.upper() if api_key.islower() else api_key.lower()

        response = test_client.post(
            "/convert",
            json={"text": "test content", "mime_type": "text/plain"},
            headers={"Authorization": f"Bearer {wrong_case_key}"},
        )

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "Invalid API key" in str(data["detail"])

    def test_bearer_token_with_extra_spaces(self, client):
        """Test Bearer token handling with extra spaces"""
        test_client, api_key = client

        # Extra spaces should be handled correctly
        response = test_client.post(
            "/convert",
            json={"text": "test content", "mime_type": "text/plain"},
            headers={"Authorization": f"Bearer  {api_key}"},  # Extra space
        )

        # The token would include the extra space, so it should fail
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "Invalid API key" in str(data["detail"])

    def test_multiple_authorization_headers(self, client):
        """Test handling of multiple Authorization headers"""
        test_client, api_key = client

        # HTTP spec allows multiple headers with same name
        # Most clients/servers join them or use the last one
        # Let's test behavior rather than assume implementation
        response = test_client.post(
            "/convert",
            json={"text": "test content", "mime_type": "text/plain"},
            headers=[
                ("Authorization", f"Bearer {api_key}"),
                ("Authorization", "Bearer wrong-key"),
            ],
        )

        # The result depends on implementation - either succeeds or fails
        # Both behaviors are acceptable
        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
        else:
            data = response.json()
            assert "detail" in data

    def test_non_json_request_with_auth(self, client):
        """Test authentication works for non-JSON requests"""
        test_client, api_key = client

        # Binary file upload with authentication
        response = test_client.post(
            "/convert",
            content=b"test binary content",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "text/plain",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_multipart_upload_with_auth(self, client):
        """Test multipart form upload with authentication"""
        test_client, api_key = client

        response = test_client.post(
            "/convert",
            files={"file": ("test.txt", "test content", "text/plain")},
            headers={"Authorization": f"Bearer {api_key}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "markdown" in data

    def test_auth_with_url_conversion(self, client):
        """Test authentication with URL conversion request"""
        test_client, api_key = client

        response = test_client.post(
            "/convert",
            json={"url": "https://example.com"},
            headers={"Authorization": f"Bearer {api_key}"},
        )

        # Should be authenticated and proceed to URL conversion
        # (might fail due to network/SDK issues but auth should pass)
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
        else:
            # If it fails, should be a conversion error, not auth error
            assert response.status_code != 401
