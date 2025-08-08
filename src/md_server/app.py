from litestar import Litestar, get
from litestar.response import Response
from litestar.status_codes import HTTP_200_OK
from .core.config import get_settings
from .controllers import ConvertController


@get("/healthz")
async def healthz() -> Response:
    """Health check endpoint"""
    return Response({"status": "healthy"}, status_code=HTTP_200_OK)


settings = get_settings()

app = Litestar(
    route_handlers=[healthz, ConvertController],
    debug=settings.debug,
)