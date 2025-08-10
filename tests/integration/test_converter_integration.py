import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch

from md_server.converter import (
    UrlConverter,
    convert_content,
    create_converter_with_options,
    validate_url,
    _clean_markdown,
    _sync_convert_content,
)
from md_server.core.config import Settings
from md_server.security import URLValidator


class TestUrlConverter:
    @pytest.fixture
    def mock_settings(self):
        settings = Mock(spec=Settings)
        settings.crawl4ai_js_rendering = True
        settings.crawl4ai_timeout = 30
        settings.crawl4ai_user_agent = "TestAgent/1.0"
        settings.url_fetch_timeout = 60
        settings.http_proxy = None
        settings.debug = False
        return settings

    @pytest.fixture
    def mock_markitdown(self):
        mock = Mock()
        mock.convert.return_value = Mock(markdown="# MarkItDown Result")
        return mock

    @pytest.fixture
    def url_converter(self, mock_settings, mock_markitdown):
        return UrlConverter(
            mock_settings, browser_available=True, markitdown_instance=mock_markitdown
        )

    @pytest.fixture
    def url_converter_no_browser(self, mock_settings, mock_markitdown):
        return UrlConverter(
            mock_settings, browser_available=False, markitdown_instance=mock_markitdown
        )

    @patch("md_server.converter.validate_url")
    @patch("md_server.converter.AsyncWebCrawler")
    async def test_convert_url_with_browser_success(
        self, mock_crawler_class, mock_validate, url_converter
    ):
        mock_validate.return_value = "https://example.com"

        # Mock the crawler and its result
        mock_crawler = AsyncMock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.markdown = "# Crawled Content"
        mock_result.error_message = None
        mock_crawler.arun.return_value = mock_result
        mock_crawler.__aenter__.return_value = mock_crawler
        mock_crawler.__aexit__.return_value = None
        mock_crawler_class.return_value = mock_crawler

        result = await url_converter.convert_url("https://example.com", enable_js=True)

        assert result == "# Crawled Content"
        mock_validate.assert_called_once_with("https://example.com")
        mock_crawler.arun.assert_called_once()

    @patch("md_server.converter.validate_url")
    @patch("md_server.converter.AsyncWebCrawler")
    async def test_convert_url_with_browser_failure(
        self, mock_crawler_class, mock_validate, url_converter
    ):
        mock_validate.return_value = "https://example.com"

        mock_crawler = AsyncMock()
        mock_result = Mock()
        mock_result.success = False
        mock_result.error_message = "Connection failed"
        mock_crawler.arun.return_value = mock_result
        mock_crawler.__aenter__.return_value = mock_crawler
        mock_crawler.__aexit__.return_value = None
        mock_crawler_class.return_value = mock_crawler

        with pytest.raises(ValueError, match="Failed to crawl"):
            await url_converter.convert_url("https://example.com")

    @patch("md_server.converter.validate_url")
    @patch("md_server.converter.AsyncWebCrawler")
    async def test_convert_url_with_browser_exception(
        self, mock_crawler_class, mock_validate, url_converter
    ):
        mock_validate.return_value = "https://example.com"

        mock_crawler_class.side_effect = Exception("Browser not available")

        with pytest.raises(ValueError, match="Failed to convert URL with browser"):
            await url_converter.convert_url("https://example.com")

    @patch("md_server.converter.validate_url")
    async def test_convert_url_without_browser_success(
        self, mock_validate, url_converter_no_browser
    ):
        mock_validate.return_value = "https://example.com"

        result = await url_converter_no_browser.convert_url("https://example.com")

        assert result == "# MarkItDown Result"
        mock_validate.assert_called_once_with("https://example.com")
        url_converter_no_browser.markitdown_instance.convert.assert_called_once_with(
            "https://example.com"
        )

    @patch("md_server.converter.validate_url")
    async def test_convert_url_without_browser_failure(
        self, mock_validate, url_converter_no_browser
    ):
        mock_validate.return_value = "https://example.com"
        url_converter_no_browser.markitdown_instance.convert.side_effect = Exception(
            "Connection failed"
        )

        with pytest.raises(ValueError, match="Failed to convert URL"):
            await url_converter_no_browser.convert_url("https://example.com")

    async def test_convert_url_js_rendering_default(self, url_converter, mock_settings):
        mock_settings.crawl4ai_js_rendering = False

        with (
            patch("md_server.converter.validate_url"),
            patch("md_server.converter.AsyncWebCrawler") as mock_crawler_class,
        ):
            mock_crawler = AsyncMock()
            mock_result = Mock(success=True, markdown="# Content")
            mock_crawler.arun.return_value = mock_result
            mock_crawler.__aenter__.return_value = mock_crawler
            mock_crawler.__aexit__.return_value = None
            mock_crawler_class.return_value = mock_crawler

            await url_converter.convert_url("https://example.com")
            # Should use settings default (False) when enable_js not specified

    async def test_convert_url_js_rendering_override(self, url_converter):
        with (
            patch("md_server.converter.validate_url"),
            patch("md_server.converter.AsyncWebCrawler") as mock_crawler_class,
        ):
            mock_crawler = AsyncMock()
            mock_result = Mock(success=True, markdown="# Content")
            mock_crawler.arun.return_value = mock_result
            mock_crawler.__aenter__.return_value = mock_crawler
            mock_crawler.__aexit__.return_value = None
            mock_crawler_class.return_value = mock_crawler

            await url_converter.convert_url("https://example.com", enable_js=False)
            # Should use override value (False) instead of settings

    def test_convert_url_sync_markitdown_success(self, url_converter_no_browser):
        result = url_converter_no_browser._sync_convert_url_with_markitdown(
            "https://example.com"
        )

        assert result == "# MarkItDown Result"
        url_converter_no_browser.markitdown_instance.convert.assert_called_once_with(
            "https://example.com"
        )

    def test_convert_url_sync_markitdown_failure(self, url_converter_no_browser):
        url_converter_no_browser.markitdown_instance.convert.side_effect = Exception(
            "Network error"
        )

        with pytest.raises(ValueError, match="Failed to convert URL"):
            url_converter_no_browser._sync_convert_url_with_markitdown(
                "https://example.com"
            )


class TestContentConversion:
    @pytest.fixture
    def mock_converter(self):
        mock = Mock()
        mock_result = Mock(markdown="# Converted Content")
        mock.convert_stream.return_value = mock_result
        return mock

    async def test_convert_content_basic(self, mock_converter):
        content = b"test content"
        result = await convert_content(mock_converter, content)

        assert result == "# Converted Content"
        mock_converter.convert_stream.assert_called_once()

    async def test_convert_content_with_filename(self, mock_converter):
        content = b"test content"
        filename = "test.pdf"

        result = await convert_content(mock_converter, content, filename=filename)

        assert result == "# Converted Content"
        args, kwargs = mock_converter.convert_stream.call_args
        assert "stream_info" in kwargs
        assert kwargs["stream_info"].filename == filename
        assert kwargs["stream_info"].extension == ".pdf"

    async def test_convert_content_with_options_clean_markdown(self, mock_converter):
        content = b"test content"
        options = {"clean_markdown": True}
        mock_converter.convert_stream.return_value = Mock(
            markdown="  \n\n  # Title  \n\n  \n  Content  \n\n  "
        )

        result = await convert_content(mock_converter, content, options=options)

        assert result == "# Title\n\nContent"

    async def test_convert_content_with_options_max_length(self, mock_converter):
        content = b"test content"
        options = {"max_length": 10}
        mock_converter.convert_stream.return_value = Mock(
            markdown="This is a very long content that should be truncated"
        )

        result = await convert_content(mock_converter, content, options=options)

        assert result == "This is a ..."
        assert len(result) == 13  # 10 + "..."

    def test_sync_convert_content_basic(self, mock_converter):
        content = b"test content"

        result = _sync_convert_content(mock_converter, content)

        assert result == "# Converted Content"
        mock_converter.convert_stream.assert_called_once()

    def test_sync_convert_content_with_stream_info(self, mock_converter):
        content = b"test content"
        filename = "document.docx"

        result = _sync_convert_content(mock_converter, content, filename=filename)

        assert result == "# Converted Content"
        args, kwargs = mock_converter.convert_stream.call_args
        stream_info = kwargs["stream_info"]
        assert stream_info.filename == filename
        assert stream_info.extension == ".docx"


class TestUtilityFunctions:
    def test_validate_url_success(self):
        with patch.object(
            URLValidator, "validate_url", return_value="https://example.com"
        ) as mock_validate:
            result = validate_url("https://example.com")
            assert result == "https://example.com"
            mock_validate.assert_called_once_with("https://example.com")

    def test_validate_url_failure(self):
        with patch.object(
            URLValidator, "validate_url", side_effect=ValueError("Invalid URL")
        ):
            with pytest.raises(ValueError, match="Invalid URL"):
                validate_url("invalid-url")

    def test_create_converter_with_options_no_options(self):
        base_converter = Mock()
        result = create_converter_with_options(base_converter)
        assert result is base_converter

    def test_create_converter_with_options_with_options(self):
        base_converter = Mock()
        options = {"some_option": "value"}
        result = create_converter_with_options(base_converter, options)
        # Currently just returns base converter, but tests the interface
        assert result is base_converter

    def test_clean_markdown_basic_cleanup(self):
        markdown = "  \n\n  # Title  \n\n  \n  Content  \n\n  "
        result = _clean_markdown(markdown)
        assert result == "# Title\n\nContent"

    def test_clean_markdown_empty_input(self):
        assert _clean_markdown("") == ""
        assert _clean_markdown(None) is None

    def test_clean_markdown_single_line(self):
        markdown = "  Single line content  "
        result = _clean_markdown(markdown)
        assert result == "Single line content"

    def test_clean_markdown_multiple_empty_lines(self):
        markdown = "Line 1\n\n\n\nLine 2\n\n\n"
        result = _clean_markdown(markdown)
        assert result == "Line 1\n\nLine 2"

    def test_clean_markdown_preserves_single_empty_lines(self):
        markdown = "# Title\n\nParagraph 1\n\nParagraph 2"
        result = _clean_markdown(markdown)
        assert result == "# Title\n\nParagraph 1\n\nParagraph 2"


class TestConverterIntegration:
    async def test_full_url_conversion_flow_with_browser(self, mock_http_server):
        settings = Settings()
        mock_markitdown = Mock()
        converter = UrlConverter(
            settings, browser_available=True, markitdown_instance=mock_markitdown
        )

        with patch("md_server.converter.AsyncWebCrawler") as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_result = Mock(success=True, markdown="# Server Content")
            mock_crawler.arun.return_value = mock_result
            mock_crawler.__aenter__.return_value = mock_crawler
            mock_crawler.__aexit__.return_value = None
            mock_crawler_class.return_value = mock_crawler

            result = await converter.convert_url(
                f"http://localhost:{mock_http_server.port}/test.html"
            )
            assert result == "# Server Content"

    async def test_full_url_conversion_flow_without_browser(self, mock_http_server):
        settings = Settings()
        mock_markitdown = Mock()
        mock_markitdown.convert.return_value = Mock(markdown="# Fallback Content")
        converter = UrlConverter(
            settings, browser_available=False, markitdown_instance=mock_markitdown
        )

        result = await converter.convert_url(
            f"http://localhost:{mock_http_server.port}/test.html"
        )
        assert result == "# Fallback Content"

    async def test_content_conversion_with_real_data(self, sample_files):
        mock_converter = Mock()
        mock_converter.convert_stream.return_value = Mock(
            markdown="# Real File Content"
        )

        with open(sample_files["json"], "rb") as f:
            content = f.read()

        result = await convert_content(mock_converter, content, filename="test.json")
        assert result == "# Real File Content"

    def test_browser_config_construction(self, mock_settings, mock_markitdown):
        mock_settings.http_proxy = "http://proxy:8080"
        mock_settings.crawl4ai_user_agent = "Custom Agent"
        mock_settings.debug = True

        converter = UrlConverter(
            mock_settings, browser_available=True, markitdown_instance=mock_markitdown
        )

        with (
            patch("md_server.converter.BrowserConfig") as mock_browser_config,
            patch("md_server.converter.CrawlerRunConfig"),
            patch("md_server.converter.AsyncWebCrawler") as mock_crawler_class,
        ):
            mock_crawler = AsyncMock()
            mock_result = Mock(success=True, markdown="# Content")
            mock_crawler.arun.return_value = mock_result
            mock_crawler.__aenter__.return_value = mock_crawler
            mock_crawler.__aexit__.return_value = None
            mock_crawler_class.return_value = mock_crawler

            asyncio.run(converter._crawl_with_browser("https://example.com", True))

            # Verify browser config was created with correct parameters
            mock_browser_config.assert_called_once()
            call_kwargs = mock_browser_config.call_args[1]
            assert call_kwargs["browser_type"] == "chromium"
            assert call_kwargs["headless"] is True
            assert call_kwargs["proxy"] == "http://proxy:8080"
            assert call_kwargs["user_agent"] == "Custom Agent"
            assert call_kwargs["verbose"] is True
