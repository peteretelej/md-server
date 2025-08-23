"""Test controller error handling and mapping"""

import pytest
from litestar.testing import TestClient
from litestar.status_codes import (
    HTTP_400_BAD_REQUEST,
    HTTP_408_REQUEST_TIMEOUT,
    HTTP_413_REQUEST_ENTITY_TOO_LARGE,
    HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from md_server.app import app
from md_server.sdk.exceptions import (
    ConversionError,
    FileSizeError,
    InvalidInputError,
    NetworkError,
    TimeoutError,
    UnsupportedFormatError,
)
from md_server.core.error_mapper import map_conversion_error, map_value_error, map_generic_error


class TestErrorMapping:
    """Test error mapping functions"""
    
    @pytest.mark.parametrize("exception,expected_code,expected_status", [
        (UnsupportedFormatError("unsupported"), "UNSUPPORTED_FORMAT", HTTP_415_UNSUPPORTED_MEDIA_TYPE),
        (InvalidInputError("invalid"), "INVALID_INPUT", HTTP_400_BAD_REQUEST),
        (FileSizeError("too large"), "FILE_TOO_LARGE", HTTP_413_REQUEST_ENTITY_TOO_LARGE),
        (TimeoutError("timeout"), "TIMEOUT", HTTP_408_REQUEST_TIMEOUT),
        (NetworkError("network"), "NETWORK_ERROR", HTTP_400_BAD_REQUEST),
        (ConversionError("failed"), "CONVERSION_FAILED", HTTP_500_INTERNAL_SERVER_ERROR),
    ])
    def test_sdk_exception_mapping(self, exception, expected_code, expected_status):
        """Test SDK exception mapping to HTTP responses"""
        code, message, status_code, suggestions = map_conversion_error(exception)
        assert code == expected_code
        assert status_code == expected_status
        assert str(exception) in message
        assert len(suggestions) > 0

    @pytest.mark.parametrize("error_msg,expected_code,expected_status", [
        ("File size exceeds limit", "FILE_TOO_LARGE", HTTP_413_REQUEST_ENTITY_TOO_LARGE),
        ("URL is blocked", "INVALID_URL", HTTP_400_BAD_REQUEST),
        ("content type mismatch", "INVALID_CONTENT", HTTP_400_BAD_REQUEST),
        ("generic error", "INVALID_INPUT", HTTP_400_BAD_REQUEST),
    ])
    def test_value_error_mapping(self, error_msg, expected_code, expected_status):
        """Test ValueError message mapping"""
        code, status_code, suggestions = map_value_error(error_msg)
        assert code == expected_code
        assert status_code == expected_status
        assert len(suggestions) > 0

    @pytest.mark.parametrize("error_msg,expected_code,expected_status", [
        ("format is unsupported", "UNSUPPORTED_FORMAT", HTTP_415_UNSUPPORTED_MEDIA_TYPE),
        ("generic failure", "CONVERSION_FAILED", HTTP_500_INTERNAL_SERVER_ERROR),
    ])
    def test_generic_error_mapping(self, error_msg, expected_code, expected_status):
        """Test generic exception mapping"""
        code, status_code, _details, suggestions = map_generic_error(error_msg)
        assert code == expected_code
        assert status_code == expected_status
        assert len(suggestions) > 0


class TestControllerErrorScenarios:
    """Test basic controller error scenarios that work reliably"""
    
    def test_missing_input_error(self):
        """Test missing required input triggers 400 response"""
        with TestClient(app) as client:
            response = client.post("/convert", json={})
            
            assert response.status_code == 400
            # HTTPException puts data in detail field
            data = response.json()["detail"]
            assert data["success"] is False
            assert data["error"]["code"] == "INVALID_INPUT"
            assert "request_id" in data
            assert data["request_id"].startswith("req_")

    def test_invalid_base64_error(self):
        """Test invalid base64 content triggers 400 response"""
        with TestClient(app) as client:
            response = client.post("/convert", json={"content": "invalid-base64"})
            
            assert response.status_code == 400
            data = response.json()["detail"]
            assert data["success"] is False
            assert data["error"]["code"] == "INVALID_INPUT"
            assert "Invalid base64 content" in data["error"]["message"]


class TestRequestIDGeneration:
    """Test request ID generation and format"""
    
    def test_request_id_uniqueness_and_format(self):
        """Test request ID uniqueness and UUID format"""
        import re
        
        with TestClient(app) as client:
            # Generate multiple request IDs
            request_ids = []
            for i in range(3):
                response = client.post("/convert", json={"text": f"test {i}"})
                assert response.status_code == 200
                request_ids.append(response.json()["request_id"])
            
            # Check uniqueness
            assert len(request_ids) == len(set(request_ids))
            
            # Check UUID4 format
            uuid_pattern = r"^req_[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
            for request_id in request_ids:
                assert re.match(uuid_pattern, request_id), f"Invalid format: {request_id}"