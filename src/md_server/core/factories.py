import os
import logging
import requests
from markitdown import MarkItDown
from .config import Settings


class MarkItDownFactory:
    @staticmethod
    def create(settings: Settings) -> MarkItDown:
        session = MarkItDownFactory._create_session(settings)
        llm_client, llm_model = MarkItDownFactory._create_llm_client(settings)
        docintel_endpoint, docintel_credential = (
            MarkItDownFactory._create_azure_credential(settings)
        )

        return MarkItDown(
            requests_session=session,
            llm_client=llm_client,
            llm_model=llm_model,
            docintel_endpoint=docintel_endpoint,
            docintel_credential=docintel_credential,
        )

    @staticmethod
    def _create_session(settings: Settings) -> requests.Session:
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

    @staticmethod
    def _create_llm_client(settings: Settings):
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

    @staticmethod
    def _create_azure_credential(settings: Settings):
        if not settings.azure_doc_intel_key or not settings.azure_doc_intel_endpoint:
            return None, None

        try:
            from azure.core.credentials import AzureKeyCredential

            credential = AzureKeyCredential(settings.azure_doc_intel_key)
            return settings.azure_doc_intel_endpoint, credential
        except ImportError:
            logging.warning("Azure Document Intelligence not available")
            return None, None
