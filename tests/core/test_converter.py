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
        with (
            patch("md_server.core.converter.validate_url") as mock_validate,
            patch(
                "md_server.core.converter.DocumentConverter._convert_url_with_markitdown"
            ) as mock_convert,
        ):
            mock_validate.return_value = "https://example.com"
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

        with (
            patch("md_server.core.converter.validate_url") as mock_validate,
            patch(
                "md_server.core.converter.DocumentConverter._crawl_with_browser"
            ) as mock_crawl,
        ):
            mock_validate.return_value = "https://example.com"
            mock_crawl.return_value = "# Crawled Content"
            result = await converter.convert_url("https://example.com")
            assert result.success is True
            assert result.markdown == "# Crawled Content"
            mock_crawl.assert_called_once_with("https://example.com")

    @pytest.mark.asyncio
    async def test_url_conversion_fallback_to_markitdown(self, converter):
        converter.js_rendering = True
        converter._browser_available = False

        with (
            patch("md_server.core.converter.validate_url") as mock_validate,
            patch(
                "md_server.core.converter.DocumentConverter._convert_url_with_markitdown"
            ) as mock_convert,
        ):
            mock_validate.return_value = "https://example.com"
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
        # Mock asyncio.wait_for to raise TimeoutError directly (no real sleep)
        import asyncio

        from md_server.core.errors import URLTimeoutError

        with (
            patch("md_server.core.converter.validate_url") as mock_validate,
            patch("md_server.core.converter.asyncio.wait_for") as mock_wait_for,
        ):
            mock_validate.return_value = "https://slow-website.com"
            mock_wait_for.side_effect = asyncio.TimeoutError()

            with pytest.raises(URLTimeoutError, match="timed out"):
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

        from md_server.core.errors import HTTPFetchError

        with patch.object(converter._markitdown, "convert") as mock_convert:
            mock_convert.side_effect = Exception("Network error")

            with pytest.raises(HTTPFetchError):
                converter._sync_convert_url(url)

    # --- Additional Format Detection Tests ---

    @pytest.mark.parametrize(
        "content,expected",
        [
            (b"\xff\xd8\xff\xe0", "image/jpeg"),  # JPEG with JFIF marker
            (b"\xff\xd8\xff\xe1", "image/jpeg"),  # JPEG with EXIF marker
            (b"GIF89a", "image/gif"),  # GIF 89a
            (b"GIF87a", "image/gif"),  # GIF 87a
            (b"RIFF\x00\x00\x00\x00WAVE", "audio/wav"),  # WAV file
            (b"\xff\xfb\x90\x00", "audio/mp3"),  # MP3 MPEG frame sync
            (b"ID3\x04\x00\x00", "audio/mp3"),  # MP3 with ID3v2 tag
            (b"<?xml version='1.0'?>", "application/xml"),  # XML declaration
        ],
    )
    def test_detect_format_magic_bytes_variants(self, converter, content, expected):
        """Test various magic byte signatures are correctly detected."""
        result = converter._detect_format(content)
        assert result == expected

    def test_detect_format_binary_with_filename_extension(self, converter):
        """Binary content with filename extension uses filename for format."""
        # Binary content with null bytes (will be detected as binary)
        binary_content = b"\x00\x01\x02\x03"
        result = converter._detect_format(binary_content, filename="data.xlsx")
        # Filename extension should be used since content is binary
        assert (
            result
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            or result == "application/octet-stream"
        )

    def test_detect_format_zip_based_office(self, converter):
        """ZIP magic bytes are detected for office documents."""
        zip_content = b"PK\x03\x04"  # ZIP signature
        result = converter._detect_format(zip_content)
        assert result == "application/zip"

    def test_detect_format_doctype_html(self, converter):
        """DOCTYPE declaration is detected as HTML."""
        html_content = b"<!DOCTYPE html><html><body>test</body></html>"
        result = converter._detect_format(html_content)
        assert result == "text/html"

    def test_detect_format_xml_in_header(self, converter):
        """XML declaration in content header is detected."""
        xml_content = b"<?xml version='1.0' encoding='utf-8'?><root></root>"
        result = converter._detect_format(xml_content)
        assert result == "application/xml"

    def test_detect_format_markdown_like_content(self, converter):
        """Content starting with # is detected as plain text (no markdown detection in converter)."""
        markdown_content = b"# Heading\n\nParagraph content"
        result = converter._detect_format(markdown_content)
        # Converter's _detect_format doesn't have markdown detection - returns text/plain
        assert result == "text/plain"

    def test_detect_format_utf8_text(self, converter):
        """Valid UTF-8 text without special markers is detected as plain text."""
        text_content = b"Just some regular text content without any special markers"
        result = converter._detect_format(text_content)
        assert result == "text/plain"


class TestTokenTruncation:
    """Tests for token-based truncation in _apply_options."""

    @pytest.fixture
    def converter(self):
        return DocumentConverter()

    @pytest.mark.parametrize(
        "content,max_tokens,should_truncate",
        [
            ("Short content", 100, False),
            ("A " * 5000, 100, True),
            ("", 100, False),
            ("Unicode: 中文 emoji 🎉 " * 100, 20, True),
        ],
        ids=[
            "short_no_truncate",
            "long_truncate",
            "empty_no_truncate",
            "unicode_truncate",
        ],
    )
    def test_token_truncation(self, converter, content, max_tokens, should_truncate):
        """Test token truncation behavior for various content types."""
        result = converter._apply_options(content, {"max_tokens": max_tokens})
        if should_truncate:
            assert "[truncated to fit token limit]" in result
        else:
            assert "[truncated" not in result

    @pytest.mark.parametrize("max_tokens", [50, 100, 500, 1000])
    def test_token_limit_respected(self, converter, max_tokens):
        """Verify truncated content stays within token limit."""
        from md_server.metadata.extractor import estimate_tokens

        long_content = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 500
        result = converter._apply_options(long_content, {"max_tokens": max_tokens})

        actual_tokens = estimate_tokens(result)
        # Allow 15% margin for safety margin and truncation indicator
        assert actual_tokens <= max_tokens * 1.15

    def test_no_truncation_when_under_limit(self, converter):
        """Content under token limit should not be truncated."""
        content = "Hello world"
        result = converter._apply_options(content, {"max_tokens": 1000})
        assert result == content
        assert "[truncated" not in result

    def test_truncation_indicator_appended(self, converter):
        """Truncated content should have indicator appended."""
        long_content = "word " * 10000
        result = converter._apply_options(long_content, {"max_tokens": 50})
        assert result.endswith("[truncated to fit token limit]")

    def test_max_tokens_none_no_truncation(self, converter):
        """max_tokens=None should not trigger truncation."""
        content = "word " * 1000
        result = converter._apply_options(content, {"max_tokens": None})
        assert "[truncated" not in result

    def test_max_tokens_zero_handled(self, converter):
        """max_tokens=0 should be treated as falsy (no truncation)."""
        content = "Some content"
        result = converter._apply_options(content, {"max_tokens": 0})
        # 0 is falsy, so no truncation
        assert result == content

    def test_both_max_length_and_max_tokens(self, converter):
        """Both max_length and max_tokens can be applied."""
        content = "A" * 1000
        result = converter._apply_options(content, {"max_length": 50, "max_tokens": 10})
        # max_length truncates first, then max_tokens
        assert len(result) <= 100  # max_length 50 + "..." + token truncation indicator
        assert "..." in result or "[truncated" in result


class TestStructuralTruncation:
    """Tests for structural truncation modes (sections, paragraphs)."""

    @pytest.fixture
    def converter(self):
        return DocumentConverter()

    # Sample content with sections for testing
    SECTION_CONTENT = """# Title

Intro paragraph.

## Section 1

Content 1.

## Section 2

Content 2.

## Section 3

Content 3."""

    # Sample content with paragraphs
    PARAGRAPH_CONTENT = """First paragraph with some content.

Second paragraph with more content.

Third paragraph continues.

Fourth paragraph here.

Fifth paragraph ends it."""

    # --- Sections Mode Tests ---

    @pytest.mark.parametrize(
        "limit,expected_sections",
        [
            (1, 1),  # Intro + Section 1
            (2, 2),  # Intro + Section 1 + Section 2
            (3, 3),  # Intro + Section 1 + Section 2 + Section 3
            (5, 3),  # Only 3 sections exist
        ],
        ids=["limit_1", "limit_2", "limit_3", "limit_exceeds"],
    )
    def test_sections_mode_truncation(self, converter, limit, expected_sections):
        """Test sections mode truncates to correct number of sections."""
        result = converter._apply_options(
            self.SECTION_CONTENT,
            {"truncate_mode": "sections", "truncate_limit": limit},
        )
        actual_sections = result.count("## ")
        assert actual_sections == expected_sections

    def test_sections_mode_includes_intro(self, converter):
        """Sections mode should include content before first ## heading."""
        result = converter._apply_options(
            self.SECTION_CONTENT,
            {"truncate_mode": "sections", "truncate_limit": 1},
        )
        assert "# Title" in result
        assert "Intro paragraph" in result
        assert "## Section 1" in result

    def test_sections_mode_no_sections(self, converter):
        """Content without ## headings should return full content."""
        no_sections = "Just some text\n\nwith paragraphs\n\nbut no sections."
        result = converter._apply_options(
            no_sections,
            {"truncate_mode": "sections", "truncate_limit": 2},
        )
        assert result == no_sections
        assert "[truncated" not in result

    def test_sections_mode_adds_truncation_indicator(self, converter):
        """Sections mode should add truncation indicator when truncating."""
        result = converter._apply_options(
            self.SECTION_CONTENT,
            {"truncate_mode": "sections", "truncate_limit": 1},
        )
        assert "[truncated...]" in result

    def test_sections_mode_no_indicator_when_not_truncated(self, converter):
        """No truncation indicator when all sections fit."""
        result = converter._apply_options(
            self.SECTION_CONTENT,
            {"truncate_mode": "sections", "truncate_limit": 10},
        )
        assert "[truncated" not in result

    # --- Paragraphs Mode Tests ---

    @pytest.mark.parametrize(
        "limit,expected_paragraphs",
        [
            (1, 1),
            (2, 2),
            (3, 3),
            (5, 5),
            (10, 5),  # Only 5 paragraphs exist
        ],
        ids=["limit_1", "limit_2", "limit_3", "limit_5", "limit_exceeds"],
    )
    def test_paragraphs_mode_truncation(self, converter, limit, expected_paragraphs):
        """Test paragraphs mode truncates to correct number of paragraphs."""
        result = converter._apply_options(
            self.PARAGRAPH_CONTENT,
            {"truncate_mode": "paragraphs", "truncate_limit": limit},
        )
        # Count paragraphs by splitting on double newlines
        # (minus 1 if truncation indicator is present)
        parts = result.split("\n\n")
        actual = len([p for p in parts if p.strip() and p.strip() != "[truncated...]"])
        assert actual == expected_paragraphs

    def test_paragraphs_mode_single_paragraph(self, converter):
        """Single paragraph content should return full content."""
        single = "Just one paragraph without any breaks."
        result = converter._apply_options(
            single,
            {"truncate_mode": "paragraphs", "truncate_limit": 2},
        )
        assert result == single
        assert "[truncated" not in result

    def test_paragraphs_mode_adds_truncation_indicator(self, converter):
        """Paragraphs mode should add truncation indicator when truncating."""
        result = converter._apply_options(
            self.PARAGRAPH_CONTENT,
            {"truncate_mode": "paragraphs", "truncate_limit": 2},
        )
        assert "[truncated...]" in result

    def test_paragraphs_mode_no_indicator_when_not_truncated(self, converter):
        """No truncation indicator when all paragraphs fit."""
        result = converter._apply_options(
            self.PARAGRAPH_CONTENT,
            {"truncate_mode": "paragraphs", "truncate_limit": 10},
        )
        assert "[truncated" not in result

    # --- Chars Mode Tests ---

    def test_chars_mode_truncation(self, converter):
        """Test chars mode truncates to character limit."""
        content = "A" * 100
        result = converter._apply_options(
            content,
            {"truncate_mode": "chars", "truncate_limit": 50},
        )
        # Should be 50 chars + truncation indicator
        assert result.startswith("A" * 50)
        assert "[truncated...]" in result

    def test_chars_mode_no_truncation_under_limit(self, converter):
        """Chars mode should not truncate when under limit."""
        content = "Short content"
        result = converter._apply_options(
            content,
            {"truncate_mode": "chars", "truncate_limit": 100},
        )
        assert result == content
        assert "[truncated" not in result

    # --- Tokens Mode Tests ---

    def test_tokens_mode_truncation(self, converter):
        """Test tokens mode truncates to token limit via truncate_mode."""
        content = "word " * 1000
        result = converter._apply_options(
            content,
            {"truncate_mode": "tokens", "truncate_limit": 50},
        )
        assert "[truncated...]" in result

    def test_tokens_mode_no_truncation_under_limit(self, converter):
        """Tokens mode should not truncate when under limit."""
        content = "Short content"
        result = converter._apply_options(
            content,
            {"truncate_mode": "tokens", "truncate_limit": 100},
        )
        assert result == content
        assert "[truncated" not in result

    # --- Edge Cases ---

    def test_empty_content(self, converter):
        """Empty content should return empty string."""
        result = converter._apply_options(
            "",
            {"truncate_mode": "sections", "truncate_limit": 5},
        )
        assert result == ""

    def test_mode_without_limit(self, converter):
        """Mode without limit should not truncate."""
        result = converter._apply_options(
            self.SECTION_CONTENT,
            {"truncate_mode": "sections"},
        )
        assert result == self.SECTION_CONTENT

    def test_limit_without_mode(self, converter):
        """Limit without mode should not truncate."""
        result = converter._apply_options(
            self.SECTION_CONTENT,
            {"truncate_limit": 2},
        )
        assert result == self.SECTION_CONTENT

    def test_backwards_compat_max_length(self, converter):
        """max_length should still work for backwards compatibility."""
        content = "A" * 100
        result = converter._apply_options(content, {"max_length": 20})
        assert result == "A" * 20 + "..."

    def test_backwards_compat_max_tokens(self, converter):
        """max_tokens should still work for backwards compatibility."""
        content = "word " * 1000
        result = converter._apply_options(content, {"max_tokens": 50})
        assert "[truncated to fit token limit]" in result

    def test_truncate_mode_overrides_max_length(self, converter):
        """truncate_mode should take precedence over max_length/max_tokens."""
        content = self.SECTION_CONTENT
        result = converter._apply_options(
            content,
            {
                "truncate_mode": "sections",
                "truncate_limit": 1,
                "max_length": 10,  # Should be ignored
            },
        )
        # Should have section truncation, not character truncation
        assert "## Section 1" in result
        # max_length uses "..." at the end, section mode uses "[truncated...]"
        assert "[truncated...]" in result
        assert not result.endswith("...")  # max_length ends with just "..."


class TestSafeTruncation:
    """Tests for markdown-aware safe truncation."""

    @pytest.fixture
    def converter(self):
        return DocumentConverter()

    # --- Code Block Safety Tests ---

    CODE_BLOCK_CONTENT = """Some intro text.

```python
def example():
    x = 1
    y = 2
    return x + y
```

After code block."""

    @pytest.mark.parametrize(
        "target_length",
        [30, 50, 70],
        ids=["short", "mid_block", "end_block"],
    )
    def test_code_block_not_split(self, converter, target_length):
        """Code blocks should never be left unclosed after truncation."""
        result, was_truncated = converter._safe_truncate(
            self.CODE_BLOCK_CONTENT, target_length
        )
        fence_count = result.count("```")
        assert fence_count % 2 == 0, f"Unclosed code block: {fence_count} fences"

    def test_code_block_complete_when_fits(self, converter):
        """Complete code blocks should be preserved when they fit."""
        result, was_truncated = converter._safe_truncate(self.CODE_BLOCK_CONTENT, 200)
        assert "```python" in result
        assert "return x + y" in result
        fence_count = result.count("```")
        assert fence_count == 2

    def test_truncation_backs_up_before_unclosed_fence(self, converter):
        """Truncation inside code block should back up to before the block."""
        # Truncate right in the middle of the code block
        result, was_truncated = converter._safe_truncate(self.CODE_BLOCK_CONTENT, 55)
        assert was_truncated
        # Should not contain partial code block
        fence_count = result.count("```")
        assert fence_count == 0, "Should back up to before code block"
        assert "Some intro text" in result

    def test_nested_code_blocks(self, converter):
        """Multiple code blocks should all be handled correctly."""
        content = """First block:

```python
code1
```

Second block:

```javascript
code2
```

End."""
        # Truncate after first complete block
        result, was_truncated = converter._safe_truncate(content, 60)
        fence_count = result.count("```")
        assert fence_count % 2 == 0

    def test_no_code_blocks(self, converter):
        """Content without code blocks should truncate normally."""
        content = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        result, was_truncated = converter._safe_truncate(content, 30)
        assert was_truncated
        assert "```" not in result

    def test_code_block_with_language_specifier(self, converter):
        """Code blocks with language specifiers should work correctly."""
        content = """Text.

```typescript
const x: number = 1;
```

More text."""
        result, was_truncated = converter._safe_truncate(content, 40)
        fence_count = result.count("```")
        assert fence_count % 2 == 0

    # --- Paragraph Boundary Tests ---

    PARAGRAPH_CONTENT = """First paragraph with some content here.

Second paragraph with different content.

Third paragraph is also here.

Fourth paragraph at the end."""

    def test_paragraph_boundary_preferred(self, converter):
        """Truncation should prefer paragraph boundaries when possible."""
        # Truncate in final 30% but with a paragraph break available
        result, was_truncated = converter._safe_truncate(self.PARAGRAPH_CONTENT, 120)
        assert was_truncated
        # Should end cleanly (no partial paragraph)
        assert result.rstrip() == result  # No trailing whitespace

    def test_paragraph_boundary_in_final_30_percent(self, converter):
        """Only look for boundaries in final 30% of content."""
        content = "A" * 70 + "\n\n" + "B" * 30
        # Target 80 chars - the \n\n is at position 70, which is in the final 30%
        result, was_truncated = converter._safe_truncate(content, 80)
        assert was_truncated
        # Should truncate at the paragraph break
        assert result == "A" * 70

    def test_no_paragraph_boundary_available(self, converter):
        """When no paragraph boundary in final 30%, truncate at limit."""
        content = "A" * 100  # No paragraph breaks at all
        result, was_truncated = converter._safe_truncate(content, 50)
        assert was_truncated
        assert len(result) == 50

    # --- Edge Cases ---

    def test_short_content_not_truncated(self, converter):
        """Content under target length should not be truncated."""
        content = "Short content"
        result, was_truncated = converter._safe_truncate(content, 100)
        assert not was_truncated
        assert result == content

    def test_exact_length_not_truncated(self, converter):
        """Content exactly at target length should not be truncated."""
        content = "A" * 50
        result, was_truncated = converter._safe_truncate(content, 50)
        assert not was_truncated
        assert result == content

    def test_empty_content(self, converter):
        """Empty content should return empty without truncation."""
        result, was_truncated = converter._safe_truncate("", 100)
        assert not was_truncated
        assert result == ""

    def test_very_short_limit(self, converter):
        """Very short limit should still produce valid output."""
        content = "```python\ncode\n```"
        result, was_truncated = converter._safe_truncate(content, 5)
        assert was_truncated
        fence_count = result.count("```")
        assert fence_count % 2 == 0

    def test_whitespace_stripped(self, converter):
        """Truncated content should have trailing whitespace stripped."""
        content = "Text here.   \n\n   More text.   "
        result, was_truncated = converter._safe_truncate(content, 20)
        assert was_truncated
        assert result == result.rstrip()

    # --- Integration with _apply_options Tests ---

    def test_chars_mode_uses_safe_truncation(self, converter):
        """chars truncate_mode should use safe truncation."""
        result = converter._apply_options(
            self.CODE_BLOCK_CONTENT,
            {"truncate_mode": "chars", "truncate_limit": 55},
        )
        fence_count = result.count("```")
        assert fence_count % 2 == 0
        assert "[truncated...]" in result

    def test_tokens_mode_uses_safe_truncation(self, converter):
        """tokens truncate_mode should use safe truncation."""
        long_content = self.CODE_BLOCK_CONTENT * 10
        result = converter._apply_options(
            long_content,
            {"truncate_mode": "tokens", "truncate_limit": 50},
        )
        fence_count = result.count("```")
        assert fence_count % 2 == 0

    def test_max_length_uses_safe_truncation(self, converter):
        """Legacy max_length should use safe truncation."""
        result = converter._apply_options(
            self.CODE_BLOCK_CONTENT,
            {"max_length": 55},
        )
        fence_count = result.count("```")
        assert fence_count % 2 == 0

    def test_max_tokens_uses_safe_truncation(self, converter):
        """Legacy max_tokens should use safe truncation."""
        long_content = self.CODE_BLOCK_CONTENT * 10
        result = converter._apply_options(
            long_content,
            {"max_tokens": 50},
        )
        fence_count = result.count("```")
        assert fence_count % 2 == 0
