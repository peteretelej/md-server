from typing import Optional, Any, List, Dict
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings


class LLMConfig(BaseModel):
    """Configuration for LLM client integration."""

    client_type: str = Field(
        ..., description="Type of LLM client (openai, azure_openai, anthropic)"
    )
    model: str = Field(..., description="Model name to use")
    api_key: Optional[str] = Field(None, description="API key for LLM service")
    base_url: Optional[str] = Field(None, description="Base URL for API")
    organization: Optional[str] = Field(None, description="Organization ID (OpenAI)")
    temperature: float = Field(0.1, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(1000, gt=0, description="Maximum tokens to generate")

    @validator("client_type")
    def validate_client_type(cls, v):
        allowed_types = {"openai", "azure_openai", "anthropic"}
        if v not in allowed_types:
            raise ValueError(f"client_type must be one of {allowed_types}")
        return v


class AzureDocIntelConfig(BaseModel):
    """Configuration for Azure Document Intelligence."""

    endpoint: str = Field(..., description="Azure Document Intelligence endpoint URL")
    api_key: Optional[str] = Field(None, description="API key for Azure service")
    api_version: str = Field("2023-07-31", description="API version to use")
    model_id: Optional[str] = Field(
        None, description="Custom model ID for document analysis"
    )

    @validator("endpoint")
    def validate_endpoint(cls, v):
        if not v.startswith(("http://", "https://")):
            raise ValueError("endpoint must be a valid URL")
        return v


class ConverterConfig(BaseModel):
    """Configuration for custom converters."""

    module_path: str = Field(..., description="Python module path for converter")
    class_name: str = Field(..., description="Converter class name")
    priority: float = Field(
        0.0, description="Converter priority (lower = higher priority)"
    )
    config: Dict[str, Any] = Field(
        default_factory=dict, description="Custom converter configuration"
    )


class MarkItDownConfig(BaseSettings):
    """Comprehensive configuration for MarkItDown integration."""

    # Core options
    enable_builtins: bool = Field(True, description="Enable built-in converters")
    enable_plugins: bool = Field(False, description="Enable 3rd-party plugins")
    timeout_seconds: int = Field(30, gt=0, description="Conversion timeout in seconds")

    # LLM integration
    llm_config: Optional[LLMConfig] = Field(
        None, description="LLM client configuration"
    )

    # Azure Document Intelligence
    azure_docintel_config: Optional[AzureDocIntelConfig] = Field(
        None, description="Azure Document Intelligence configuration"
    )

    # Custom converters
    custom_converters: List[ConverterConfig] = Field(
        default_factory=list, description="Custom converter configurations"
    )

    # Advanced options
    exiftool_path: Optional[str] = Field(None, description="Path to exiftool binary")
    style_map: Optional[Dict[str, str]] = Field(
        None, description="Custom style mapping for document conversion"
    )

    # Request session configuration
    requests_timeout: int = Field(30, gt=0, description="HTTP requests timeout")
    requests_max_retries: int = Field(3, ge=0, description="Maximum HTTP retries")
    requests_user_agent: str = Field(
        "MarkItDown-Server/1.0", description="User-Agent header for requests"
    )

    # Plugin system
    plugin_search_paths: List[str] = Field(
        default_factory=list, description="Additional paths to search for plugins"
    )

    # Environment-based configuration with fallbacks (support both direct and prefixed env vars)
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    azure_openai_api_key: Optional[str] = Field(
        None, description="Azure OpenAI API key"
    )
    azure_openai_endpoint: Optional[str] = Field(
        None, description="Azure OpenAI endpoint"
    )
    anthropic_api_key: Optional[str] = Field(None, description="Anthropic API key")
    azure_docintel_endpoint: Optional[str] = Field(
        None, description="Azure Document Intelligence endpoint"
    )
    azure_docintel_key: Optional[str] = Field(
        None, description="Azure Document Intelligence API key"
    )

    class Config:
        env_prefix = "MARKITDOWN_"
        case_sensitive = False
        validate_assignment = True
        env_nested_delimiter = "__"

    @validator("custom_converters")
    def validate_custom_converters(cls, v):
        """Validate custom converter configurations."""
        for converter in v:
            if not converter.module_path or not converter.class_name:
                raise ValueError(
                    "Custom converters must have module_path and class_name"
                )
        return v

    def __init__(self, **kwargs):
        """Initialize with fallback to non-prefixed environment variables."""
        import os

        # First, initialize with pydantic-settings (which handles MARKITDOWN_ prefixed vars)
        super().__init__(**kwargs)

        # Then, fallback to non-prefixed environment variables if not already set
        env_fallbacks = {
            "openai_api_key": "OPENAI_API_KEY",
            "azure_openai_api_key": "AZURE_OPENAI_API_KEY",
            "azure_openai_endpoint": "AZURE_OPENAI_ENDPOINT",
            "anthropic_api_key": "ANTHROPIC_API_KEY",
            "azure_docintel_endpoint": "AZURE_DOCINTEL_ENDPOINT",
            "azure_docintel_key": "AZURE_DOCINTEL_KEY",
        }

        # Only use fallback if the field is None and the env var exists
        for field_name, env_var in env_fallbacks.items():
            current_value = getattr(self, field_name)
            if current_value is None and env_var in os.environ:
                setattr(self, field_name, os.environ[env_var])

    def get_llm_client(self) -> Optional[Any]:
        """Create and configure LLM client based on configuration."""
        if not self.llm_config:
            return None

        try:
            if self.llm_config.client_type == "openai":
                from openai import OpenAI

                return OpenAI(
                    api_key=self.llm_config.api_key or self.openai_api_key,
                    base_url=self.llm_config.base_url,
                    organization=self.llm_config.organization,
                )
            elif self.llm_config.client_type == "azure_openai":
                from openai import AzureOpenAI

                return AzureOpenAI(
                    api_key=self.llm_config.api_key or self.azure_openai_api_key,
                    azure_endpoint=self.llm_config.base_url
                    or self.azure_openai_endpoint,
                    api_version="2024-02-01",
                )
            elif self.llm_config.client_type == "anthropic":
                from anthropic import Anthropic

                return Anthropic(
                    api_key=self.llm_config.api_key or self.anthropic_api_key
                )
        except ImportError as e:
            raise ValueError(f"LLM client library not installed: {e}")

        return None

    def get_azure_docintel_credential(self) -> Optional[Any]:
        """Create Azure Document Intelligence credential."""
        if not self.azure_docintel_config:
            return None

        api_key = self.azure_docintel_config.api_key or self.azure_docintel_key
        if api_key:
            try:
                from azure.core.credentials import AzureKeyCredential

                return AzureKeyCredential(api_key)
            except ImportError:
                raise ValueError(
                    "Azure libraries not installed for Document Intelligence"
                )

        return None

    def get_requests_session(self) -> Any:
        """Create configured requests session."""
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        session = requests.Session()

        # Configure retries
        retry_strategy = Retry(
            total=self.requests_max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set headers
        session.headers.update({"User-Agent": self.requests_user_agent})

        return session

    def load_custom_converters(self) -> List[Any]:
        """Load and instantiate custom converters."""
        converters = []

        for converter_config in self.custom_converters:
            try:
                import importlib

                module = importlib.import_module(converter_config.module_path)
                converter_class = getattr(module, converter_config.class_name)

                # Instantiate converter with config
                if converter_config.config:
                    converter = converter_class(**converter_config.config)
                else:
                    converter = converter_class()

                converters.append((converter, converter_config.priority))
            except (ImportError, AttributeError) as e:
                raise ValueError(
                    f"Failed to load converter {converter_config.class_name}: {e}"
                )

        return converters

    def to_markitdown_kwargs(self) -> Dict[str, Any]:
        """Convert configuration to MarkItDown constructor arguments."""
        kwargs = {
            "enable_builtins": self.enable_builtins,
            "enable_plugins": self.enable_plugins,
            "requests_session": self.get_requests_session(),
        }

        # Add LLM client if configured
        llm_client = self.get_llm_client()
        if llm_client:
            kwargs["llm_client"] = llm_client
            kwargs["llm_model"] = self.llm_config.model

        # Add Azure Document Intelligence if configured
        if self.azure_docintel_config:
            kwargs["docintel_endpoint"] = (
                self.azure_docintel_config.endpoint or self.azure_docintel_endpoint
            )
            kwargs["docintel_credential"] = self.get_azure_docintel_credential()

        # Add exiftool path if configured
        if self.exiftool_path:
            kwargs["exiftool_path"] = self.exiftool_path

        # Add style map if configured
        if self.style_map:
            kwargs["style_map"] = self.style_map

        return kwargs


def get_markitdown_config() -> MarkItDownConfig:
    """Get MarkItDown configuration from environment variables and defaults."""
    return MarkItDownConfig()
