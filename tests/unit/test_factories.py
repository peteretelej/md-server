import pytest
import os
import sys
import requests
from unittest.mock import Mock, patch, MagicMock
import logging
from md_server.factories import (
    HTTPClientFactory,
    LLMClientFactory,
    AzureDocIntelFactory,
    MarkItDownFactory,
)
from md_server.core.config import Settings


class TestHTTPClientFactory:
    def test_create_session_no_proxy(self):
        """Test session creation without proxy settings"""
        settings = Settings()
        
        session = HTTPClientFactory.create_session(settings)
        
        assert isinstance(session, requests.Session)
        assert session.proxies == {}

    def test_create_session_http_proxy(self):
        """Test session creation with HTTP proxy"""
        settings = Settings(http_proxy="http://proxy.example.com:8080")
        
        session = HTTPClientFactory.create_session(settings)
        
        assert session.proxies["http"] == "http://proxy.example.com:8080"
        assert os.environ.get("HTTP_PROXY") == "http://proxy.example.com:8080"

    def test_create_session_https_proxy(self):
        """Test session creation with HTTPS proxy"""
        settings = Settings(https_proxy="https://proxy.example.com:8443")
        
        session = HTTPClientFactory.create_session(settings)
        
        assert session.proxies["https"] == "https://proxy.example.com:8443"
        assert os.environ.get("HTTPS_PROXY") == "https://proxy.example.com:8443"

    def test_create_session_both_proxies(self):
        """Test session creation with both HTTP and HTTPS proxies"""
        settings = Settings(
            http_proxy="http://proxy.example.com:8080",
            https_proxy="https://proxy.example.com:8443"
        )
        
        session = HTTPClientFactory.create_session(settings)
        
        assert session.proxies["http"] == "http://proxy.example.com:8080"
        assert session.proxies["https"] == "https://proxy.example.com:8443"
        assert os.environ.get("HTTP_PROXY") == "http://proxy.example.com:8080"
        assert os.environ.get("HTTPS_PROXY") == "https://proxy.example.com:8443"


class TestLLMClientFactory:
    def test_create_client_no_api_key(self):
        """Test client creation without API key"""
        settings = Settings()
        
        client, model = LLMClientFactory.create_client(settings)
        
        assert client is None
        assert model is None

    @patch("openai.OpenAI")
    def test_create_client_success(self, mock_openai):
        """Test successful client creation"""
        settings = Settings(
            openai_api_key="sk-test-key",
            llm_model="gpt-4",
            llm_provider_url="https://api.openai.com/v1"
        )
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        client, model = LLMClientFactory.create_client(settings)
        
        assert client == mock_client
        assert model == "gpt-4"
        mock_openai.assert_called_once_with(
            api_key="sk-test-key",
            base_url="https://api.openai.com/v1"
        )

    def test_create_client_import_error(self, caplog):
        """Test client creation with import error"""
        settings = Settings(openai_api_key="sk-test-key")
        
        # Mock the import to raise ImportError
        with patch.dict('sys.modules', {'openai': None}):
            with caplog.at_level(logging.WARNING):
                client, model = LLMClientFactory.create_client(settings)
        
        assert client is None
        assert model is None
        assert "OpenAI client not available" in caplog.text


class TestAzureDocIntelFactory:
    def test_create_credential_no_config(self):
        """Test credential creation without Azure configuration"""
        settings = Settings()
        
        endpoint, credential = AzureDocIntelFactory.create_credential(settings)
        
        assert endpoint is None
        assert credential is None

    def test_create_credential_missing_key(self):
        """Test credential creation with missing key"""
        settings = Settings(azure_doc_intel_endpoint="https://test.cognitiveservices.azure.com/")
        
        endpoint, credential = AzureDocIntelFactory.create_credential(settings)
        
        assert endpoint is None
        assert credential is None

    def test_create_credential_missing_endpoint(self):
        """Test credential creation with missing endpoint"""
        settings = Settings(azure_doc_intel_key="test-key")
        
        endpoint, credential = AzureDocIntelFactory.create_credential(settings)
        
        assert endpoint is None
        assert credential is None

    @patch("azure.core.credentials.AzureKeyCredential")
    def test_create_credential_success(self, mock_credential_class):
        """Test successful credential creation"""
        settings = Settings(
            azure_doc_intel_key="test-key",
            azure_doc_intel_endpoint="https://test.cognitiveservices.azure.com/"
        )
        mock_credential = Mock()
        mock_credential_class.return_value = mock_credential
        
        endpoint, credential = AzureDocIntelFactory.create_credential(settings)
        
        assert endpoint == "https://test.cognitiveservices.azure.com/"
        assert credential == mock_credential
        mock_credential_class.assert_called_once_with("test-key")

    def test_create_credential_import_error(self, caplog):
        """Test credential creation with import error"""
        settings = Settings(
            azure_doc_intel_key="test-key",
            azure_doc_intel_endpoint="https://test.cognitiveservices.azure.com/"
        )
        
        # Mock the import to raise ImportError
        with patch.dict('sys.modules', {'azure.core.credentials': None}):
            with caplog.at_level(logging.WARNING):
                endpoint, credential = AzureDocIntelFactory.create_credential(settings)
        
        assert endpoint is None
        assert credential is None
        assert "Azure Document Intelligence not available" in caplog.text


class TestMarkItDownFactory:
    @patch("md_server.factories.MarkItDown")
    @patch("md_server.factories.AzureDocIntelFactory.create_credential")
    @patch("md_server.factories.LLMClientFactory.create_client")
    @patch("md_server.factories.HTTPClientFactory.create_session")
    def test_create_full_configuration(
        self, mock_http_factory, mock_llm_factory, mock_azure_factory, mock_markitdown
    ):
        """Test MarkItDown creation with all services configured"""
        settings = Settings()
        
        mock_session = Mock()
        mock_llm_client = Mock()
        mock_llm_model = "gpt-4"
        mock_endpoint = "https://test.cognitiveservices.azure.com/"
        mock_credential = Mock()
        mock_markitdown_instance = Mock()
        
        mock_http_factory.return_value = mock_session
        mock_llm_factory.return_value = (mock_llm_client, mock_llm_model)
        mock_azure_factory.return_value = (mock_endpoint, mock_credential)
        mock_markitdown.return_value = mock_markitdown_instance
        
        result = MarkItDownFactory.create(settings)
        
        assert result == mock_markitdown_instance
        mock_http_factory.assert_called_once_with(settings)
        mock_llm_factory.assert_called_once_with(settings)
        mock_azure_factory.assert_called_once_with(settings)
        mock_markitdown.assert_called_once_with(
            requests_session=mock_session,
            llm_client=mock_llm_client,
            llm_model=mock_llm_model,
            docintel_endpoint=mock_endpoint,
            docintel_credential=mock_credential,
        )

    @patch("md_server.factories.MarkItDown")
    @patch("md_server.factories.AzureDocIntelFactory.create_credential")
    @patch("md_server.factories.LLMClientFactory.create_client")
    @patch("md_server.factories.HTTPClientFactory.create_session")
    def test_create_minimal_configuration(
        self, mock_http_factory, mock_llm_factory, mock_azure_factory, mock_markitdown
    ):
        """Test MarkItDown creation with minimal configuration"""
        settings = Settings()
        
        mock_session = Mock()
        mock_markitdown_instance = Mock()
        
        mock_http_factory.return_value = mock_session
        mock_llm_factory.return_value = (None, None)
        mock_azure_factory.return_value = (None, None)
        mock_markitdown.return_value = mock_markitdown_instance
        
        result = MarkItDownFactory.create(settings)
        
        assert result == mock_markitdown_instance
        mock_markitdown.assert_called_once_with(
            requests_session=mock_session,
            llm_client=None,
            llm_model=None,
            docintel_endpoint=None,
            docintel_credential=None,
        )