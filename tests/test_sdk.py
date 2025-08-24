import pytest
from pathlib import Path
from unittest.mock import patch

from md_server.sdk import MDConverter
from md_server.models import ConversionResult


class TestMDConverter:
    @pytest.fixture
    def converter(self):
        return MDConverter()

    def test_init_default_params(self):
        converter = MDConverter()
        assert converter._converter is not None

    def test_init_custom_params(self):
        converter = MDConverter(ocr_enabled=True, js_rendering=True, timeout=60)
        assert converter._converter.ocr_enabled is True
        assert converter._converter.js_rendering is True
        assert converter._converter.timeout == 60

    @pytest.mark.asyncio
    async def test_convert_file_async(self, converter, simple_html_file):
        if simple_html_file.exists():
            result = await converter.convert_file(simple_html_file)
            assert isinstance(result, ConversionResult)
            assert result.success is True
            assert result.markdown

    def test_convert_file_sync(self, converter, simple_html_file):
        if simple_html_file.exists():
            result = converter.convert_file_sync(simple_html_file)
            assert isinstance(result, ConversionResult)
            assert result.success is True
            assert result.markdown

    @pytest.mark.asyncio
    async def test_convert_file_nonexistent(self, converter):
        nonexistent = Path("/nonexistent/file.txt")
        with pytest.raises(FileNotFoundError):
            await converter.convert_file(nonexistent)

    @pytest.mark.asyncio
    async def test_convert_content_async(self, converter):
        content = b"<html><body><h1>Test Content</h1></body></html>"
        result = await converter.convert_content(content)
        assert isinstance(result, ConversionResult)
        assert result.success is True
        assert "Test Content" in result.markdown

    def test_convert_content_sync(self, converter):
        content = b"<html><body><h1>Test Content</h1></body></html>"
        result = converter.convert_content_sync(content)
        assert isinstance(result, ConversionResult)
        assert result.success is True
        assert "Test Content" in result.markdown

    @pytest.mark.asyncio
    async def test_convert_content_empty(self, converter):
        from markitdown._exceptions import UnsupportedFormatException

        with pytest.raises(UnsupportedFormatException):
            await converter.convert_content(b"")

    @pytest.mark.asyncio
    async def test_convert_url_async(self, converter):
        from md_server.models import ConversionMetadata

        with patch.object(converter._converter, "convert_url") as mock_convert:
            metadata = ConversionMetadata(
                source_type="url",
                source_size=100,
                markdown_size=50,
                conversion_time_ms=100,
                detected_format="text/html",
            )
            mock_convert.return_value = ConversionResult(
                success=True, markdown="# Test URL", metadata=metadata
            )
            result = await converter.convert_url("https://example.com")
            assert result.success is True
            assert result.markdown == "# Test URL"

    def test_convert_url_sync(self, converter):
        from md_server.models import ConversionMetadata

        with patch.object(converter._converter, "convert_url") as mock_convert:
            metadata = ConversionMetadata(
                source_type="url",
                source_size=100,
                markdown_size=50,
                conversion_time_ms=100,
                detected_format="text/html",
            )
            mock_convert.return_value = ConversionResult(
                success=True, markdown="# Test URL", metadata=metadata
            )
            result = converter.convert_url_sync("https://example.com")
            assert result.success is True
            assert result.markdown == "# Test URL"

    @pytest.mark.asyncio
    async def test_convert_url_invalid(self, converter):
        with pytest.raises(ValueError):
            await converter.convert_url("not-a-url")


class TestMDConverterContextManager:
    @pytest.mark.asyncio
    async def test_async_context_manager(self, simple_html_file):
        if simple_html_file.exists():
            async with MDConverter() as converter:
                result = await converter.convert_file(simple_html_file)
                assert result.success is True

    def test_sync_context_manager(self, simple_html_file):
        if simple_html_file.exists():
            with MDConverter() as converter:
                result = converter.convert_file_sync(simple_html_file)
                assert result.success is True


class TestMDConverterEdgeCases:
    """Test edge cases and model validation"""

    def test_model_validation_edge_cases(self):
        """Test ConversionResult model validation edge cases"""
        from md_server.models import ConversionResult

        from md_server.models import ConversionMetadata

        # Test with success result
        metadata = ConversionMetadata(
            source_type="html",
            source_size=100,
            markdown_size=50,
            conversion_time_ms=100,
            detected_format="text/html",
        )
        result = ConversionResult(success=True, markdown="", metadata=metadata)
        assert result.success is True
        assert result.markdown == ""

        # Test with minimal metadata
        minimal_metadata = ConversionMetadata(
            source_type="text",
            source_size=0,
            markdown_size=0,
            conversion_time_ms=0,
            detected_format="text/plain",
        )
        minimal_result = ConversionResult(
            success=True, markdown="test", metadata=minimal_metadata
        )
        assert minimal_result.success is True
        assert minimal_result.markdown == "test"

    def test_converter_parameter_validation(self):
        """Test converter parameter validation"""
        # Test with invalid timeout
        converter = MDConverter(timeout=-1)
        assert (
            converter._converter.timeout == -1
        )  # Should accept but may be handled by underlying converter

        # Test with extreme values
        converter = MDConverter(timeout=999999)
        assert converter._converter.timeout == 999999

    @pytest.mark.asyncio
    async def test_convert_content_type_edge_cases(self):
        """Test content type edge cases"""
        converter = MDConverter()

        # Test with binary content
        binary_content = b"\x00\x01\x02\x03"
        result = await converter.convert_content(binary_content)
        # Should handle gracefully
        assert isinstance(result, ConversionResult)

        # Test with very large content
        large_content = ("<html><body>" + "a" * 10000 + "</body></html>").encode()
        result = await converter.convert_content(large_content)
        assert isinstance(result, ConversionResult)


class TestMDConverterUserWorkflows:
    def test_batch_file_conversion(self, test_data_dir):
        """Test converting multiple files in batch"""
        converter = MDConverter()

        # Find available test files
        test_files = [
            test_data_dir / "simple.html",
            test_data_dir / "test.pdf",
            test_data_dir / "test.docx",
        ]

        results = []
        for file_path in test_files:
            if file_path.exists():
                result = converter.convert_file_sync(file_path)
                results.append(result)

        # Should have at least one successful conversion
        assert len(results) > 0
        successful_results = [r for r in results if r.success]
        assert len(successful_results) > 0

    def test_mixed_content_types(self):
        """Test converting different content types"""
        converter = MDConverter()

        test_contents = [
            b"<html><body><h1>HTML Content</h1></body></html>",
            b'{"title": "JSON Content", "type": "test"}',
            b"Plain text content for testing",
        ]

        results = []
        for content in test_contents:
            result = converter.convert_content_sync(content)
            results.append(result)

        # All should succeed
        assert all(r.success for r in results)
        assert all(r.markdown for r in results)


class TestMDConverterNetworkErrors:
    """Test network timeout and error handling"""

    @pytest.fixture
    def converter(self):
        return MDConverter(timeout=1)  # Short timeout for testing

    @pytest.mark.asyncio
    async def test_network_timeout_handling(self, converter):
        """Test handling of network timeouts"""
        with patch.object(converter._converter, "convert_url") as mock_convert:
            from asyncio import TimeoutError

            mock_convert.side_effect = TimeoutError("Network timeout")

            with pytest.raises(TimeoutError):
                await converter.convert_url("https://slow-server.example.com")

    @pytest.mark.asyncio
    async def test_invalid_response_handling(self, converter):
        """Test handling of invalid server responses"""
        with patch.object(converter._converter, "convert_content") as mock_convert:
            # Simulate invalid response from underlying converter
            mock_convert.side_effect = ValueError("Invalid response format")

            with pytest.raises(ValueError):
                await converter.convert_content(b"<html><body>Test</body></html>")

    def test_sync_wrapper_exceptions(self, converter):
        """Test exception handling in sync wrappers"""
        with patch.object(converter._converter, "convert_content") as mock_convert:
            mock_convert.side_effect = RuntimeError("Sync wrapper error")

            with pytest.raises(RuntimeError):
                converter.convert_content_sync(b"<html><body>Test</body></html>")
