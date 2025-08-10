import base64
from unittest.mock import patch, Mock
import pytest
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_408_REQUEST_TIMEOUT,
    HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    HTTP_500_INTERNAL_SERVER_ERROR,
)


class TestHealthEndpoints:
    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "uptime_seconds" in data
        assert "version" in data
        assert data["conversions_last_hour"] == 0

    def test_healthz_legacy_endpoint(self, client):
        response = client.get("/healthz")
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"

    def test_formats_endpoint(self, client):
        response = client.get("/formats")
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert "formats" in data
        assert isinstance(data["formats"], dict)
        assert len(data["formats"]) > 0


class TestConvertAPI:
    @pytest.fixture
    def mock_converter(self):
        with patch("md_server.app.provide_converter") as mock_provide:
            mock_conv = Mock()
            mock_conv.convert.return_value = Mock(text_content="# Converted Content")
            mock_provide.return_value = mock_conv
            yield mock_conv

    @pytest.fixture
    def mock_url_converter(self):
        with patch("md_server.app.provide_url_converter") as mock_provide:
            mock_url_conv = Mock()
            # Make it async
            mock_url_conv.convert_url = Mock(return_value="# URL Content")
            mock_provide.return_value = mock_url_conv
            yield mock_url_conv

    def test_convert_json_text_success(self, client, mock_converter):
        payload = {"text": "Hello world", "options": {"clean_markdown": True}}
        response = client.post("/convert", json=payload)

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["success"]
        assert data["markdown"] == "Hello world"
        assert data["metadata"]["source_type"] == "text"
        assert "conversion_time_ms" in data["metadata"]

    @patch("md_server.converter.validate_url")
    def test_convert_json_url_success(self, mock_validate, client, mock_url_converter):
        mock_validate.return_value = "https://example.com"
        payload = {"url": "https://example.com", "options": {"js_rendering": True}}

        response = client.post("/convert", json=payload)

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["success"]
        assert data["metadata"]["source_type"] == "url"
        # Don't check exact markdown content as it may vary

    def test_convert_json_base64_success(self, client, mock_converter, sample_files):
        with open(sample_files["json"], "rb") as f:
            content = base64.b64encode(f.read()).decode()

        payload = {
            "content": content,
            "filename": "test.json",
            "options": {"max_length": 1000},
        }

        response = client.post("/convert", json=payload)

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["success"]
        assert data["markdown"] == "# Converted Content"

    def test_convert_multipart_upload_success(
        self, client, mock_converter, sample_files
    ):
        with open(sample_files["pdf"], "rb") as f:
            content = f.read()

        files = {"file": (sample_files["pdf"].name, content, "application/pdf")}
        response = client.post("/convert", files=files)

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["success"]
        assert data["markdown"] == "# Converted Content"
        assert data["metadata"]["source_type"] == "pdf"

    def test_convert_binary_upload_success(self, client, mock_converter, sample_files):
        with open(sample_files["docx"], "rb") as f:
            content = f.read()

        response = client.post(
            "/convert",
            content=content,
            headers={
                "Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            },
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["success"]
        assert data["markdown"] == "# Converted Content"

    def test_convert_invalid_json_error(self, client):
        response = client.post(
            "/convert",
            content="{invalid json}",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == HTTP_400_BAD_REQUEST
        data = response.json()
        assert not data["success"]
        assert data["error"]["code"] == "INVALID_INPUT"

    def test_convert_missing_multipart_file_error(self, client):
        response = client.post(
            "/convert",
            data={"not_file": "value"},
            headers={"Content-Type": "multipart/form-data"},
        )

        assert response.status_code == HTTP_400_BAD_REQUEST
        data = response.json()
        assert not data["success"]
        assert "File parameter 'file' is required" in data["error"]["message"]

    def test_convert_invalid_base64_error(self, client, mock_converter):
        payload = {"content": "invalid-base64!", "filename": "test.txt"}

        response = client.post("/convert", json=payload)

        assert response.status_code == HTTP_400_BAD_REQUEST
        data = response.json()
        assert not data["success"]
        assert data["error"]["code"] == "INVALID_INPUT"

    @patch("md_server.controllers.FileSizeValidator.validate_size")
    def test_convert_file_too_large_error(self, mock_validate, client, sample_files):
        mock_validate.side_effect = ValueError("File size exceeds maximum allowed")

        with open(sample_files["pdf"], "rb") as f:
            content = f.read()

        files = {"file": (sample_files["pdf"].name, content, "application/pdf")}
        response = client.post("/convert", files=files)

        assert response.status_code == 413
        data = response.json()
        assert not data["success"]
        assert data["error"]["code"] == "FILE_TOO_LARGE"

    @patch("md_server.controllers.ContentValidator.validate_content_type")
    def test_convert_content_type_mismatch_error(
        self, mock_validate, client, sample_files
    ):
        mock_validate.side_effect = ValueError("Content type mismatch detected")

        with open(sample_files["pdf"], "rb") as f:
            content = f.read()

        files = {"file": (sample_files["pdf"].name, content, "text/plain")}
        response = client.post("/convert", files=files)

        assert response.status_code == HTTP_400_BAD_REQUEST
        data = response.json()
        assert not data["success"]
        assert data["error"]["code"] == "INVALID_CONTENT"

    @patch("asyncio.wait_for")
    def test_convert_timeout_error(self, mock_wait_for, client, mock_converter):
        from asyncio import TimeoutError

        mock_wait_for.side_effect = TimeoutError()

        payload = {"text": "Hello world"}
        response = client.post("/convert", json=payload)

        assert response.status_code == HTTP_408_REQUEST_TIMEOUT
        data = response.json()
        assert not data["success"]
        assert data["error"]["code"] == "TIMEOUT"

    def test_convert_unsupported_format_error(self, client, mock_converter):
        mock_converter.convert.side_effect = ValueError("Unsupported file format")

        payload = {"text": "Hello world"}
        response = client.post("/convert", json=payload)

        assert response.status_code == HTTP_415_UNSUPPORTED_MEDIA_TYPE
        data = response.json()
        assert not data["success"]
        assert data["error"]["code"] == "UNSUPPORTED_FORMAT"

    def test_convert_generic_error(self, client, mock_converter):
        mock_converter.convert.side_effect = RuntimeError("Something went wrong")

        payload = {"text": "Hello world"}
        response = client.post("/convert", json=payload)

        assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert not data["success"]
        assert data["error"]["code"] == "CONVERSION_FAILED"

    def test_convert_with_options_success(self, client, mock_converter):
        payload = {
            "text": "Long text content that might need truncation",
            "options": {"clean_markdown": True, "max_length": 10, "timeout": 30},
        }

        response = client.post("/convert", json=payload)

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["success"]
        assert len(data["markdown"]) <= 13  # 10 chars + "..."

    def test_convert_empty_content(self, client, mock_converter):
        response = client.post(
            "/convert",
            content=b"",
            headers={"Content-Type": "application/octet-stream"},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["success"]

    def test_convert_large_text_truncation(self, client):
        large_text = "a" * 2000
        payload = {"text": large_text, "options": {"max_length": 100}}

        response = client.post("/convert", json=payload)

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert len(data["markdown"]) == 103  # 100 + "..."
        assert data["markdown"].endswith("...")

    def test_convert_response_structure(self, client, mock_converter):
        payload = {"text": "Test content"}

        response = client.post("/convert", json=payload)

        assert response.status_code == HTTP_200_OK
        data = response.json()

        # Verify response structure
        assert "success" in data
        assert "markdown" in data
        assert "metadata" in data
        assert "request_id" in data
        assert "source_type" in data["metadata"]
        assert "source_size" in data["metadata"]
        assert "conversion_time_ms" in data["metadata"]
        assert "detected_format" in data["metadata"]
        assert "warnings" in data["metadata"]
