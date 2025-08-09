from litestar import Litestar, get
from litestar.di import Provide
from litestar.response import Response
from litestar.status_codes import HTTP_200_OK
from markitdown import MarkItDown
from .core.config import get_settings, Settings
from .controllers import ConvertController
from .middleware.auth import create_auth_middleware


@get("/healthz")
async def healthz() -> Response:
    """Health check endpoint"""
    return Response({"status": "healthy"}, status_code=HTTP_200_OK)


def provide_converter() -> MarkItDown:
    """Provide MarkItDown converter instance as singleton"""
    return MarkItDown()


def provide_settings() -> Settings:
    """Provide application settings as singleton"""
    return get_settings()


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
    },
    middleware=middleware,
    debug=settings.debug,
    state={"config": settings},
)
