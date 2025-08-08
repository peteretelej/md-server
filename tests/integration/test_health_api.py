import pytest
from litestar.testing import AsyncTestClient
from md_server.app import app


@pytest.mark.integration
class TestHealthAPI:
    @pytest.mark.asyncio
    async def test_health_check_endpoint(self):
        async with AsyncTestClient(app=app) as client:
            response = await client.get("/healthz")

            assert response.status_code == 200
            assert response.json() == {"status": "healthy"}

    @pytest.mark.asyncio
    async def test_health_check_response_format(self):
        async with AsyncTestClient(app=app) as client:
            response = await client.get("/healthz")

            data = response.json()
            assert isinstance(data, dict)
            assert "status" in data
            assert data["status"] == "healthy"
            assert len(data) == 1

    @pytest.mark.asyncio
    async def test_health_check_content_type(self):
        async with AsyncTestClient(app=app) as client:
            response = await client.get("/healthz")

            assert response.headers["content-type"] == "application/json"

    @pytest.mark.asyncio
    async def test_health_check_service_availability(self):
        async with AsyncTestClient(app=app) as client:
            response = await client.get("/healthz")

            assert response.status_code == 200
            assert response.json()["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_multiple_requests(self):
        async with AsyncTestClient(app=app) as client:
            for _ in range(5):
                response = await client.get("/healthz")
                assert response.status_code == 200
                assert response.json() == {"status": "healthy"}

    @pytest.mark.asyncio
    async def test_health_check_method_not_allowed(self):
        async with AsyncTestClient(app=app) as client:
            response = await client.post("/healthz")
            assert response.status_code == 405

    @pytest.mark.asyncio
    async def test_health_check_with_query_params(self):
        async with AsyncTestClient(app=app) as client:
            response = await client.get("/healthz?test=1")
            assert response.status_code == 200
            assert response.json() == {"status": "healthy"}
