from litestar.exceptions import NotAuthorizedException
from litestar.middleware.authentication import (
    AbstractAuthenticationMiddleware,
    AuthenticationResult,
)
from litestar.connection import ASGIConnection
from litestar.types import ASGIApp
from typing import Optional

from ..core.config import Settings


class APIKeyMiddleware(AbstractAuthenticationMiddleware):
    """Authentication middleware that validates API keys from Authorization header"""

    def __init__(self, app: ASGIApp, exclude_paths: Optional[set] = None):
        super().__init__(app, exclude=exclude_paths or set())

    async def authenticate_request(
        self, connection: ASGIConnection
    ) -> AuthenticationResult:
        """Extract and validate API key from Authorization header"""
        settings = connection.app.state["config"]

        if not settings.api_key:
            return AuthenticationResult(user=None, auth=None)

        auth_header = connection.headers.get("authorization")
        if not auth_header:
            raise NotAuthorizedException("Missing Authorization header")

        if not auth_header.startswith("Bearer "):
            raise NotAuthorizedException("Invalid Authorization header format")

        token = auth_header[7:]  # Remove "Bearer " prefix

        if token != settings.api_key:
            raise NotAuthorizedException("Invalid API key")

        return AuthenticationResult(user="authenticated", auth=token)


def create_auth_middleware(settings: Settings):
    """Factory function to create authentication middleware class if API key is configured"""
    if settings.api_key:

        class ConfiguredAPIKeyMiddleware(APIKeyMiddleware):
            def __init__(self, app: ASGIApp):
                super().__init__(app, exclude_paths={"/health", "/healthz"})

        return ConfiguredAPIKeyMiddleware
    return None
