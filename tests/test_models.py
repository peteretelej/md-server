"""Tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from md_server.models import ConvertRequest, ConversionOptions


class TestConvertRequest:
    """Tests for ConvertRequest model validation."""

    @pytest.mark.parametrize(
        "kwargs,expected_field",
        [
            ({"url": "https://example.com"}, "url"),
            ({"content": "dGVzdCBjb250ZW50"}, "content"),
            ({"text": "<h1>Hello</h1>"}, "text"),
        ],
        ids=["url", "content", "text"],
    )
    def test_valid_single_input(self, kwargs, expected_field):
        """Should accept exactly one input field."""
        request = ConvertRequest(**kwargs)
        assert getattr(request, expected_field) is not None
        # Other fields should be None
        for field in ["url", "content", "text"]:
            if field != expected_field:
                assert getattr(request, field) is None

    def test_no_input_raises_error(self):
        """Should raise error when no input is provided."""
        with pytest.raises(
            ValidationError, match="url, content, or text must be provided"
        ):
            ConvertRequest()

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"url": "https://example.com", "text": "<h1>Test</h1>"},
            {"url": "https://example.com", "content": "ZGF0YQ=="},
            {"content": "ZGF0YQ==", "text": "text"},
            {"url": "https://example.com", "content": "ZGF0YQ==", "text": "text"},
        ],
        ids=["url+text", "url+content", "content+text", "all_three"],
    )
    def test_multiple_inputs_raises_error(self, kwargs):
        """Should raise error when multiple inputs are provided."""
        with pytest.raises(ValidationError, match="Only one of url, content, or text"):
            ConvertRequest(**kwargs)

    def test_optional_parameters(self):
        """Should accept optional parameters."""
        request = ConvertRequest(
            url="https://example.com",
            mime_type="text/html",
            options=ConversionOptions(max_length=1000),
        )
        assert request.url == "https://example.com"
        assert request.mime_type == "text/html"
        assert request.options.max_length == 1000
