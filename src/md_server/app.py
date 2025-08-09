import os
import requests
from litestar import Litestar, get
from litestar.di import Provide
from litestar.response import Response
from litestar.status_codes import HTTP_200_OK
from markitdown import MarkItDown
from .core.config import get_settings, Settings
from .controllers import ConvertController
from .middleware.auth import create_auth_middleware
from .converter import UrlConverter


@get("/healthz")
async def healthz() -> Response:
    """Health check endpoint"""
    return Response({"status": "healthy"}, status_code=HTTP_200_OK)


def create_requests_session(settings: Settings) -> requests.Session:
    """Create requests session with proxy configuration"""
    session = requests.Session()

    proxies = {}
    if settings.http_proxy:
        proxies["http"] = settings.http_proxy
        os.environ["HTTP_PROXY"] = settings.http_proxy

    if settings.https_proxy:
        proxies["https"] = settings.https_proxy
        os.environ["HTTPS_PROXY"] = settings.https_proxy

    if proxies:
        session.proxies.update(proxies)

    return session


def provide_converter() -> MarkItDown:
    """Provide MarkItDown converter instance as singleton"""
    settings = get_settings()
    session = create_requests_session(settings)
    return MarkItDown(requests_session=session)


def provide_settings() -> Settings:
    """Provide application settings as singleton"""
    return get_settings()


def provide_url_converter(settings: Settings) -> UrlConverter:
    """Provide UrlConverter instance with settings"""
    return UrlConverter(settings)


settings = get_settings()

middleware = []
auth_middleware_class = create_auth_middleware(settings)
if auth_middleware_class:
    middleware.append(auth_middleware_class)

app = Litestar(
    route_handlers=[healthz, ConvertController],
    dependencies={
        "converter": Provide(provide_converter, sync_to_thread=False),
        "settings": Provide(provide_settings, sync_to_thread=False),
        "url_converter": Provide(provide_url_converter, sync_to_thread=False),
    },
    middleware=middleware,
    debug=settings.debug,
    state={"config": settings},
)
