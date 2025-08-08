import pytest
from httpx import AsyncClient, ASGITransport
from pathlib import Path
from md_server.app import app


test_data_dir = Path(__file__).parent.parent / "test_data"


@pytest.mark.integration
class TestConvertFileAPI:
    @pytest.mark.asyncio
    async def test_convert_pdf_file(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            pdf_path = test_data_dir / "test.pdf"

            with open(pdf_path, "rb") as f:
                files = {"file": ("test.pdf", f, "application/pdf")}
                response = await client.post("/convert", files=files)

            assert response.status_code == 200
            data = response.json()
            assert "markdown" in data
            assert isinstance(data["markdown"], str)
            assert len(data["markdown"]) > 0

    @pytest.mark.asyncio
    async def test_convert_docx_file(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            docx_path = test_data_dir / "test.docx"

            with open(docx_path, "rb") as f:
                files = {
                    "file": (
                        "test.docx",
                        f,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                }
                response = await client.post("/convert", files=files)

            assert response.status_code == 200
            data = response.json()
            assert "markdown" in data
            assert isinstance(data["markdown"], str)
            assert len(data["markdown"]) > 0

    @pytest.mark.asyncio
    async def test_convert_html_file(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            html_path = test_data_dir / "test_blog.html"

            with open(html_path, "rb") as f:
                files = {"file": ("test_blog.html", f, "text/html")}
                response = await client.post("/convert", files=files)

            assert response.status_code == 200
            data = response.json()
            assert "markdown" in data
            assert isinstance(data["markdown"], str)

    @pytest.mark.asyncio
    async def test_convert_pptx_file(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            pptx_path = test_data_dir / "test.pptx"

            with open(pptx_path, "rb") as f:
                files = {
                    "file": (
                        "test.pptx",
                        f,
                        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    )
                }
                response = await client.post("/convert", files=files)

            assert response.status_code == 200
            data = response.json()
            assert "markdown" in data
            assert isinstance(data["markdown"], str)

    @pytest.mark.asyncio
    async def test_convert_xlsx_file(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            xlsx_path = test_data_dir / "test.xlsx"

            with open(xlsx_path, "rb") as f:
                files = {
                    "file": (
                        "test.xlsx",
                        f,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                }
                response = await client.post("/convert", files=files)

            assert response.status_code == 200
            data = response.json()
            assert "markdown" in data
            assert isinstance(data["markdown"], str)

    @pytest.mark.asyncio
    async def test_convert_unsupported_file_type(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            bin_path = test_data_dir / "random.bin"

            with open(bin_path, "rb") as f:
                files = {"file": ("random.bin", f, "application/octet-stream")}
                response = await client.post("/convert", files=files)

            assert response.status_code in [415, 500]
            data = response.json()
            assert "detail" in data

    @pytest.mark.asyncio
    async def test_convert_missing_file(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/convert")

            assert response.status_code == 400
            data = response.json()
            assert "detail" in data

    @pytest.mark.asyncio
    async def test_convert_empty_file(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            files = {"file": ("empty.txt", b"", "text/plain")}
            response = await client.post("/convert", files=files)

            assert response.status_code == 200
            data = response.json()
            assert "markdown" in data
            assert data["markdown"] == ""

    @pytest.mark.asyncio
    async def test_convert_text_file(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            content = b"Hello World\nThis is a test file."
            files = {"file": ("test.txt", content, "text/plain")}
            response = await client.post("/convert", files=files)

            assert response.status_code == 200
            data = response.json()
            assert "markdown" in data
            assert "Hello World" in data["markdown"]
            assert "This is a test file" in data["markdown"]

    @pytest.mark.asyncio
    async def test_convert_json_file(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            json_path = test_data_dir / "test.json"

            with open(json_path, "rb") as f:
                files = {"file": ("test.json", f, "application/json")}
                response = await client.post("/convert", files=files)

            assert response.status_code == 200
            data = response.json()
            assert "markdown" in data
            assert isinstance(data["markdown"], str)

    @pytest.mark.asyncio
    async def test_convert_response_format(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            content = b"Test content"
            files = {"file": ("test.txt", content, "text/plain")}
            response = await client.post("/convert", files=files)

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, dict)
            assert "markdown" in data
            assert len(data) == 1
            assert isinstance(data["markdown"], str)

    @pytest.mark.asyncio
    async def test_convert_with_special_characters(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            content = "Special chars: åäö ñ 中文 🚀".encode("utf-8")
            files = {"file": ("special.txt", content, "text/plain")}
            response = await client.post("/convert", files=files)

            assert response.status_code == 200
            data = response.json()
            assert "markdown" in data
            assert "åäö" in data["markdown"]
            assert "中文" in data["markdown"]
            assert "🚀" in data["markdown"]
