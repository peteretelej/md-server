import pytest
import asyncio
from pathlib import Path


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_data_dir():
    return Path(__file__).parent / "test_data"


@pytest.fixture
def simple_html_file(test_data_dir):
    return test_data_dir / "simple.html"


@pytest.fixture
def test_pdf_file(test_data_dir):
    return test_data_dir / "test.pdf"


@pytest.fixture
def test_docx_file(test_data_dir):
    return test_data_dir / "test.docx"


@pytest.fixture
def test_jpg_file(test_data_dir):
    return test_data_dir / "test.jpg"


@pytest.fixture(scope="session")
def test_server():
    from tests.test_server.server import TestHTTPServer, get_free_port

    server = TestHTTPServer(port=get_free_port())
    server.start()
    yield server
    server.stop()
