import os
import requests
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
from .converter import UrlConverter
from .browser import BrowserChecker
from .models import HealthResponse, FormatsResponse
from .detection import ContentTypeDetector

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
    formats_data = FormatsResponse(formats=ContentTypeDetector.get_supported_formats())
    return Response(formats_data, status_code=HTTP_200_OK)


# Legacy health endpoint for backward compatibility
@get("/healthz")
async def healthz() -> Response:
    """Legacy health check endpoint"""
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

    # Configure LLM client for image descriptions if available
    llm_client = None
    llm_model = None

    if settings.openai_api_key:
        try:
            from openai import OpenAI

            llm_client = OpenAI(
                api_key=settings.openai_api_key, base_url=settings.llm_provider_url
            )
            llm_model = settings.llm_model
        except ImportError:
            logging.warning(
                "OpenAI client not available - image descriptions will be disabled"
            )

    # Configure Azure Document Intelligence if available
    docintel_endpoint = settings.azure_doc_intel_endpoint
    docintel_credential = None
    if settings.azure_doc_intel_key and docintel_endpoint:
        try:
            from azure.core.credentials import AzureKeyCredential

            docintel_credential = AzureKeyCredential(settings.azure_doc_intel_key)
        except ImportError:
            logging.warning("Azure Document Intelligence not available")
            docintel_endpoint = None

    return MarkItDown(
        requests_session=session,
        llm_client=llm_client,
        llm_model=llm_model,
        docintel_endpoint=docintel_endpoint,
        docintel_credential=docintel_credential,
    )


def provide_settings() -> Settings:
    """Provide application settings as singleton"""
    return get_settings()


def provide_url_converter(settings: Settings) -> UrlConverter:
    """Provide UrlConverter instance with settings and browser availability"""
    # Get browser availability from app state
    browser_available = getattr(provide_url_converter, "_browser_available", False)
    return UrlConverter(settings, browser_available)


async def startup_browser_detection():
    """Detect browser availability at startup and configure logging"""
    logging.basicConfig(level=logging.INFO)

    try:
        browser_available = await BrowserChecker.is_available()
        provide_url_converter._browser_available = browser_available
        BrowserChecker.log_availability(browser_available)
    except Exception as e:
        logging.error(f"Startup browser detection failed: {e}")
        provide_url_converter._browser_available = False


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
        "url_converter": Provide(provide_url_converter, sync_to_thread=False),
    },
    middleware=middleware,
    debug=settings.debug,
    state={"config": settings},
    on_startup=[startup_browser_detection],
)
