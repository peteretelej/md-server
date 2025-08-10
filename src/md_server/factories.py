import os
import logging
import requests
from markitdown import MarkItDown
from .core.config import Settings


class HTTPClientFactory:
    @staticmethod
    def create_session(settings: Settings) -> requests.Session:
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


class LLMClientFactory:
    @staticmethod
    def create_client(settings: Settings):
        """Create LLM client if OpenAI configuration is available"""
        if not settings.openai_api_key:
            return None, None

        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=settings.openai_api_key, base_url=settings.llm_provider_url
            )
            return client, settings.llm_model
        except ImportError:
            logging.warning(
                "OpenAI client not available - image descriptions will be disabled"
            )
            return None, None


class AzureDocIntelFactory:
    @staticmethod
    def create_credential(settings: Settings):
        """Create Azure Document Intelligence credential if available"""
        if not settings.azure_doc_intel_key or not settings.azure_doc_intel_endpoint:
            return None, None

        try:
            from azure.core.credentials import AzureKeyCredential

            credential = AzureKeyCredential(settings.azure_doc_intel_key)
            return settings.azure_doc_intel_endpoint, credential
        except ImportError:
            logging.warning("Azure Document Intelligence not available")
            return None, None


class MarkItDownFactory:
    @staticmethod
    def create(settings: Settings) -> MarkItDown:
        """Create MarkItDown instance with all configured services"""
        session = HTTPClientFactory.create_session(settings)
        llm_client, llm_model = LLMClientFactory.create_client(settings)
        docintel_endpoint, docintel_credential = AzureDocIntelFactory.create_credential(
            settings
        )

        return MarkItDown(
            requests_session=session,
            llm_client=llm_client,
            llm_model=llm_model,
            docintel_endpoint=docintel_endpoint,
            docintel_credential=docintel_credential,
        )
