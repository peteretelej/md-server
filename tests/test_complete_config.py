from md_server.core.config import Settings


class TestCompleteConfiguration:
    def test_openai_api_key_configuration(self, monkeypatch):
        monkeypatch.setenv("MD_SERVER_OPENAI_API_KEY", "sk-test-key")
        settings = Settings()
        assert settings.openai_api_key == "sk-test-key"

    def test_azure_doc_intel_configuration(self, monkeypatch):
        monkeypatch.setenv(
            "MD_SERVER_AZURE_DOC_INTEL_ENDPOINT",
            "https://test.cognitiveservices.azure.com",
        )
        monkeypatch.setenv("MD_SERVER_AZURE_DOC_INTEL_KEY", "test-azure-key")

        settings = Settings()
        assert (
            settings.azure_doc_intel_endpoint
            == "https://test.cognitiveservices.azure.com"
        )
        assert settings.azure_doc_intel_key == "test-azure-key"

    def test_crawl4ai_configuration(self, monkeypatch):
        monkeypatch.setenv("MD_SERVER_CRAWL4AI_JS_RENDERING", "true")
        monkeypatch.setenv("MD_SERVER_CRAWL4AI_TIMEOUT", "60")
        monkeypatch.setenv("MD_SERVER_CRAWL4AI_USER_AGENT", "custom-agent/2.0")

        settings = Settings()
        assert settings.crawl4ai_js_rendering
        assert settings.crawl4ai_timeout == 60
        assert settings.crawl4ai_user_agent == "custom-agent/2.0"

    def test_default_values(self):
        settings = Settings()
        assert settings.openai_api_key is None
        assert settings.azure_doc_intel_endpoint is None
        assert settings.azure_doc_intel_key is None
        assert not settings.crawl4ai_js_rendering
        assert settings.crawl4ai_timeout == 30
        assert settings.crawl4ai_user_agent is None

    def test_all_configuration_fields_together(self, monkeypatch):
        monkeypatch.setenv("MD_SERVER_HOST", "0.0.0.0")
        monkeypatch.setenv("MD_SERVER_PORT", "9090")
        monkeypatch.setenv("MD_SERVER_API_KEY", "test-api-key")
        monkeypatch.setenv("MD_SERVER_HTTP_PROXY", "http://proxy:8080")
        monkeypatch.setenv("MD_SERVER_HTTPS_PROXY", "https://proxy:8080")
        monkeypatch.setenv("MD_SERVER_OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("MD_SERVER_AZURE_DOC_INTEL_ENDPOINT", "https://azure.test")
        monkeypatch.setenv("MD_SERVER_AZURE_DOC_INTEL_KEY", "azure-key")
        monkeypatch.setenv("MD_SERVER_CRAWL4AI_TIMEOUT", "45")

        settings = Settings()
        assert settings.host == "0.0.0.0"
        assert settings.port == 9090
        assert settings.api_key == "test-api-key"
        assert settings.http_proxy == "http://proxy:8080"
        assert settings.https_proxy == "https://proxy:8080"
        assert settings.openai_api_key == "sk-test"
        assert settings.azure_doc_intel_endpoint == "https://azure.test"
        assert settings.azure_doc_intel_key == "azure-key"
        assert settings.crawl4ai_timeout == 45
