import pytest
import unittest.mock as mock
import os
from unittest.mock import patch, MagicMock
from md_server.factories import MarkItDownFactory
from md_server.core.config import Settings


class TestMarkItDownFactory:
    """Unit tests for MarkItDownFactory"""

    @pytest.fixture
    def basic_settings(self):
        """Basic settings without optional services"""
        return Settings()

    @pytest.fixture
    def full_settings(self):
        """Settings with all optional services configured"""
        return Settings(
            openai_api_key="test-key",
            llm_provider_url="https://api.openai.com/v1",
            llm_model="gpt-4",
            azure_doc_intel_key="azure-key",
            azure_doc_intel_endpoint="https://test.cognitiveservices.azure.com/",
            http_proxy="http://proxy.example.com:8080",
            https_proxy="https://proxy.example.com:8080",
        )

    def test_create_with_no_services(self, basic_settings):
        """Test MarkItDown creation with no optional services"""
        with patch('md_server.factories.MarkItDown') as mock_markitdown:
            mock_instance = MagicMock()
            mock_markitdown.return_value = mock_instance
            
            result = MarkItDownFactory.create(basic_settings)
            
            # Should create MarkItDown with basic configuration
            mock_markitdown.assert_called_once()
            args = mock_markitdown.call_args
            
            # Should have requests session but no LLM or Azure services
            assert 'requests_session' in args.kwargs
            assert args.kwargs['llm_client'] is None
            assert args.kwargs['llm_model'] is None
            assert args.kwargs['docintel_endpoint'] is None
            assert args.kwargs['docintel_credential'] is None

    def test_create_with_all_services(self, full_settings):
        """Test MarkItDown creation with all services"""
        with patch('md_server.factories.MarkItDown') as mock_markitdown, \
             patch('md_server.factories.MarkItDownFactory._create_llm_client') as mock_llm, \
             patch('md_server.factories.MarkItDownFactory._create_azure_credential') as mock_azure:
            
            # Mock the service creation methods
            mock_llm_client = MagicMock()
            mock_llm.return_value = (mock_llm_client, "gpt-4")
            mock_azure.return_value = ("https://endpoint.com", MagicMock())
            
            mock_instance = MagicMock()
            mock_markitdown.return_value = mock_instance
            
            result = MarkItDownFactory.create(full_settings)
            
            # Should create MarkItDown with all services
            mock_markitdown.assert_called_once()
            args = mock_markitdown.call_args
            
            assert args.kwargs['llm_client'] == mock_llm_client
            assert args.kwargs['llm_model'] == "gpt-4"
            assert args.kwargs['docintel_endpoint'] == "https://endpoint.com"

    def test_create_session_no_proxy(self, basic_settings):
        """Test session creation without proxy"""
        session = MarkItDownFactory._create_session(basic_settings)
        
        # Should create session with no proxies
        assert len(session.proxies) == 0

    def test_create_session_with_proxy(self, full_settings):
        """Test session creation with proxy configuration"""
        # Clear environment first
        old_http = os.environ.get('HTTP_PROXY')
        old_https = os.environ.get('HTTPS_PROXY')
        
        try:
            session = MarkItDownFactory._create_session(full_settings)
            
            # Should configure proxies
            assert session.proxies['http'] == full_settings.http_proxy
            assert session.proxies['https'] == full_settings.https_proxy
            assert os.environ['HTTP_PROXY'] == full_settings.http_proxy
            assert os.environ['HTTPS_PROXY'] == full_settings.https_proxy
            
        finally:
            # Restore environment
            if old_http is not None:
                os.environ['HTTP_PROXY'] = old_http
            elif 'HTTP_PROXY' in os.environ:
                del os.environ['HTTP_PROXY']
                
            if old_https is not None:
                os.environ['HTTPS_PROXY'] = old_https
            elif 'HTTPS_PROXY' in os.environ:
                del os.environ['HTTPS_PROXY']

    def test_create_llm_client_no_config(self, basic_settings):
        """Test LLM client creation without configuration"""
        client, model = MarkItDownFactory._create_llm_client(basic_settings)
        
        assert client is None
        assert model is None

    def test_create_llm_client_with_config(self, full_settings):
        """Test LLM client creation with configuration"""
        with patch('openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            
            client, model = MarkItDownFactory._create_llm_client(full_settings)
            
            # Should create OpenAI client with correct configuration
            mock_openai.assert_called_once_with(
                api_key=full_settings.openai_api_key,
                base_url=full_settings.llm_provider_url
            )
            assert client == mock_client
            assert model == full_settings.llm_model

    def test_create_llm_client_import_failure(self, full_settings):
        """Test LLM client creation when OpenAI import fails"""
        # Simply test that import failure is handled gracefully
        # by temporarily removing any existing openai module
        import sys
        openai_module = sys.modules.get('openai')
        if 'openai' in sys.modules:
            del sys.modules['openai']
        
        try:
            with patch('sys.modules', {k: v for k, v in sys.modules.items() if k != 'openai'}):
                with patch('logging.warning') as mock_warning:
                    client, model = MarkItDownFactory._create_llm_client(full_settings)
                    
                    # Should handle gracefully without openai
                    assert client is None
                    assert model is None
        finally:
            if openai_module:
                sys.modules['openai'] = openai_module

    def test_create_azure_credential_no_config(self, basic_settings):
        """Test Azure credential creation without configuration"""
        endpoint, credential = MarkItDownFactory._create_azure_credential(basic_settings)
        
        assert endpoint is None
        assert credential is None

    def test_create_azure_credential_partial_config(self):
        """Test Azure credential creation with partial configuration"""
        # Only key, no endpoint
        settings_key_only = Settings(azure_doc_intel_key="test-key")
        endpoint, credential = MarkItDownFactory._create_azure_credential(settings_key_only)
        assert endpoint is None
        assert credential is None
        
        # Only endpoint, no key
        settings_endpoint_only = Settings(azure_doc_intel_endpoint="https://test.com")
        endpoint, credential = MarkItDownFactory._create_azure_credential(settings_endpoint_only)
        assert endpoint is None
        assert credential is None

    def test_create_azure_credential_with_config(self, full_settings):
        """Test Azure credential creation with full configuration"""
        with patch('azure.core.credentials.AzureKeyCredential') as mock_credential:
            mock_cred_instance = MagicMock()
            mock_credential.return_value = mock_cred_instance
            
            endpoint, credential = MarkItDownFactory._create_azure_credential(full_settings)
            
            # Should create credential with correct configuration
            mock_credential.assert_called_once_with(full_settings.azure_doc_intel_key)
            assert endpoint == full_settings.azure_doc_intel_endpoint
            assert credential == mock_cred_instance

    def test_create_azure_credential_import_failure(self, full_settings):
        """Test Azure credential creation when Azure import fails"""
        # Simply test that import failure is handled gracefully
        import sys
        azure_modules = {k: v for k, v in sys.modules.items() if k.startswith('azure')}
        for module in azure_modules:
            if module in sys.modules:
                del sys.modules[module]
        
        try:
            with patch('sys.modules', {k: v for k, v in sys.modules.items() if not k.startswith('azure')}):
                with patch('logging.warning') as mock_warning:
                    endpoint, credential = MarkItDownFactory._create_azure_credential(full_settings)
                    
                    # Should handle gracefully without azure
                    assert endpoint is None
                    assert credential is None
        finally:
            for module, mod_obj in azure_modules.items():
                sys.modules[module] = mod_obj

    def test_proxy_configuration_precedence(self):
        """Test proxy configuration precedence and environment handling"""
        settings = Settings(
            http_proxy="http://custom.proxy:8080",
            https_proxy="https://custom.proxy:8080"
        )
        
        # Store original environment
        orig_http = os.environ.get('HTTP_PROXY')
        orig_https = os.environ.get('HTTPS_PROXY')
        
        try:
            session = MarkItDownFactory._create_session(settings)
            
            # Should set both session proxies and environment variables
            assert session.proxies['http'] == settings.http_proxy
            assert session.proxies['https'] == settings.https_proxy
            assert os.environ['HTTP_PROXY'] == settings.http_proxy
            assert os.environ['HTTPS_PROXY'] == settings.https_proxy
            
        finally:
            # Restore original environment
            if orig_http is not None:
                os.environ['HTTP_PROXY'] = orig_http
            elif 'HTTP_PROXY' in os.environ:
                del os.environ['HTTP_PROXY']
                
            if orig_https is not None:
                os.environ['HTTPS_PROXY'] = orig_https
            elif 'HTTPS_PROXY' in os.environ:
                del os.environ['HTTPS_PROXY']

    def test_mixed_proxy_configuration(self):
        """Test mixed proxy configuration (only HTTP or only HTTPS)"""
        # Only HTTP proxy
        settings_http = Settings(http_proxy="http://proxy.example.com:8080")
        session = MarkItDownFactory._create_session(settings_http)
        
        assert 'http' in session.proxies
        assert 'https' not in session.proxies
        
        # Only HTTPS proxy
        settings_https = Settings(https_proxy="https://proxy.example.com:8080")
        session = MarkItDownFactory._create_session(settings_https)
        
        assert 'https' in session.proxies
        assert session.proxies.get('http') != settings_https.https_proxy  # Should not be set

    def test_factory_integration(self, full_settings):
        """Test full factory integration with all components"""
        with patch('md_server.factories.MarkItDown') as mock_markitdown, \
             patch('openai.OpenAI') as mock_openai, \
             patch('azure.core.credentials.AzureKeyCredential') as mock_azure:
            
            # Setup mocks
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            mock_credential = MagicMock()
            mock_azure.return_value = mock_credential
            mock_markitdown_instance = MagicMock()
            mock_markitdown.return_value = mock_markitdown_instance
            
            # Create instance
            result = MarkItDownFactory.create(full_settings)
            
            # Verify all components were created and configured
            mock_openai.assert_called_once()
            mock_azure.assert_called_once()
            mock_markitdown.assert_called_once()
            
            # Verify MarkItDown was called with all components
            call_kwargs = mock_markitdown.call_args.kwargs
            assert 'requests_session' in call_kwargs
            assert call_kwargs['llm_client'] == mock_client
            assert call_kwargs['llm_model'] == full_settings.llm_model
            assert call_kwargs['docintel_endpoint'] == full_settings.azure_doc_intel_endpoint
            assert call_kwargs['docintel_credential'] == mock_credential
            
            assert result == mock_markitdown_instance