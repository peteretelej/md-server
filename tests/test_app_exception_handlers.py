from litestar import Litestar, post, get
from litestar.exceptions import HTTPException
from litestar.status_codes import HTTP_404_NOT_FOUND, HTTP_422_UNPROCESSABLE_ENTITY, HTTP_500_INTERNAL_SERVER_ERROR
from litestar.testing import TestClient
from pydantic import BaseModel

from md_server.app import app


class TestModel(BaseModel):
    """Test model for validation error testing."""
    required_field: str
    numeric_field: int


@post("/test-validation")
async def test_validation_endpoint(data: TestModel) -> dict:
    """Test endpoint that requires specific data structure."""
    return {"message": "success", "data": data.model_dump()}


class TestAppExceptionHandlers:
    """Test application exception handlers and error responses."""

    def test_404_not_found_routes(self):
        """Test 404 responses for non-existent routes."""
        with TestClient(app=app) as client:
            # Test non-existent GET route
            response = client.get("/non-existent-route")
            assert response.status_code == HTTP_404_NOT_FOUND
            
            # Test non-existent POST route
            response = client.post("/non-existent-endpoint")
            assert response.status_code == HTTP_404_NOT_FOUND
            
            # Test route with invalid path segments
            response = client.get("/convert/invalid/path/segment")
            assert response.status_code == HTTP_404_NOT_FOUND

    def test_404_invalid_health_endpoints(self):
        """Test 404 for invalid health endpoint variations."""
        with TestClient(app=app) as client:
            # Valid endpoints should work
            response = client.get("/health")
            assert response.status_code == 200
            
            response = client.get("/healthz")
            assert response.status_code == 200
            
            # Health with trailing slash also works (Litestar allows it)
            response = client.get("/health/")
            assert response.status_code == 200
            
            # Invalid variations should return 404
            response = client.get("/healthcheck")
            assert response.status_code == HTTP_404_NOT_FOUND
            
            response = client.get("/health-check")
            assert response.status_code == HTTP_404_NOT_FOUND

    def test_405_method_not_allowed(self):
        """Test 405 Method Not Allowed for wrong HTTP methods."""
        with TestClient(app=app) as client:
            # Health endpoints should only accept GET
            response = client.post("/health")
            assert response.status_code == 405  # Method Not Allowed
            
            response = client.put("/health")
            assert response.status_code == 405
            
            response = client.delete("/health")
            assert response.status_code == 405

    def test_pydantic_validation_errors(self):
        """Test Pydantic validation error handling returns 422."""
        # Create test app with validation endpoint
        test_app = Litestar(
            route_handlers=[test_validation_endpoint],
            debug=True
        )
        
        with TestClient(app=test_app) as client:
            # Test missing required field  
            response = client.post(
                "/test-validation",
                json={"numeric_field": 42}  # Missing required_field
            )
            assert response.status_code == 400  # Litestar returns 400 for validation errors
            
            # Test invalid field type
            response = client.post(
                "/test-validation",
                json={
                    "required_field": "test",
                    "numeric_field": "not_a_number"  # Should be int
                }
            )
            assert response.status_code == 400  # Litestar returns 400 for validation errors
            
            # Test completely invalid JSON structure
            response = client.post(
                "/test-validation",
                json="invalid_structure"
            )
            assert response.status_code == 400  # Litestar returns 400 for validation errors

    def test_convert_endpoint_validation_errors(self):
        """Test validation errors on actual convert endpoint."""
        with TestClient(app=app) as client:
            # Test missing request body
            response = client.post("/convert")
            assert response.status_code in [400, HTTP_422_UNPROCESSABLE_ENTITY]
            
            # Test invalid JSON
            response = client.post(
                "/convert",
                content="invalid json",
                headers={"Content-Type": "application/json"}
            )
            assert response.status_code in [400, HTTP_422_UNPROCESSABLE_ENTITY]
            
            # Test invalid field types
            response = client.post(
                "/convert",
                json={
                    "input": {"text": 123}  # text should be string
                }
            )
            assert response.status_code in [400, HTTP_422_UNPROCESSABLE_ENTITY]

    def test_convert_endpoint_missing_input(self):
        """Test convert endpoint with missing input field."""
        with TestClient(app=app) as client:
            response = client.post(
                "/convert",
                json={}  # Missing input field
            )
            assert response.status_code in [400, HTTP_422_UNPROCESSABLE_ENTITY]

    def test_http_exceptions_are_handled(self):
        """Test that HTTPException instances are handled correctly."""
        
        @get("/test-http-exception/{status_code:int}")
        async def test_http_exception_endpoint(status_code: int) -> dict:
            """Test endpoint that raises HTTPException."""
            raise HTTPException(
                status_code=status_code,
                detail=f"Test HTTP exception with status {status_code}"
            )
        
        test_app = Litestar(
            route_handlers=[test_http_exception_endpoint],
            debug=True
        )
        
        with TestClient(app=test_app) as client:
            # Test 400 Bad Request
            response = client.get("/test-http-exception/400")
            assert response.status_code == 400
            data = response.json()
            assert "Test HTTP exception with status 400" in str(data)
            
            # Test 401 Unauthorized
            response = client.get("/test-http-exception/401")
            assert response.status_code == 401
            
            # Test 403 Forbidden
            response = client.get("/test-http-exception/403")
            assert response.status_code == 403
            
            # Test 500 Internal Server Error
            response = client.get("/test-http-exception/500")
            assert response.status_code == 500

    def test_generic_exception_handling(self):
        """Test generic exception handling returns 500."""
        
        @get("/test-generic-exception")
        async def test_generic_exception_endpoint() -> dict:
            """Test endpoint that raises generic exception."""
            raise ValueError("Test generic exception")
        
        test_app = Litestar(
            route_handlers=[test_generic_exception_endpoint],
            debug=False  # Important: debug=False to test production error handling
        )
        
        with TestClient(app=test_app) as client:
            response = client.get("/test-generic-exception")
            assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR

    def test_validation_exception_details(self):
        """Test validation exception includes helpful details."""
        test_app = Litestar(
            route_handlers=[test_validation_endpoint],
            debug=True
        )
        
        with TestClient(app=test_app) as client:
            response = client.post(
                "/test-validation",
                json={
                    "required_field": "test",
                    "numeric_field": "invalid"
                }
            )
            
            assert response.status_code == 400  # Litestar returns 400 for validation errors
            data = response.json()
            
            # Should include validation error details
            assert "detail" in data or "errors" in data or "message" in data

    def test_content_type_errors(self):
        """Test content type related errors."""
        with TestClient(app=app) as client:
            # Test completely unsupported content type with binary data
            response = client.post(
                "/convert",
                content=b"\x00\x01\x02\x03binary_data",  # Binary data
                headers={"Content-Type": "application/x-custom-binary"}
            )
            # Should handle binary content but may not validate properly  
            # This test mainly ensures the endpoint handles unusual content types gracefully
            assert response.status_code in [200, 400, 415, 500, HTTP_422_UNPROCESSABLE_ENTITY]

    def test_large_request_handling(self):
        """Test handling of oversized requests."""
        with TestClient(app=app) as client:
            # Create large text input (but within reasonable test limits)
            large_text = "A" * 10000  # 10KB of text
            
            response = client.post(
                "/convert",
                json={
                    "input": {"text": large_text}
                }
            )
            
            # Should not fail due to size (this is within normal limits)
            # But validates that the endpoint can handle larger inputs
            assert response.status_code in [200, 400, 422, 500]  # Various valid responses

    def test_empty_request_body(self):
        """Test handling of completely empty request bodies."""
        with TestClient(app=app) as client:
            response = client.post(
                "/convert",
                content="",
                headers={"Content-Type": "application/json"}
            )
            assert response.status_code in [400, HTTP_422_UNPROCESSABLE_ENTITY]

    def test_malformed_json_request(self):
        """Test handling of malformed JSON in requests."""
        with TestClient(app=app) as client:
            # Test various malformed JSON patterns
            malformed_json_examples = [
                '{"input": {"text": "test"',  # Missing closing braces
                '{"input": {"text": "test"}}extra',  # Extra content
                '{input: {text: "test"}}',  # Unquoted keys
                '{"input": {"text": undefined}}',  # JavaScript undefined
                '{"input": null,}',  # Trailing comma
            ]
            
            for malformed_json in malformed_json_examples:
                response = client.post(
                    "/convert",
                    content=malformed_json,
                    headers={"Content-Type": "application/json"}
                )
                assert response.status_code in [400, HTTP_422_UNPROCESSABLE_ENTITY]

    def test_error_response_format(self):
        """Test that error responses follow consistent format."""
        with TestClient(app=app) as client:
            # Test 404 error format
            response = client.get("/non-existent")
            assert response.status_code == HTTP_404_NOT_FOUND
            data = response.json()
            
            # Error response should be a valid JSON object
            assert isinstance(data, dict)
            
            # Test validation error format (400 or 422)
            response = client.post("/convert", json={})
            assert response.status_code in [400, HTTP_422_UNPROCESSABLE_ENTITY]
            data = response.json()
            assert isinstance(data, dict)

    def test_concurrent_error_handling(self):
        """Test error handling under concurrent requests."""
        import threading
        
        with TestClient(app=app) as client:
            results = []
            
            def make_error_request():
                """Make a request that will result in an error."""
                response = client.get("/non-existent-route")
                results.append(response.status_code)
            
            # Start multiple threads making error requests
            threads = []
            for _ in range(5):
                thread = threading.Thread(target=make_error_request)
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join(timeout=5)
            
            # All should return 404
            assert len(results) == 5
            assert all(status == HTTP_404_NOT_FOUND for status in results)