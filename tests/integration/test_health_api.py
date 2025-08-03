import pytest
from httpx import AsyncClient, ASGITransport
from md_server.main import app


@pytest.mark.integration
class TestHealthAPI:
    @pytest.mark.asyncio
    async def test_health_check_endpoint(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/healthz")
            
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_health_check_response_format(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/healthz")
            
            data = response.json()
            assert isinstance(data, dict)
            assert "status" in data
            assert data["status"] == "ok"
            assert len(data) == 1

    @pytest.mark.asyncio
    async def test_health_check_content_type(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/healthz")
            
            assert response.headers["content-type"] == "application/json"

    @pytest.mark.asyncio
    async def test_health_check_service_availability(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/healthz")
            
            assert response.status_code == 200
            assert response.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_health_check_multiple_requests(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for _ in range(5):
                response = await client.get("/healthz")
                assert response.status_code == 200
                assert response.json() == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_health_check_method_not_allowed(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/healthz")
            assert response.status_code == 405

    @pytest.mark.asyncio
    async def test_health_check_with_query_params(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/healthz?test=1")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}