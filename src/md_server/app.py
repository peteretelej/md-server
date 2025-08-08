from litestar import Litestar, get
from litestar.di import Provide
from litestar.response import Response
from litestar.status_codes import HTTP_200_OK
from markitdown import MarkItDown
from .core.config import get_settings, Settings
from .controllers import ConvertController


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

app = Litestar(
    route_handlers=[healthz, ConvertController],
    dependencies={
        "converter": Provide(provide_converter, sync_to_thread=False),
        "settings": Provide(provide_settings, sync_to_thread=False),
    },
    debug=settings.debug,
    state={"config": settings},
)
