import pytest
from unittest.mock import Mock
from litestar.exceptions import HTTPException
from litestar.status_codes import (
    HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from md_server.controllers import ConvertController


class TestConvertControllerErrorHandling:
    def test_handle_generic_error_unsupported_format(self):
        """Test generic error handler for unsupported formats"""
        controller = ConvertController(owner=Mock())

        with pytest.raises(HTTPException) as exc_info:
            controller._handle_generic_error("File format unsupported", "pdf")

        assert exc_info.value.status_code == HTTP_415_UNSUPPORTED_MEDIA_TYPE
        detail = exc_info.value.detail
        assert detail["error"]["code"] == "UNSUPPORTED_FORMAT"
        assert "unsupported" in detail["error"]["message"].lower()
        assert detail["error"]["details"]["detected_format"] == "pdf"
        assert "Check supported formats at /formats" in detail["error"]["suggestions"]

    def test_handle_generic_error_unsupported_format_no_type(self):
        """Test generic error handler for unsupported formats without format type"""
        controller = ConvertController(owner=Mock())

        with pytest.raises(HTTPException) as exc_info:
            controller._handle_generic_error("This format is unsupported")

        assert exc_info.value.status_code == HTTP_415_UNSUPPORTED_MEDIA_TYPE
        detail = exc_info.value.detail
        assert detail["error"]["code"] == "UNSUPPORTED_FORMAT"
        assert detail["error"]["details"] is None

    def test_handle_generic_error_conversion_failed(self):
        """Test generic error handler for conversion failures"""
        controller = ConvertController(owner=Mock())

        with pytest.raises(HTTPException) as exc_info:
            controller._handle_generic_error("Something went wrong", "docx")

        assert exc_info.value.status_code == HTTP_500_INTERNAL_SERVER_ERROR
        detail = exc_info.value.detail
        assert detail["error"]["code"] == "CONVERSION_FAILED"
        assert "Conversion failed: Something went wrong" in detail["error"]["message"]

    def test_handle_generic_error_general_failure(self):
        """Test generic error handler for general failures"""
        controller = ConvertController(owner=Mock())

        with pytest.raises(HTTPException) as exc_info:
            controller._handle_generic_error("Database connection failed")

        assert exc_info.value.status_code == HTTP_500_INTERNAL_SERVER_ERROR
        detail = exc_info.value.detail
        assert detail["error"]["code"] == "CONVERSION_FAILED"
        assert (
            "Conversion failed: Database connection failed"
            in detail["error"]["message"]
        )


class TestConvertControllerExceptionHandling:
    def test_size_calculation_default_return(self):
        """Test default return 0 in size calculation"""
        controller = ConvertController(owner=Mock())

        # Test with empty data - this should hit line 216
        result = controller._calculate_source_size("unknown_type", {}, {})
        assert result == 0

        # Test with None content_data
        result = controller._calculate_source_size("multipart", {}, None)
        assert result == 0
