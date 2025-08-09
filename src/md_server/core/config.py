from pydantic import ConfigDict
from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", env_prefix="MD_SERVER_")
    
    host: str = "127.0.0.1"
    port: int = 8080
    api_key: Optional[str] = None
    max_file_size: int = 50 * 1024 * 1024
    timeout_seconds: int = 30
    debug: bool = False
    
    http_proxy: Optional[str] = None
    https_proxy: Optional[str] = None
    
    openai_api_key: Optional[str] = None
    azure_doc_intel_endpoint: Optional[str] = None
    azure_doc_intel_key: Optional[str] = None
    
    crawl4ai_timeout: int = 30
    crawl4ai_max_pages: int = 10
    crawl4ai_user_agent: str = "md-server/1.0"
    
    allowed_file_types: List[str] = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/plain",
        "text/html",
        "text/markdown",
        "application/json",
    ]


def get_settings() -> Settings:
    return Settings()
