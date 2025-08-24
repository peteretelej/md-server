import os
import sys
import unittest.mock
import pytest
import requests
from markitdown import MarkItDown
from src.md_server.core.factories import MarkItDownFactory
from src.md_server.core.config import Settings


def test_markitdown_factory_basic_creation():
    settings = Settings()

    result = MarkItDownFactory.create(settings)

    assert isinstance(result, MarkItDown)
    assert hasattr(result, "_requests_session")
    assert isinstance(result._requests_session, requests.Session)


def test_session_creation_with_proxy_config():
    settings = Settings(
        http_proxy="http://proxy.example.com:8080",
        https_proxy="https://proxy.example.com:8080",
    )

    session = MarkItDownFactory._create_session(settings)

    assert isinstance(session, requests.Session)
    assert session.proxies["http"] == "http://proxy.example.com:8080"
    assert session.proxies["https"] == "https://proxy.example.com:8080"
    assert os.environ.get("HTTP_PROXY") == "http://proxy.example.com:8080"
    assert os.environ.get("HTTPS_PROXY") == "https://proxy.example.com:8080"


def test_session_creation_without_proxy_config():
    settings = Settings()

    session = MarkItDownFactory._create_session(settings)

    assert isinstance(session, requests.Session)
    assert not session.proxies


def test_llm_client_creation_without_openai_key():
    settings = Settings()

    client, model = MarkItDownFactory._create_llm_client(settings)

    assert client is None
    assert model is None


def test_llm_client_creation_with_openai_key():
    settings = Settings(
        openai_api_key="test-api-key",
        llm_model="gpt-4",
        llm_provider_url="https://api.openai.com/v1",
    )

    with unittest.mock.patch("openai.OpenAI") as mock_openai:
        mock_client = unittest.mock.Mock()
        mock_openai.return_value = mock_client

        client, model = MarkItDownFactory._create_llm_client(settings)

        assert client == mock_client
        assert model == "gpt-4"
        mock_openai.assert_called_once_with(
            api_key="test-api-key", base_url="https://api.openai.com/v1"
        )


def test_llm_client_creation_import_error():
    settings = Settings(openai_api_key="test-api-key")

    original_openai = sys.modules.get("openai")
    try:
        if "openai" in sys.modules:
            del sys.modules["openai"]

        with unittest.mock.patch.dict(sys.modules, {"openai": None}):
            with unittest.mock.patch("logging.warning") as mock_warning:
                client, model = MarkItDownFactory._create_llm_client(settings)

                assert client is None
                assert model is None
                mock_warning.assert_called_once_with(
                    "OpenAI client not available - image descriptions will be disabled"
                )
    finally:
        if original_openai is not None:
            sys.modules["openai"] = original_openai


def test_azure_credentials_without_config():
    settings = Settings()

    endpoint, credential = MarkItDownFactory._create_azure_credential(settings)

    assert endpoint is None
    assert credential is None


def test_azure_credentials_partial_config_missing_key():
    settings = Settings(
        azure_doc_intel_endpoint="https://test.cognitiveservices.azure.com/"
    )

    endpoint, credential = MarkItDownFactory._create_azure_credential(settings)

    assert endpoint is None
    assert credential is None


def test_azure_credentials_partial_config_missing_endpoint():
    settings = Settings(azure_doc_intel_key="test-key")

    endpoint, credential = MarkItDownFactory._create_azure_credential(settings)

    assert endpoint is None
    assert credential is None


def test_azure_credentials_with_full_config():
    settings = Settings(
        azure_doc_intel_key="test-key",
        azure_doc_intel_endpoint="https://test.cognitiveservices.azure.com/",
    )

    with unittest.mock.patch(
        "azure.core.credentials.AzureKeyCredential"
    ) as mock_credential:
        mock_cred_instance = unittest.mock.Mock()
        mock_credential.return_value = mock_cred_instance

        endpoint, credential = MarkItDownFactory._create_azure_credential(settings)

        assert endpoint == "https://test.cognitiveservices.azure.com/"
        assert credential == mock_cred_instance
        mock_credential.assert_called_once_with("test-key")


def test_azure_credentials_import_error():
    settings = Settings(
        azure_doc_intel_key="test-key",
        azure_doc_intel_endpoint="https://test.cognitiveservices.azure.com/",
    )

    original_azure = sys.modules.get("azure.core.credentials")
    try:
        if "azure.core.credentials" in sys.modules:
            del sys.modules["azure.core.credentials"]

        with unittest.mock.patch.dict(sys.modules, {"azure.core.credentials": None}):
            with unittest.mock.patch("logging.warning") as mock_warning:
                endpoint, credential = MarkItDownFactory._create_azure_credential(
                    settings
                )

                assert endpoint is None
                assert credential is None
                mock_warning.assert_called_once_with(
                    "Azure Document Intelligence not available"
                )
    finally:
        if original_azure is not None:
            sys.modules["azure.core.credentials"] = original_azure


def test_factory_integration_with_all_components():
    settings = Settings(
        http_proxy="http://proxy.example.com:8080",
        openai_api_key="test-openai-key",
        llm_model="gpt-4",
        azure_doc_intel_key="test-azure-key",
        azure_doc_intel_endpoint="https://test.cognitiveservices.azure.com/",
    )

    with (
        unittest.mock.patch("openai.OpenAI") as mock_openai,
        unittest.mock.patch(
            "azure.core.credentials.AzureKeyCredential"
        ) as mock_credential,
    ):
        mock_openai_client = unittest.mock.Mock()
        mock_openai.return_value = mock_openai_client

        mock_azure_cred = unittest.mock.Mock()
        mock_credential.return_value = mock_azure_cred

        result = MarkItDownFactory.create(settings)

        assert isinstance(result, MarkItDown)
        assert (
            result._requests_session.proxies["http"] == "http://proxy.example.com:8080"
        )
        mock_openai.assert_called_once()
        mock_credential.assert_called_once()


@pytest.fixture(autouse=True)
def cleanup_environment():
    original_http_proxy = os.environ.get("HTTP_PROXY")
    original_https_proxy = os.environ.get("HTTPS_PROXY")

    yield

    if original_http_proxy is not None:
        os.environ["HTTP_PROXY"] = original_http_proxy
    elif "HTTP_PROXY" in os.environ:
        del os.environ["HTTP_PROXY"]

    if original_https_proxy is not None:
        os.environ["HTTPS_PROXY"] = original_https_proxy
    elif "HTTPS_PROXY" in os.environ:
        del os.environ["HTTPS_PROXY"]
