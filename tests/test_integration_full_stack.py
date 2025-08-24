import pytest

from md_server.sdk import MDConverter, RemoteMDConverter
from md_server.sdk.exceptions import NetworkError


class TestIntegration:
    """Simple integration tests focused on coverage gaps."""

    def test_remote_fallback(self):
        """Test remote converter error handling."""
        # Test remote converter with invalid endpoint
        remote_converter = RemoteMDConverter(endpoint="http://127.0.0.1:9999")

        # Should fail gracefully
        with pytest.raises((NetworkError, ConnectionError, OSError)):
            remote_converter.convert_text_sync("test content", "text/plain")

        # Local converter should work
        local_converter = MDConverter()
        result = local_converter.convert_text_sync("test content", "text/plain")
        assert result.success
        assert "test content" in result.markdown

    def test_basic_conversion_types(self):
        """Test different input types work correctly."""
        converter = MDConverter()

        # Test different MIME types
        test_cases = [
            ("Plain text", "text/plain"),
            ("<h1>HTML</h1><p>Content</p>", "text/html"),
            ("# Markdown\nContent", "text/markdown"),
        ]

        for content, mime_type in test_cases:
            result = converter.convert_text_sync(content, mime_type)
            assert result.success
            assert len(result.markdown) > 0

    def test_remote_converter_with_server(self, test_server):
        """Test remote converter against real server."""
        remote_converter = RemoteMDConverter(endpoint=test_server)

        # Test basic conversion
        result = remote_converter.convert_text_sync("Test content", "text/plain")
        assert result.success
        assert "test content" in result.markdown.lower()

        # Test async context manager
        async def test_context_manager():
            async with RemoteMDConverter(endpoint=test_server) as client:
                result = await client.convert_text("Async test", "text/plain")
                assert result.success

        import asyncio

        asyncio.run(test_context_manager())
