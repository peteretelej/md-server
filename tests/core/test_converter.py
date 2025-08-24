import pytest
from pathlib import Path
from unittest.mock import patch

from md_server.core.converter import DocumentConverter
from md_server.models import ConversionResult


class TestDocumentConverter:
    @pytest.fixture
    def converter(self):
        return DocumentConverter()

    def test_init_default_params(self):
        converter = DocumentConverter()
        assert converter.ocr_enabled is False
        assert converter.js_rendering is False
        assert converter.timeout == 30
        assert converter.max_file_size_mb == 50
        assert converter.extract_images is False
        assert converter.preserve_formatting is False
        assert converter.clean_markdown is True

    def test_init_custom_params(self):
        converter = DocumentConverter(
            ocr_enabled=True,
            js_rendering=True,
            timeout=60,
            max_file_size_mb=100,
            extract_images=True,
            preserve_formatting=True,
            clean_markdown=False,
        )
        assert converter.ocr_enabled is True
        assert converter.js_rendering is True
        assert converter.timeout == 60
        assert converter.max_file_size_mb == 100
        assert converter.extract_images is True
        assert converter.preserve_formatting is True
        assert converter.clean_markdown is False

    def test_browser_availability_check(self):
        converter = DocumentConverter()
        assert isinstance(converter._browser_available, bool)

    @pytest.mark.asyncio
    async def test_convert_file_success(self, converter, simple_html_file):
        result = await converter.convert_file(simple_html_file)
        assert isinstance(result, ConversionResult)
        assert result.success is True
        assert result.markdown
        assert result.metadata

    @pytest.mark.asyncio
    async def test_convert_file_nonexistent(self, converter):
        nonexistent = Path("/nonexistent/file.txt")
        with pytest.raises(FileNotFoundError):
            await converter.convert_file(nonexistent)

    @pytest.mark.asyncio
    async def test_convert_content_success(self, converter):
        content = b"<html><body><h1>Test</h1></body></html>"
        result = await converter.convert_content(content)
        assert isinstance(result, ConversionResult)
        assert result.success is True
        assert "Test" in result.markdown

    @pytest.mark.asyncio
    async def test_convert_url_success(self, converter):
        with patch(
            "md_server.core.converter.DocumentConverter._convert_url_with_markitdown"
        ) as mock_convert:
            mock_convert.return_value = "# Test Content"
            result = await converter.convert_url("https://example.com")
            assert result.success is True
            assert result.markdown == "# Test Content"

    @pytest.mark.asyncio
    async def test_convert_invalid_url(self, converter):
        with pytest.raises(ValueError):
            await converter.convert_url("not-a-url")

    @pytest.mark.asyncio
    async def test_file_size_limit_validation(self, converter, tmp_path):
        # Test file size validation in convert_file method
        large_content = b"x" * (55 * 1024 * 1024)  # 55MB > 50MB default limit
        large_file = tmp_path / "large_file.txt"
        large_file.write_bytes(large_content)

        with pytest.raises(ValueError, match="File too large"):
            await converter.convert_file(large_file)

    @pytest.mark.asyncio
    async def test_content_size_limit_validation(self, converter):
        # Test content size validation in convert_content method
        large_content = b"x" * (55 * 1024 * 1024)  # 55MB > 50MB default limit

        with pytest.raises(ValueError, match="Content too large"):
            await converter.convert_content(large_content)

    def test_browser_availability_check_no_import(self, converter):
        with patch("importlib.util.find_spec", return_value=None):
            result = converter._check_browser_availability()
            assert result is False

    def test_browser_availability_check_with_import(self, converter):
        with patch("importlib.util.find_spec") as mock_find_spec:
            mock_find_spec.return_value = True  # Mock module found
            result = converter._check_browser_availability()
            assert result is True

    def test_detect_format_pdf_magic_bytes(self, converter):
        pdf_content = b"%PDF-1.4"
        result = converter._detect_format(pdf_content)
        assert result == "application/pdf"

    def test_detect_format_html_content(self, converter):
        html_content = b"<html><body>test</body></html>"
        result = converter._detect_format(html_content)
        assert result == "text/html"

    def test_detect_format_image_png(self, converter):
        png_content = b"\x89PNG\r\n\x1a\n"
        result = converter._detect_format(png_content)
        assert result == "image/png"

    def test_detect_format_binary_with_nulls(self, converter):
        binary_content = b"some\x00binary\x00content"
        result = converter._detect_format(binary_content)
        assert result == "application/octet-stream"

    def test_detect_format_from_filename(self, converter):
        text_content = b"plain text content"
        result = converter._detect_format(text_content, "test.pdf")
        assert result == "application/pdf"

    def test_detect_format_text_fallback(self, converter):
        text_content = b"plain text content"
        result = converter._detect_format(text_content)
        assert result == "text/plain"

    @pytest.mark.asyncio
    async def test_url_conversion_with_browser_enabled(self, converter):
        converter.js_rendering = True
        converter._browser_available = True

        with patch(
            "md_server.core.converter.DocumentConverter._crawl_with_browser"
        ) as mock_crawl:
            mock_crawl.return_value = "# Crawled Content"
            result = await converter.convert_url("https://example.com")
            assert result.success is True
            assert result.markdown == "# Crawled Content"
            mock_crawl.assert_called_once_with("https://example.com")

    @pytest.mark.asyncio
    async def test_url_conversion_fallback_to_markitdown(self, converter):
        converter.js_rendering = True
        converter._browser_available = False

        with patch(
            "md_server.core.converter.DocumentConverter._convert_url_with_markitdown"
        ) as mock_convert:
            mock_convert.return_value = "# MarkItDown Content"
            result = await converter.convert_url("https://example.com")
            assert result.success is True
            assert result.markdown == "# MarkItDown Content"

    @pytest.mark.asyncio
    async def test_convert_text_with_markdown_mime(self, converter):
        text = "# Already Markdown"
        result = await converter.convert_text(text, "text/markdown")
        assert result.success is True
        assert result.markdown == "# Already Markdown"

    @pytest.mark.asyncio
    async def test_convert_text_with_html_mime(self, converter):
        text = "<h1>HTML Title</h1>"
        result = await converter.convert_text(text, "text/html")
        assert result.success is True
        assert "HTML Title" in result.markdown

    def test_clean_markdown_removes_empty_lines(self, converter):
        messy_markdown = "\n\n# Title\n\n\nContent\n\n\n"
        cleaned = converter._clean_markdown(messy_markdown)
        assert cleaned == "# Title\n\nContent"

    def test_clean_markdown_preserves_single_breaks(self, converter):
        markdown = "Line 1\n\nLine 2"
        cleaned = converter._clean_markdown(markdown)
        assert cleaned == "Line 1\n\nLine 2"

    def test_apply_options_max_length(self, converter):
        long_markdown = "x" * 100
        options = {"max_length": 10}
        result = converter._apply_options(long_markdown, options)
        assert result == "x" * 10 + "..."

    def test_apply_options_clean_markdown_disabled(self, converter):
        messy_markdown = "\n\n# Title\n\n\n"
        options = {"clean_markdown": False}
        result = converter._apply_options(messy_markdown, options)
        assert result == messy_markdown

    def test_validate_url_empty_string(self, converter):
        with pytest.raises(ValueError, match="URL must be a non-empty string"):
            converter._validate_url("")

    def test_validate_url_non_string(self, converter):
        with pytest.raises(ValueError, match="URL must be a non-empty string"):
            converter._validate_url(None)

    def test_validate_url_invalid_scheme(self, converter):
        with pytest.raises(ValueError, match="URL must start with http"):
            converter._validate_url("ftp://example.com")

    def test_create_stream_info_for_content_with_filename(self, converter):
        stream_info = converter._create_stream_info_for_content("test.pdf")
        assert stream_info.extension == ".pdf"
        assert stream_info.filename == "test.pdf"

    def test_create_stream_info_for_content_no_filename(self, converter):
        stream_info = converter._create_stream_info_for_content(None)
        assert stream_info is None

    @pytest.mark.asyncio
    async def test_image_extraction_workflow_option(self, converter):
        # Test that image extraction option is passed through
        html_content = b"<html><body><img src='test.jpg' alt='Test'/></body></html>"
        options = {"extract_images": True}

        with patch(
            "md_server.core.converter.DocumentConverter._sync_convert_content"
        ) as mock_sync:
            mock_sync.return_value = "![Test](test.jpg)\n\nContent with image"
            result = await converter.convert_content(html_content, **options)

            assert result.success is True
            assert "![Test]" in result.markdown
            mock_sync.assert_called_once_with(html_content, None, options)

    @pytest.mark.asyncio
    async def test_timeout_handling_in_url_conversion(self, converter):
        # Test timeout handling in URL conversion
        converter.timeout = 1  # Very short timeout

        with patch(
            "md_server.core.converter.DocumentConverter._sync_convert_url"
        ) as mock_sync:

            def slow_conversion(url):
                import time

                time.sleep(2)  # Longer than timeout
                return "converted content"

            mock_sync.side_effect = slow_conversion

            with pytest.raises(TimeoutError, match="URL conversion timed out"):
                await converter.convert_url("https://slow-website.com")

    def test_sync_convert_content_calls_markitdown(self, converter):
        # Test that sync convert content properly calls MarkItDown
        content = b"<html><body>Test content</body></html>"

        with patch.object(converter._markitdown, "convert_stream") as mock_convert:
            mock_result = type("Result", (), {"markdown": "# Test Content"})()
            mock_convert.return_value = mock_result

            result = converter._sync_convert_content(content, "test.html")

            assert result == "# Test Content"
            mock_convert.assert_called_once()

    def test_sync_convert_text_with_mime_type(self, converter):
        # Test text conversion with mime type
        text = "<h1>HTML Title</h1>"
        mime_type = "text/html"

        with patch.object(converter._markitdown, "convert_stream") as mock_convert:
            mock_result = type("Result", (), {"markdown": "# HTML Title"})()
            mock_convert.return_value = mock_result

            result = converter._sync_convert_text_with_mime_type(text, mime_type)

            assert result == "# HTML Title"
            mock_convert.assert_called_once()

    def test_sync_convert_url_calls_markitdown(self, converter):
        # Test URL conversion through MarkItDown
        url = "https://example.com"

        with patch.object(converter._markitdown, "convert") as mock_convert:
            mock_result = type("Result", (), {"markdown": "# Example Site"})()
            mock_convert.return_value = mock_result

            result = converter._sync_convert_url(url)

            assert result == "# Example Site"
            mock_convert.assert_called_once_with(url)

    def test_sync_convert_url_handles_exception(self, converter):
        # Test URL conversion exception handling
        url = "https://example.com"

        with patch.object(converter._markitdown, "convert") as mock_convert:
            mock_convert.side_effect = Exception("Network error")

            with pytest.raises(Exception, match="Failed to convert URL"):
                converter._sync_convert_url(url)
