import pytest
import os
from unittest.mock import patch, Mock
from md_server.core.config import Settings, get_settings


class TestSettings:
    def test_default_values(self):
        """Test default configuration values"""
        settings = Settings()
        
        assert settings.host == "127.0.0.1"
        assert settings.port == 8080
        assert settings.api_key is None
        assert settings.max_file_size == 50 * 1024 * 1024
        assert settings.timeout_seconds == 30
        assert settings.url_fetch_timeout == 30
        assert settings.conversion_timeout == 120
        assert settings.debug is False
        
        assert settings.http_proxy is None
        assert settings.https_proxy is None
        
        assert settings.openai_api_key is None
        assert settings.azure_doc_intel_endpoint is None
        assert settings.azure_doc_intel_key is None
        
        assert settings.crawl4ai_js_rendering is False
        assert settings.crawl4ai_timeout == 30
        assert settings.crawl4ai_user_agent is None
        
        assert settings.llm_provider_url is None
        assert settings.llm_api_key is None
        assert settings.llm_model == "google/gemini-2.5-flash"
        
        assert isinstance(settings.allowed_file_types, list)
        assert len(settings.allowed_file_types) > 0

    def test_allowed_file_types_content(self):
        """Test allowed file types contain expected formats"""
        settings = Settings()
        
        expected_types = [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "text/plain",
            "text/html",
            "text/markdown",
            "application/json",
        ]
        
        for file_type in expected_types:
            assert file_type in settings.allowed_file_types

    def test_custom_values(self):
        """Test settings with custom values"""
        settings = Settings(
            host="0.0.0.0",
            port=9000,
            api_key="test-api-key",
            max_file_size=100 * 1024 * 1024,
            timeout_seconds=60,
            url_fetch_timeout=45,
            conversion_timeout=180,
            debug=True,
            http_proxy="http://proxy.example.com:8080",
            https_proxy="https://proxy.example.com:8443",
            openai_api_key="sk-test-key",
            azure_doc_intel_endpoint="https://test.cognitiveservices.azure.com/",
            azure_doc_intel_key="azure-test-key",
            crawl4ai_js_rendering=True,
            crawl4ai_timeout=60,
            crawl4ai_user_agent="Custom User Agent",
            llm_provider_url="https://api.openai.com/v1",
            llm_api_key="llm-test-key",
            llm_model="gpt-4",
        )
        
        assert settings.host == "0.0.0.0"
        assert settings.port == 9000
        assert settings.api_key == "test-api-key"
        assert settings.max_file_size == 100 * 1024 * 1024
        assert settings.timeout_seconds == 60
        assert settings.url_fetch_timeout == 45
        assert settings.conversion_timeout == 180
        assert settings.debug is True
        
        assert settings.http_proxy == "http://proxy.example.com:8080"
        assert settings.https_proxy == "https://proxy.example.com:8443"
        
        assert settings.openai_api_key == "sk-test-key"
        assert settings.azure_doc_intel_endpoint == "https://test.cognitiveservices.azure.com/"
        assert settings.azure_doc_intel_key == "azure-test-key"
        
        assert settings.crawl4ai_js_rendering is True
        assert settings.crawl4ai_timeout == 60
        assert settings.crawl4ai_user_agent == "Custom User Agent"
        
        assert settings.llm_provider_url == "https://api.openai.com/v1"
        assert settings.llm_api_key == "llm-test-key"
        assert settings.llm_model == "gpt-4"

    def test_field_descriptions(self):
        """Test field descriptions are properly set"""
        # Check that fields have descriptions (accessing the model fields from class)
        fields = Settings.model_fields
        
        assert "JavaScript rendering" in fields["crawl4ai_js_rendering"].description
        assert "timeout" in fields["crawl4ai_timeout"].description.lower()
        assert "User agent" in fields["crawl4ai_user_agent"].description
        assert "LLM provider" in fields["llm_provider_url"].description
        assert "API key" in fields["llm_api_key"].description
        assert "model" in fields["llm_model"].description.lower()

    @patch.dict(os.environ, {
        "MD_SERVER_HOST": "192.168.1.100",
        "MD_SERVER_PORT": "9090",
        "MD_SERVER_API_KEY": "env-api-key",
        "MD_SERVER_DEBUG": "true",
        "MD_SERVER_OPENAI_API_KEY": "env-openai-key",
    })
    def test_environment_variables(self):
        """Test loading from environment variables"""
        settings = Settings()
        
        assert settings.host == "192.168.1.100"
        assert settings.port == 9090
        assert settings.api_key == "env-api-key"
        assert settings.debug is True
        assert settings.openai_api_key == "env-openai-key"

    @patch.dict(os.environ, {
        "MD_SERVER_MAX_FILE_SIZE": "104857600",  # 100MB in bytes
        "MD_SERVER_TIMEOUT_SECONDS": "45",
        "MD_SERVER_CRAWL4AI_TIMEOUT": "90",
    })
    def test_integer_environment_variables(self):
        """Test integer conversion from environment variables"""
        settings = Settings()
        
        assert settings.max_file_size == 104857600
        assert settings.timeout_seconds == 45
        assert settings.crawl4ai_timeout == 90

    @patch.dict(os.environ, {
        "MD_SERVER_CRAWL4AI_JS_RENDERING": "true",
        "MD_SERVER_DEBUG": "false",
    })
    def test_boolean_environment_variables(self):
        """Test boolean conversion from environment variables"""
        settings = Settings()
        
        assert settings.crawl4ai_js_rendering is True
        assert settings.debug is False

    @patch.dict(os.environ, {
        "MD_SERVER_CRAWL4AI_JS_RENDERING": "1",
        "MD_SERVER_DEBUG": "0",
    })
    def test_boolean_numeric_environment_variables(self):
        """Test boolean conversion from numeric environment variables"""
        settings = Settings()
        
        assert settings.crawl4ai_js_rendering is True
        assert settings.debug is False

    def test_model_config_settings(self):
        """Test model configuration settings"""
        settings = Settings()
        
        # Check that model config is properly set
        assert settings.model_config["env_file"] == ".env"
        assert settings.model_config["env_prefix"] == "MD_SERVER_"

    def test_proxy_settings_none_by_default(self):
        """Test proxy settings are None by default"""
        settings = Settings()
        
        assert settings.http_proxy is None
        assert settings.https_proxy is None

    def test_azure_settings_none_by_default(self):
        """Test Azure settings are None by default"""
        settings = Settings()
        
        assert settings.azure_doc_intel_endpoint is None
        assert settings.azure_doc_intel_key is None

    def test_llm_settings_defaults(self):
        """Test LLM settings defaults"""
        settings = Settings()
        
        assert settings.llm_provider_url is None
        assert settings.llm_api_key is None
        assert settings.llm_model == "google/gemini-2.5-flash"

    def test_crawl4ai_settings_defaults(self):
        """Test Crawl4AI settings defaults"""
        settings = Settings()
        
        assert settings.crawl4ai_js_rendering is False
        assert settings.crawl4ai_timeout == 30
        assert settings.crawl4ai_user_agent is None

    def test_allowed_file_types_is_list(self):
        """Test allowed file types is a proper list"""
        settings = Settings()
        
        assert isinstance(settings.allowed_file_types, list)
        assert all(isinstance(file_type, str) for file_type in settings.allowed_file_types)

    @patch.dict(os.environ, {
        "MD_SERVER_HTTP_PROXY": "http://company-proxy:3128",
        "MD_SERVER_HTTPS_PROXY": "https://company-proxy:3128",
    })
    def test_proxy_environment_variables(self):
        """Test proxy settings from environment"""
        settings = Settings()
        
        assert settings.http_proxy == "http://company-proxy:3128"
        assert settings.https_proxy == "https://company-proxy:3128"

    @patch.dict(os.environ, {
        "MD_SERVER_AZURE_DOC_INTEL_ENDPOINT": "https://myservice.cognitiveservices.azure.com/",
        "MD_SERVER_AZURE_DOC_INTEL_KEY": "my-azure-key",
    })
    def test_azure_environment_variables(self):
        """Test Azure settings from environment"""
        settings = Settings()
        
        assert settings.azure_doc_intel_endpoint == "https://myservice.cognitiveservices.azure.com/"
        assert settings.azure_doc_intel_key == "my-azure-key"

    @patch.dict(os.environ, {
        "MD_SERVER_LLM_PROVIDER_URL": "https://openrouter.ai/api/v1",
        "MD_SERVER_LLM_API_KEY": "or-key-123",
        "MD_SERVER_LLM_MODEL": "anthropic/claude-3-sonnet",
    })
    def test_llm_environment_variables(self):
        """Test LLM settings from environment"""
        settings = Settings()
        
        assert settings.llm_provider_url == "https://openrouter.ai/api/v1"
        assert settings.llm_api_key == "or-key-123"
        assert settings.llm_model == "anthropic/claude-3-sonnet"


class TestGetSettings:
    def test_get_settings_returns_settings_instance(self):
        """Test get_settings returns a Settings instance"""
        settings = get_settings()
        
        assert isinstance(settings, Settings)

    def test_get_settings_returns_fresh_instance(self):
        """Test get_settings returns a fresh instance each time"""
        settings1 = get_settings()
        settings2 = get_settings()
        
        # They should be separate instances
        assert settings1 is not settings2
        
        # But have the same values
        assert settings1.host == settings2.host
        assert settings1.port == settings2.port

    @patch.dict(os.environ, {
        "MD_SERVER_HOST": "test-host",
        "MD_SERVER_PORT": "9999",
    })
    def test_get_settings_with_environment(self):
        """Test get_settings respects environment variables"""
        settings = get_settings()
        
        assert settings.host == "test-host"
        assert settings.port == 9999