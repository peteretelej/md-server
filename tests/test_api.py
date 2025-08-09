import pytest
from litestar.testing import AsyncTestClient
from pathlib import Path
from unittest.mock import patch

from md_server.app import app


test_data_dir = Path(__file__).parent / "test_data"


class TestAPI:
    """Simplified test suite covering all essential API functionality"""

    @pytest.mark.asyncio
    async def test_health_check(self):
        async with AsyncTestClient(app=app) as client:
            response = await client.get("/healthz")

            assert response.status_code == 200
            assert response.json() == {"status": "healthy"}

    @pytest.mark.asyncio
    async def test_convert_text_file(self):
        async with AsyncTestClient(app=app) as client:
            content = b"Hello World\nThis is a test."
            files = {"file": ("test.txt", content, "text/plain")}
            response = await client.post("/convert", files=files)

            assert response.status_code == 200
            data = response.json()
            assert "markdown" in data
            assert "Hello World" in data["markdown"]

    @pytest.mark.asyncio
    async def test_convert_pdf_file(self):
        async with AsyncTestClient(app=app) as client:
            pdf_path = test_data_dir / "test.pdf"

            with open(pdf_path, "rb") as f:
                files = {"file": ("test.pdf", f, "application/pdf")}
                response = await client.post("/convert", files=files)

            assert response.status_code == 200
            data = response.json()
            assert "markdown" in data
            assert len(data["markdown"]) > 0

    @pytest.mark.asyncio
    async def test_convert_missing_file(self):
        async with AsyncTestClient(app=app) as client:
            response = await client.post("/convert")

            assert response.status_code == 400
            data = response.json()
            assert "detail" in data

    @pytest.mark.asyncio
    async def test_convert_url_success(self):
        with patch("md_server.converter.UrlConverter.convert_url") as mock_convert:
            mock_convert.return_value = "# Test Content"

            async with AsyncTestClient(app=app) as client:
                response = await client.post(
                    "/convert/url", json={"url": "https://example.com"}
                )

                assert response.status_code == 200
                data = response.json()
                assert data["markdown"] == "# Test Content"
                mock_convert.assert_called_once_with("https://example.com", None)

    @pytest.mark.asyncio
    async def test_convert_url_with_js_rendering(self):
        """Test URL conversion with JavaScript rendering enabled"""
        with patch("md_server.converter.UrlConverter.convert_url") as mock_convert:
            mock_convert.return_value = (
                "# Dynamic Content\n\nJavaScript rendered content"
            )

            async with AsyncTestClient(app=app) as client:
                response = await client.post(
                    "/convert/url",
                    json={"url": "https://spa-example.com", "js_rendering": True},
                )

                assert response.status_code == 200
                data = response.json()
                assert (
                    data["markdown"]
                    == "# Dynamic Content\n\nJavaScript rendered content"
                )
                mock_convert.assert_called_once_with("https://spa-example.com", True)

    @pytest.mark.asyncio
    async def test_convert_url_with_js_rendering_false(self):
        """Test URL conversion with JavaScript rendering explicitly disabled"""
        with patch("md_server.converter.UrlConverter.convert_url") as mock_convert:
            mock_convert.return_value = "# Static Content"

            async with AsyncTestClient(app=app) as client:
                response = await client.post(
                    "/convert/url",
                    json={"url": "https://example.com", "js_rendering": False},
                )

                assert response.status_code == 200
                data = response.json()
                assert data["markdown"] == "# Static Content"
                mock_convert.assert_called_once_with("https://example.com", False)

    @pytest.mark.asyncio
    async def test_convert_url_conversion_error(self):
        """Test URL conversion when ValueError is raised"""
        with patch("md_server.converter.UrlConverter.convert_url") as mock_convert:
            mock_convert.side_effect = ValueError("Failed to crawl URL")

            async with AsyncTestClient(app=app) as client:
                response = await client.post(
                    "/convert/url", json={"url": "https://failing-url.com"}
                )

                assert response.status_code == 400  # Bad request for URL-related errors
                data = response.json()
                assert "Failed to crawl URL" in str(data["detail"])

    @pytest.mark.asyncio
    async def test_convert_url_invalid_format(self):
        async with AsyncTestClient(app=app) as client:
            response = await client.post("/convert/url", json={"url": "invalid-url"})

            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_convert_url_missing_data(self):
        async with AsyncTestClient(app=app) as client:
            response = await client.post("/convert/url", json={})

            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_convert_empty_file(self):
        async with AsyncTestClient(app=app) as client:
            files = {"file": ("empty.txt", b"", "text/plain")}
            response = await client.post("/convert", files=files)

            assert response.status_code == 200
            data = response.json()
            assert "markdown" in data
            assert data["markdown"] == ""
