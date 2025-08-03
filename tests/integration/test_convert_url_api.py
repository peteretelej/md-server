import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock
from md_server.main import app


@pytest.mark.integration
class TestConvertURLAPI:
    @pytest.mark.asyncio
    async def test_convert_valid_url(self):
        with patch('md_server.converters.url_converter.URLConverter.convert') as mock_convert:
            mock_convert.return_value = "# Test Content\n\nThis is converted from URL."
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/convert/url",
                    json={"url": "https://example.com/article"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert "markdown" in data
                assert data["markdown"] == "# Test Content\n\nThis is converted from URL."

    @pytest.mark.asyncio
    async def test_convert_url_response_format(self):
        with patch('md_server.converters.url_converter.URLConverter.convert') as mock_convert:
            mock_convert.return_value = "Sample markdown content"
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/convert/url",
                    json={"url": "https://example.com"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert isinstance(data, dict)
                assert "markdown" in data
                assert len(data) == 1
                assert isinstance(data["markdown"], str)

    @pytest.mark.asyncio
    async def test_convert_invalid_url_format(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/convert/url",
                json={"url": "not-a-valid-url"}
            )
            
            assert response.status_code == 422
            data = response.json()
            assert "detail" in data

    @pytest.mark.asyncio
    async def test_convert_missing_url(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/convert/url", json={})
            
            assert response.status_code == 422
            data = response.json()
            assert "detail" in data

    @pytest.mark.asyncio
    async def test_convert_url_with_timeout_error(self):
        from md_server.core.exceptions import ConversionTimeoutError
        
        with patch('md_server.converters.url_converter.URLConverter.convert') as mock_convert:
            mock_convert.side_effect = ConversionTimeoutError("Request timed out")
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/convert/url",
                    json={"url": "https://example.com/slow-page"}
                )
                
                assert response.status_code == 408
                data = response.json()
                assert "detail" in data
                assert "timed out" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_convert_url_with_fetch_error(self):
        from md_server.core.exceptions import URLFetchError
        
        with patch('md_server.converters.url_converter.URLConverter.convert') as mock_convert:
            mock_convert.side_effect = URLFetchError("Failed to fetch URL")
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/convert/url",
                    json={"url": "https://nonexistent.example.com"}
                )
                
                assert response.status_code == 400
                data = response.json()
                assert "detail" in data
                assert "Failed to fetch URL" in data["detail"]

    @pytest.mark.asyncio
    async def test_convert_url_with_generic_error(self):
        with patch('md_server.converters.url_converter.URLConverter.convert') as mock_convert:
            mock_convert.side_effect = Exception("Generic conversion error")
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/convert/url",
                    json={"url": "https://example.com"}
                )
                
                assert response.status_code == 500
                data = response.json()
                assert "detail" in data
                assert "Conversion failed" in data["detail"]

    @pytest.mark.asyncio
    async def test_convert_url_content_validation(self):
        with patch('md_server.converters.url_converter.URLConverter.convert') as mock_convert:
            mock_convert.return_value = "# Example Article\n\nThis is the content from the webpage.\n\n## Section 1\n\nMore details here."
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/convert/url",
                    json={"url": "https://example.com/article"}
                )
                
                assert response.status_code == 200
                data = response.json()
                markdown = data["markdown"]
                assert "Example Article" in markdown
                assert "Section 1" in markdown
                assert markdown.startswith("#")

    @pytest.mark.asyncio
    async def test_convert_url_with_different_schemes(self):
        test_urls = [
            "https://example.com",
            "http://example.com",
            "https://subdomain.example.com/path?param=value"
        ]
        
        with patch('md_server.converters.url_converter.URLConverter.convert') as mock_convert:
            mock_convert.return_value = "# URL Content"
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                for url in test_urls:
                    response = await client.post(
                        "/convert/url",
                        json={"url": url}
                    )
                    assert response.status_code == 200
                    data = response.json()
                    assert "markdown" in data

    @pytest.mark.asyncio
    async def test_convert_url_sanitization(self):
        with patch('md_server.converters.url_converter.URLConverter.convert') as mock_convert:
            mock_convert.return_value = "# Sanitized Content"
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/convert/url",
                    json={"url": "https://example.com/path with spaces"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert "markdown" in data

    @pytest.mark.asyncio
    async def test_convert_url_empty_response(self):
        with patch('md_server.converters.url_converter.URLConverter.convert') as mock_convert:
            mock_convert.return_value = ""
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/convert/url",
                    json={"url": "https://example.com/empty"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert "markdown" in data
                assert data["markdown"] == ""

    @pytest.mark.asyncio
    async def test_convert_url_wrong_content_type(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/convert/url",
                data="url=https://example.com",
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            assert response.status_code == 422