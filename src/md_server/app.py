import logging
import time
from litestar import Litestar, get
from litestar.di import Provide
from litestar.response import Response
from litestar.status_codes import HTTP_200_OK
from markitdown import MarkItDown
from .core.config import get_settings, Settings
from .controllers import ConvertController
from .middleware.auth import create_auth_middleware
from .core.browser import BrowserChecker
from .models import HealthResponse, FormatsResponse, SystemCapabilities
from .core.detection import ContentTypeDetector
from .core.factories import MarkItDownFactory
from .core.converter import DocumentConverter

# Track server start time for uptime calculation
_server_start_time = time.time()


@get("/health")
async def health() -> Response[HealthResponse]:
    """Health check endpoint with detailed information"""
    uptime = int(time.time() - _server_start_time)
    health_data = HealthResponse(
        status="healthy",
        version="0.1.0",  # TODO: Get this from package metadata
        uptime_seconds=uptime,
        conversions_last_hour=0,  # TODO: Implement conversion tracking
    )
    return Response(health_data, status_code=HTTP_200_OK)


@get("/formats")
async def formats() -> Response[FormatsResponse]:
    """Return supported formats and their capabilities"""
    supported_formats_dict = ContentTypeDetector.get_supported_formats()

    # Create capabilities with browser detection
    browser_available = await BrowserChecker.is_available()
    capabilities = SystemCapabilities(browser_available=browser_available)

    formats_data = FormatsResponse(
        formats=supported_formats_dict,
        supported_formats=list(supported_formats_dict.keys()),
        capabilities=capabilities,
    )
    return Response(formats_data, status_code=HTTP_200_OK)


# Legacy health endpoint for backward compatibility
@get("/healthz")
async def healthz() -> Response:
    """Legacy health check endpoint"""
    return Response({"status": "healthy"}, status_code=HTTP_200_OK)


def provide_converter() -> MarkItDown:
    """Provide MarkItDown converter instance using factory"""
    settings = get_settings()
    return MarkItDownFactory.create(settings)


def provide_settings() -> Settings:
    """Provide application settings as singleton"""
    return get_settings()


def provide_document_converter(settings: Settings) -> DocumentConverter:
    """Provide DocumentConverter instance with settings configuration"""
    # Get browser availability from app state
    browser_available = getattr(provide_document_converter, "_browser_available", False)

    return DocumentConverter(
        ocr_enabled=getattr(settings, "ocr_enabled", False),
        js_rendering=browser_available,
        timeout=settings.conversion_timeout,
        max_file_size_mb=settings.max_file_size // (1024 * 1024),  # Convert bytes to MB
        extract_images=getattr(settings, "extract_images", False),
        preserve_formatting=getattr(settings, "preserve_formatting", True),
        clean_markdown=getattr(settings, "clean_markdown", False),
    )


async def startup_browser_detection():
    """Detect browser availability at startup and configure logging"""
    logging.basicConfig(level=logging.INFO)

    try:
        browser_available = await BrowserChecker.is_available()
        provide_document_converter._browser_available = browser_available
        BrowserChecker.log_availability(browser_available)
    except Exception as e:
        logging.error(f"Startup browser detection failed: {e}")
        provide_document_converter._browser_available = False


settings = get_settings()

middleware = []
auth_middleware_class = create_auth_middleware(settings)
if auth_middleware_class:
    middleware.append(auth_middleware_class)

app = Litestar(
    route_handlers=[health, healthz, formats, ConvertController],
    dependencies={
        "converter": Provide(provide_converter, sync_to_thread=False),
        "settings": Provide(provide_settings, sync_to_thread=False),
        "document_converter": Provide(provide_document_converter, sync_to_thread=False),
    },
    middleware=middleware,
    debug=settings.debug,
    state={"config": settings},
    on_startup=[startup_browser_detection],
)
