"""Tests for MCP error factories."""

import pytest
from md_server.mcp.errors import (
    ErrorCode,
    timeout_error,
    connection_error,
    not_found_error,
    access_denied_error,
    invalid_url_error,
    unsupported_format_error,
    file_too_large_error,
    content_empty_error,
    unknown_tool_error,
    conversion_error,
    invalid_input_error,
    SUPPORTED_FORMATS,
)


class TestErrorCode:
    """Tests for ErrorCode enum."""

    def test_all_codes_are_strings(self):
        """All error codes should be string values."""
        for code in ErrorCode:
            assert isinstance(code.value, str)

    def test_expected_codes_exist(self):
        """Should have all expected error codes."""
        expected = [
            "TIMEOUT",
            "CONNECTION_FAILED",
            "NOT_FOUND",
            "ACCESS_DENIED",
            "INVALID_URL",
            "UNSUPPORTED_FORMAT",
            "FILE_TOO_LARGE",
            "CONVERSION_FAILED",
            "CONTENT_EMPTY",
            "INVALID_INPUT",
            "UNKNOWN_TOOL",
        ]
        actual = [code.value for code in ErrorCode]
        for code in expected:
            assert code in actual


class TestTimeoutError:
    """Tests for timeout_error factory."""

    def test_creates_error_response(self):
        """Should create an error response."""
        result = timeout_error("URL fetch", 60)
        assert result.success is False
        assert result.error.code == ErrorCode.TIMEOUT

    def test_includes_timeout_in_message(self):
        """Message should include the timeout value."""
        result = timeout_error("URL fetch", 60)
        assert "60" in result.error.message

    def test_includes_operation_in_message(self):
        """Message should include the operation name."""
        result = timeout_error("File conversion", 30)
        assert "File conversion" in result.error.message

    def test_has_suggestions(self):
        """Should include helpful suggestions."""
        result = timeout_error("URL fetch", 60)
        assert len(result.error.suggestions) > 0


class TestConnectionError:
    """Tests for connection_error factory."""

    def test_includes_url_in_message(self):
        """Message should include the URL."""
        result = connection_error("https://example.com", "Connection refused")
        assert "example.com" in result.error.message

    def test_includes_reason_in_message(self):
        """Message should include the reason."""
        result = connection_error("https://example.com", "Connection refused")
        assert "Connection refused" in result.error.message

    def test_has_suggestions(self):
        """Should include helpful suggestions."""
        result = connection_error("https://example.com", "Timeout")
        assert len(result.error.suggestions) > 0


class TestNotFoundError:
    """Tests for not_found_error factory."""

    def test_has_404_status_code(self):
        """Should include 404 status code in details."""
        result = not_found_error("https://example.com/missing")
        assert result.error.details is not None
        assert result.error.details.status_code == 404


class TestAccessDeniedError:
    """Tests for access_denied_error factory."""

    def test_default_403_status_code(self):
        """Should default to 403 status code."""
        result = access_denied_error("https://example.com/private")
        assert result.error.details is not None
        assert result.error.details.status_code == 403

    def test_custom_status_code(self):
        """Should accept custom status code."""
        result = access_denied_error("https://example.com/private", 401)
        assert result.error.details.status_code == 401


class TestInvalidUrlError:
    """Tests for invalid_url_error factory."""

    def test_includes_url_in_message(self):
        """Message should include the invalid URL."""
        result = invalid_url_error("not-a-url")
        assert "not-a-url" in result.error.message

    def test_suggests_correct_format(self):
        """Suggestions should mention correct URL format."""
        result = invalid_url_error("bad")
        suggestions_text = " ".join(result.error.suggestions)
        assert "http" in suggestions_text.lower()


class TestUnsupportedFormatError:
    """Tests for unsupported_format_error factory."""

    def test_includes_extension_in_message(self):
        """Message should include the unsupported extension."""
        result = unsupported_format_error(".xyz")
        assert ".xyz" in result.error.message

    def test_lists_supported_formats(self):
        """Suggestions should list supported formats."""
        result = unsupported_format_error(".xyz")
        suggestions_text = " ".join(result.error.suggestions)
        # Should mention at least some supported formats
        assert "pdf" in suggestions_text.lower() or "Supported" in suggestions_text

    def test_custom_supported_formats(self):
        """Should accept custom list of supported formats."""
        result = unsupported_format_error(".xyz", ["pdf", "docx"])
        suggestions_text = " ".join(result.error.suggestions)
        assert "pdf" in suggestions_text.lower()


class TestFileTooLargeError:
    """Tests for file_too_large_error factory."""

    def test_includes_sizes_in_message(self):
        """Message should include both file size and max size."""
        result = file_too_large_error(100.5, 50)
        assert "100" in result.error.message
        assert "50" in result.error.message


class TestContentEmptyError:
    """Tests for content_empty_error factory."""

    def test_suggests_js_when_not_tried(self):
        """Should suggest render_js when JS wasn't tried."""
        result = content_empty_error("https://spa.com", tried_js=False)
        suggestions_text = " ".join(result.error.suggestions)
        assert "render_js" in suggestions_text

    def test_no_js_suggestion_when_already_tried(self):
        """Should not suggest render_js when JS was already tried."""
        result = content_empty_error("https://spa.com", tried_js=True)
        suggestions_text = " ".join(result.error.suggestions)
        assert "render_js" not in suggestions_text


class TestUnknownToolError:
    """Tests for unknown_tool_error factory."""

    def test_includes_tool_name_in_message(self):
        """Message should include the unknown tool name."""
        result = unknown_tool_error("bad_tool")
        assert "bad_tool" in result.error.message

    def test_lists_available_tools(self):
        """Suggestions should list available tools."""
        result = unknown_tool_error("bad_tool")
        suggestions_text = " ".join(result.error.suggestions)
        assert "read_url" in suggestions_text
        assert "read_file" in suggestions_text


class TestConversionError:
    """Tests for conversion_error factory."""

    def test_includes_message(self):
        """Should include the error message."""
        result = conversion_error("File is corrupted")
        assert "File is corrupted" in result.error.message

    def test_has_suggestions(self):
        """Should include helpful suggestions."""
        result = conversion_error("Error")
        assert len(result.error.suggestions) > 0


class TestInvalidInputError:
    """Tests for invalid_input_error factory."""

    def test_includes_message(self):
        """Should include the error message."""
        result = invalid_input_error("Missing required field")
        assert "Missing required field" in result.error.message
