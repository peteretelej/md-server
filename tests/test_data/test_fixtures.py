import pytest
from pathlib import Path
from httpx import AsyncClient
from fastapi.testclient import TestClient

from md_server.core.config import Settings
from md_server.core.markitdown_config import MarkItDownConfig


def test_test_data_dir_fixture(test_data_dir):
    assert isinstance(test_data_dir, Path)
    assert test_data_dir.exists()
    assert test_data_dir.is_dir()
    assert (test_data_dir / "test.pdf").exists()


def test_client_fixture(client):
    assert isinstance(client, TestClient)


@pytest.mark.asyncio
async def test_async_client_fixture(async_client):
    assert isinstance(async_client, AsyncClient)


def test_file_test_vectors_fixture(file_test_vectors):
    assert isinstance(file_test_vectors, dict)
    assert "pdf" in file_test_vectors
    assert "docx" in file_test_vectors
    assert "html_blog" in file_test_vectors
    
    pdf_vector = file_test_vectors["pdf"]
    assert pdf_vector.filename == "test.pdf"
    assert pdf_vector.content_type == "application/pdf"
    assert pdf_vector.expected_status == 200


def test_url_test_vectors_fixture(url_test_vectors):
    assert isinstance(url_test_vectors, dict)
    assert "valid_webpage" in url_test_vectors
    assert "invalid_url" in url_test_vectors


def test_sample_files_fixture(sample_files):
    assert isinstance(sample_files, dict)
    assert "pdf" in sample_files
    assert isinstance(sample_files["pdf"], Path)
    assert sample_files["pdf"].exists()


def test_mock_settings_fixture(mock_settings):
    assert isinstance(mock_settings, Settings)
    assert mock_settings.max_file_size == 10 * 1024 * 1024
    assert mock_settings.timeout_seconds == 5


def test_mock_markitdown_config_fixture(mock_markitdown_config):
    assert isinstance(mock_markitdown_config, MarkItDownConfig)
    assert mock_markitdown_config.enable_builtins is True
    assert mock_markitdown_config.enable_plugins is False


def test_mock_converter_fixture(mock_converter):
    result = mock_converter.convert("test")
    assert "Test Content" in result
    assert "mock converted content" in result


def test_test_file_content_fixture(test_file_content):
    assert isinstance(test_file_content, dict)
    assert "text" in test_file_content
    assert "json" in test_file_content
    assert "html" in test_file_content
    assert "empty" in test_file_content
    
    assert test_file_content["text"] == b"Hello World\nThis is a test file."
    assert test_file_content["empty"] == b""