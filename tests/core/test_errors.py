"""Tests for the shared error module."""

import pytest

from md_server.core.errors import (
    ErrorCode,
    NotFoundError,
    AccessDeniedError,
    ServerError,
    URLTimeoutError,
    URLConnectionError,
    parse_http_status_from_error,
    classify_http_error,
)


class TestParseHttpStatusFromError:
    """Tests for parse_http_status_from_error function."""

    def test_parse_404_client_error(self):
        """Test parsing 404 Client Error."""
        error = Exception(
            "404 Client Error: Not Found for url: https://example.com/page"
        )
        status_code, message = parse_http_status_from_error(error)
        assert status_code == 404
        assert message == "Not Found"

    def test_parse_500_server_error(self):
        """Test parsing 500 Server Error."""
        error = Exception(
            "500 Server Error: Internal Server Error for url: https://example.com/api"
        )
        status_code, message = parse_http_status_from_error(error)
        assert status_code == 500
        assert message == "Internal Server Error"

    def test_parse_403_forbidden(self):
        """Test parsing 403 Forbidden."""
        error = Exception(
            "403 Client Error: Forbidden for url: https://example.com/secret"
        )
        status_code, message = parse_http_status_from_error(error)
        assert status_code == 403
        assert message == "Forbidden"

    def test_parse_503_service_unavailable(self):
        """Test parsing 503 Service Unavailable."""
        error = Exception(
            "503 Server Error: Service Unavailable for url: https://example.com"
        )
        status_code, message = parse_http_status_from_error(error)
        assert status_code == 503
        assert message == "Service Unavailable"

    def test_parse_unrecognized_error(self):
        """Test parsing an unrecognized error format."""
        error = Exception("Something went wrong")
        status_code, message = parse_http_status_from_error(error)
        assert status_code is None
        assert message == "Something went wrong"

    def test_parse_case_insensitive(self):
        """Test that parsing is case insensitive."""
        error = Exception("404 client error: not found for url: https://example.com")
        status_code, message = parse_http_status_from_error(error)
        assert status_code == 404
        assert message == "not found"


class TestClassifyHttpError:
    """Tests for classify_http_error function."""

    def test_classify_404_returns_not_found_error(self):
        """Test that 404 is classified as NotFoundError."""
        error = Exception(
            "404 Client Error: Not Found for url: https://example.com/page"
        )
        url = "https://example.com/page"
        result = classify_http_error(error, url)
        assert isinstance(result, NotFoundError)
        assert result.code == ErrorCode.NOT_FOUND
        assert result.status_code == 404
        assert result.url == url

    def test_classify_401_returns_access_denied_error(self):
        """Test that 401 is classified as AccessDeniedError."""
        error = Exception("401 Client Error: Unauthorized for url: https://example.com")
        url = "https://example.com"
        result = classify_http_error(error, url)
        assert isinstance(result, AccessDeniedError)
        assert result.code == ErrorCode.ACCESS_DENIED
        assert result.status_code == 401

    def test_classify_403_returns_access_denied_error(self):
        """Test that 403 is classified as AccessDeniedError."""
        error = Exception("403 Client Error: Forbidden for url: https://example.com")
        url = "https://example.com"
        result = classify_http_error(error, url)
        assert isinstance(result, AccessDeniedError)
        assert result.code == ErrorCode.ACCESS_DENIED
        assert result.status_code == 403

    def test_classify_500_returns_server_error(self):
        """Test that 500 is classified as ServerError."""
        error = Exception(
            "500 Server Error: Internal Server Error for url: https://example.com"
        )
        url = "https://example.com"
        result = classify_http_error(error, url)
        assert isinstance(result, ServerError)
        assert result.code == ErrorCode.SERVER_ERROR
        assert result.status_code == 500

    def test_classify_503_returns_server_error(self):
        """Test that 503 is classified as ServerError."""
        error = Exception(
            "503 Server Error: Service Unavailable for url: https://example.com"
        )
        url = "https://example.com"
        result = classify_http_error(error, url)
        assert isinstance(result, ServerError)
        assert result.code == ErrorCode.SERVER_ERROR
        assert result.status_code == 503

    def test_classify_timeout_in_message(self):
        """Test that timeout in error message is classified correctly."""
        error = Exception("Connection timed out")
        url = "https://example.com"
        result = classify_http_error(error, url)
        assert result.code == ErrorCode.TIMEOUT

    def test_classify_connection_in_message(self):
        """Test that connection error in message is classified correctly."""
        error = Exception("Connection refused by server")
        url = "https://example.com"
        result = classify_http_error(error, url)
        assert result.code == ErrorCode.CONNECTION_FAILED

    def test_classify_unknown_error(self):
        """Test that unknown errors are classified as CONNECTION_FAILED."""
        error = Exception("Something completely unexpected")
        url = "https://example.com"
        result = classify_http_error(error, url)
        # Unknown fetch errors use CONNECTION_FAILED, not CONVERSION_FAILED
        assert result.code == ErrorCode.CONNECTION_FAILED

    @pytest.mark.parametrize(
        "error_msg,expected_code,expected_status",
        [
            # Parsed 5xx status codes
            ("502 Server Error: Bad Gateway for url: x", ErrorCode.SERVER_ERROR, 502),
            # Fallback pattern matching (no regex match)
            ("Resource was not found on server", ErrorCode.NOT_FOUND, 404),
            ("Got 404 when trying to fetch", ErrorCode.NOT_FOUND, 404),
            ("Access forbidden by policy", ErrorCode.ACCESS_DENIED, 403),
            ("Server returned 403", ErrorCode.ACCESS_DENIED, 403),
            ("Request unauthorized", ErrorCode.ACCESS_DENIED, 401),
            ("Got 401 from API", ErrorCode.ACCESS_DENIED, 401),
        ],
    )
    def test_classify_fallback_patterns(
        self, error_msg, expected_code, expected_status
    ):
        """Test classification of errors via regex and fallback patterns."""
        result = classify_http_error(Exception(error_msg), "https://example.com")
        assert result.code == expected_code
        assert result.status_code == expected_status


class TestNotFoundError:
    """Tests for NotFoundError exception."""

    def test_not_found_error_properties(self):
        """Test NotFoundError has correct properties."""
        url = "https://example.com/missing"
        error = NotFoundError(url)
        assert error.code == ErrorCode.NOT_FOUND
        assert error.status_code == 404
        assert error.url == url
        assert "Page not found" in str(error)
        assert url in str(error)
        assert len(error.suggestions) > 0

    def test_not_found_error_suggestions(self):
        """Test NotFoundError has relevant suggestions."""
        error = NotFoundError("https://example.com/missing")
        suggestions = error.suggestions
        assert any("url" in s.lower() for s in suggestions)


class TestAccessDeniedError:
    """Tests for AccessDeniedError exception."""

    def test_access_denied_401(self):
        """Test AccessDeniedError with 401 status code."""
        url = "https://example.com/protected"
        error = AccessDeniedError(url, 401)
        assert error.code == ErrorCode.ACCESS_DENIED
        assert error.status_code == 401
        assert any("authentication" in s.lower() for s in error.suggestions)

    def test_access_denied_403(self):
        """Test AccessDeniedError with 403 status code."""
        url = "https://example.com/forbidden"
        error = AccessDeniedError(url, 403)
        assert error.code == ErrorCode.ACCESS_DENIED
        assert error.status_code == 403
        assert any("permission" in s.lower() for s in error.suggestions)


class TestServerError:
    """Tests for ServerError exception."""

    def test_server_error_500(self):
        """Test ServerError with 500 status code."""
        url = "https://example.com/api"
        error = ServerError(url, 500)
        assert error.code == ErrorCode.SERVER_ERROR
        assert error.status_code == 500
        assert any("server" in s.lower() for s in error.suggestions)

    def test_server_error_503(self):
        """Test ServerError with 503 status code."""
        url = "https://example.com/api"
        error = ServerError(url, 503)
        assert error.code == ErrorCode.SERVER_ERROR
        assert error.status_code == 503


class TestURLTimeoutError:
    """Tests for URLTimeoutError exception."""

    def test_timeout_error_properties(self):
        """Test URLTimeoutError has correct properties."""
        url = "https://example.com/slow"
        timeout = 30
        error = URLTimeoutError(url, timeout)
        assert error.code == ErrorCode.TIMEOUT
        assert error.url == url
        assert error.timeout == timeout
        assert "timed out" in str(error).lower()
        assert str(timeout) in str(error)


class TestURLConnectionError:
    """Tests for URLConnectionError exception."""

    def test_connection_error_properties(self):
        """Test URLConnectionError has correct properties."""
        url = "https://example.com"
        reason = "Connection refused"
        error = URLConnectionError(url, reason)
        assert error.code == ErrorCode.CONNECTION_FAILED
        assert error.url == url
        assert error.reason == reason
        assert "connect" in str(error).lower()


class TestErrorCode:
    """Tests for ErrorCode enum."""

    def test_error_codes_are_strings(self):
        """Test that error codes are string values."""
        assert ErrorCode.NOT_FOUND.value == "NOT_FOUND"
        assert ErrorCode.SERVER_ERROR.value == "SERVER_ERROR"
        assert ErrorCode.TIMEOUT.value == "TIMEOUT"
        assert ErrorCode.CONNECTION_FAILED.value == "CONNECTION_FAILED"

    def test_server_error_code_exists(self):
        """Test that SERVER_ERROR code exists (new code)."""
        assert hasattr(ErrorCode, "SERVER_ERROR")
        assert ErrorCode.SERVER_ERROR.value == "SERVER_ERROR"
