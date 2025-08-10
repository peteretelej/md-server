import pytest
from unittest.mock import Mock, patch

from md_server.converter import (
    convert_text_with_mime_type,
    _sync_convert_text_with_mime_type,
)


class TestConvertTextWithMimeType:
    @pytest.mark.asyncio
    async def test_validates_mime_type(self):
        """Test MIME type validation"""
        converter = Mock()

        # Test invalid MIME type - validation happens in async wrapper
        with pytest.raises(ValueError, match="MIME type must contain"):
            await convert_text_with_mime_type(converter, "test", "invalid-mime-type")

    def test_sync_converts_any_mime_type(self):
        """Test sync function processes any MIME type (validation happens in async wrapper)"""
        converter = Mock()
        result_mock = Mock()
        result_mock.markdown = "Converted"
        converter.convert_stream.return_value = result_mock

        result = _sync_convert_text_with_mime_type(converter, "test", "text/html")

        assert result == "Converted"
        converter.convert_stream.assert_called_once()

    def test_converts_html_text(self):
        """Test HTML text conversion"""
        converter = Mock()
        result_mock = Mock()
        result_mock.markdown = "# Test\n\nConverted content"
        converter.convert_stream.return_value = result_mock

        html_text = "<h1>Test</h1><p>Some content</p>"
        result = _sync_convert_text_with_mime_type(converter, html_text, "text/html")

        assert result == "# Test\n\nConverted content"

        # Verify converter called with correct parameters
        converter.convert_stream.assert_called_once()
        args, kwargs = converter.convert_stream.call_args

        # Check that stream_info has correct mimetype
        stream_info = kwargs["stream_info"]
        assert stream_info.mimetype == "text/html"

        # The stream is closed after use, but we know it was created from our text

    def test_applies_clean_markdown_option(self):
        """Test clean_markdown option is applied"""
        converter = Mock()
        result_mock = Mock()
        result_mock.markdown = "# Test\n\n\n\nSome content\n\n\n"
        converter.convert_stream.return_value = result_mock

        result = _sync_convert_text_with_mime_type(
            converter, "<h1>Test</h1>", "text/html", {"clean_markdown": True}
        )

        # Should be cleaned (trailing whitespace removed)
        assert result == "# Test\n\nSome content"

    def test_applies_max_length_option(self):
        """Test max_length option truncates output"""
        converter = Mock()
        result_mock = Mock()
        result_mock.markdown = "This is a very long markdown content"
        converter.convert_stream.return_value = result_mock

        result = _sync_convert_text_with_mime_type(
            converter, "<p>Long content</p>", "text/html", {"max_length": 10}
        )

        assert result == "This is a ..."
        assert len(result) == 13  # 10 + "..."

    def test_handles_various_mime_types(self):
        """Test various MIME types are handled"""
        converter = Mock()
        result_mock = Mock()
        result_mock.markdown = "Converted"
        converter.convert_stream.return_value = result_mock

        mime_types = ["text/html", "application/xml", "text/xml", "application/json"]

        for mime_type in mime_types:
            result = _sync_convert_text_with_mime_type(
                converter, "test content", mime_type
            )

            assert result == "Converted"

    @pytest.mark.asyncio
    async def test_async_wrapper(self):
        """Test async wrapper function"""
        with patch(
            "md_server.converter.MimeTypeValidator.validate_mime_type"
        ) as mock_validate:
            mock_validate.return_value = "text/html"

            with patch(
                "md_server.converter._sync_convert_text_with_mime_type"
            ) as mock_sync:
                mock_sync.return_value = "Converted content"

                converter = Mock()
                result = await convert_text_with_mime_type(
                    converter, "<h1>Test</h1>", "text/html"
                )

                assert result == "Converted content"
                mock_validate.assert_called_once_with("text/html")
                mock_sync.assert_called_once_with(
                    converter, "<h1>Test</h1>", "text/html", None
                )

    @pytest.mark.asyncio
    async def test_async_markdown_passthrough(self):
        """Test markdown text passes through without conversion"""
        with patch(
            "md_server.converter.MimeTypeValidator.validate_mime_type"
        ) as mock_validate:
            mock_validate.return_value = "text/markdown"

            converter = Mock()
            text = "# Test\n\nMarkdown content"

            result = await convert_text_with_mime_type(converter, text, "text/markdown")

            assert result == text
