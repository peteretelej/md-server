"""Tests for MCP response models."""

import pytest
from md_server.mcp.models import (
    MCPSuccessResponse,
    MCPErrorResponse,
    MCPMetadata,
    MCPError,
    MCPErrorDetails,
)


class TestMCPMetadata:
    """Tests for MCPMetadata model."""

    def test_all_fields_optional(self):
        """All metadata fields should be optional."""
        metadata = MCPMetadata()
        assert metadata.author is None
        assert metadata.description is None
        assert metadata.published is None
        assert metadata.language is None
        assert metadata.pages is None
        assert metadata.format is None
        assert metadata.ocr_applied is None

    def test_with_values(self):
        """Metadata should accept values for all fields."""
        metadata = MCPMetadata(
            author="John Doe",
            description="A test document",
            published="2024-01-15",
            language="en",
            pages=10,
            format="application/pdf",
            ocr_applied=True,
        )
        assert metadata.author == "John Doe"
        assert metadata.description == "A test document"
        assert metadata.published == "2024-01-15"
        assert metadata.language == "en"
        assert metadata.pages == 10
        assert metadata.format == "application/pdf"
        assert metadata.ocr_applied is True

    def test_serialization(self):
        """Metadata should serialize to dict correctly."""
        metadata = MCPMetadata(author="Jane", pages=5)
        data = metadata.model_dump()
        assert data["author"] == "Jane"
        assert data["pages"] == 5
        assert data["description"] is None


class TestMCPSuccessResponse:
    """Tests for MCPSuccessResponse model."""

    def test_success_is_true_by_default(self):
        """Success should be True by default."""
        response = MCPSuccessResponse(
            title="Test",
            content="# Test",
            source="test.pdf",
            word_count=1,
            metadata=MCPMetadata(),
        )
        assert response.success is True

    def test_all_required_fields(self):
        """Should require all mandatory fields."""
        with pytest.raises(Exception):
            MCPSuccessResponse()

    def test_serialization(self):
        """Should serialize to dict correctly."""
        response = MCPSuccessResponse(
            title="Test Title",
            content="# Content",
            source="https://example.com",
            word_count=100,
            metadata=MCPMetadata(author="Author"),
        )
        data = response.model_dump()
        assert data["success"] is True
        assert data["title"] == "Test Title"
        assert data["content"] == "# Content"
        assert data["source"] == "https://example.com"
        assert data["word_count"] == 100
        assert data["metadata"]["author"] == "Author"

    def test_json_output(self):
        """Should serialize to JSON correctly."""
        response = MCPSuccessResponse(
            title="T",
            content="C",
            source="S",
            word_count=1,
            metadata=MCPMetadata(),
        )
        json_str = response.model_dump_json()
        assert "true" in json_str  # success: true
        assert '"title"' in json_str
        assert '"content"' in json_str

    def test_default_metadata(self):
        """Should use empty metadata by default."""
        response = MCPSuccessResponse(
            title="T",
            content="C",
            source="S",
            word_count=1,
        )
        assert response.metadata is not None
        assert response.metadata.author is None


class TestMCPError:
    """Tests for MCPError model."""

    def test_required_fields(self):
        """Should require code and message."""
        error = MCPError(
            code="TEST_ERROR",
            message="Test error message",
            suggestions=["Fix it"],
        )
        assert error.code == "TEST_ERROR"
        assert error.message == "Test error message"
        assert "Fix it" in error.suggestions

    def test_empty_suggestions_by_default(self):
        """Suggestions should default to empty list."""
        error = MCPError(code="TEST", message="Test")
        assert error.suggestions == []

    def test_with_details(self):
        """Should accept optional details."""
        details = MCPErrorDetails(status_code=404, content_type="text/html")
        error = MCPError(
            code="NOT_FOUND",
            message="Not found",
            details=details,
        )
        assert error.details is not None
        assert error.details.status_code == 404


class TestMCPErrorResponse:
    """Tests for MCPErrorResponse model."""

    def test_success_is_false_by_default(self):
        """Success should be False by default."""
        response = MCPErrorResponse(
            error=MCPError(
                code="TEST",
                message="Test error",
                suggestions=["Fix it"],
            )
        )
        assert response.success is False

    def test_error_structure(self):
        """Should contain error with correct structure."""
        response = MCPErrorResponse(
            error=MCPError(
                code="TIMEOUT",
                message="Request timed out",
                suggestions=["Retry later"],
            )
        )
        assert response.error.code == "TIMEOUT"
        assert response.error.message == "Request timed out"
        assert "Retry later" in response.error.suggestions

    def test_json_output(self):
        """Should serialize to JSON correctly."""
        response = MCPErrorResponse(
            error=MCPError(
                code="ERROR",
                message="An error occurred",
            )
        )
        json_str = response.model_dump_json()
        assert "false" in json_str  # success: false
        assert '"code"' in json_str
        assert '"message"' in json_str
