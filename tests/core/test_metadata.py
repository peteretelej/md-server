import pytest

from md_server.metadata import (
    ExtractedMetadata,
    MetadataExtractor,
    detect_language,
    estimate_tokens,
    extract_title,
    format_frontmatter,
)


class TestTokenEstimation:
    """Test token count estimation."""

    @pytest.mark.unit
    def test_empty_string(self):
        assert estimate_tokens("") == 0

    @pytest.mark.unit
    def test_simple_text(self):
        tokens = estimate_tokens("Hello, world!")
        assert 3 <= tokens <= 5

    @pytest.mark.unit
    def test_longer_text(self):
        text = "The quick brown fox jumps over the lazy dog. " * 10
        tokens = estimate_tokens(text)
        assert tokens > 50

    @pytest.mark.unit
    def test_unicode_text(self):
        text = "こんにちは世界"
        tokens = estimate_tokens(text)
        assert tokens > 0


class TestLanguageDetection:
    """Test language detection."""

    @pytest.mark.unit
    def test_english(self):
        text = (
            "This is a sample text in English for language detection testing purposes."
        )
        assert detect_language(text) == "en"

    @pytest.mark.unit
    def test_french(self):
        text = "Ceci est un exemple de texte en français pour tester la détection de langue."
        assert detect_language(text) == "fr"

    @pytest.mark.unit
    def test_german(self):
        text = (
            "Dies ist ein Beispieltext auf Deutsch zur Spracherkennung und zum Testen."
        )
        assert detect_language(text) == "de"

    @pytest.mark.unit
    def test_short_text_returns_none(self):
        assert detect_language("Hi") is None

    @pytest.mark.unit
    def test_empty_text_returns_none(self):
        assert detect_language("") is None

    @pytest.mark.unit
    def test_whitespace_only_returns_none(self):
        assert detect_language("   \n\t  ") is None


class TestTitleExtraction:
    """Test title extraction from Markdown."""

    @pytest.mark.unit
    def test_h1_heading(self):
        markdown = "# Document Title\n\nSome content here."
        assert extract_title(markdown) == "Document Title"

    @pytest.mark.unit
    def test_h1_with_extra_hashes(self):
        markdown = "# Title ##\n\nContent"
        title = extract_title(markdown)
        assert title == "Title"

    @pytest.mark.unit
    def test_h1_with_asterisks(self):
        markdown = "# Title **bold** *\n\nContent"
        title = extract_title(markdown)
        assert "Title" in title

    @pytest.mark.unit
    def test_no_heading_uses_first_line(self):
        markdown = "Short First Line\n\nMore content here."
        assert extract_title(markdown) == "Short First Line"

    @pytest.mark.unit
    def test_long_first_line_skipped(self):
        # Long first line is skipped, falls back to next valid line
        markdown = "a" * 250 + "\n\nMore content."
        assert extract_title(markdown) == "More content."

    @pytest.mark.unit
    def test_all_long_lines_returns_none(self):
        # When all lines are too long, returns None
        markdown = "a" * 250 + "\n\n" + "b" * 250
        assert extract_title(markdown) is None

    @pytest.mark.unit
    def test_empty_markdown(self):
        assert extract_title("") is None

    @pytest.mark.unit
    def test_none_markdown(self):
        assert extract_title(None) is None

    @pytest.mark.unit
    def test_skips_code_blocks(self):
        markdown = "```python\ncode\n```\n\n# Actual Title"
        assert extract_title(markdown) == "Actual Title"

    @pytest.mark.unit
    def test_skips_frontmatter_delimiter(self):
        markdown = "---\ntitle: metadata\n---\n\n# Real Title"
        assert extract_title(markdown) == "Real Title"

    @pytest.mark.unit
    def test_h1_not_at_start(self):
        markdown = "Some intro text\n\n# The Title\n\nContent"
        assert extract_title(markdown) == "The Title"


class TestFrontmatter:
    """Test YAML frontmatter generation."""

    @pytest.mark.unit
    def test_full_frontmatter(self):
        result = format_frontmatter(
            title="Test Document",
            source="https://example.com/doc.pdf",
            source_type="pdf",
            language="en",
            tokens=1234,
        )
        assert "---" in result
        assert 'title: "Test Document"' in result
        assert "source: https://example.com/doc.pdf" in result
        assert "type: pdf" in result
        assert "language: en" in result
        assert "tokens: 1234" in result

    @pytest.mark.unit
    def test_minimal_frontmatter(self):
        result = format_frontmatter(source_type="unknown", tokens=0)
        assert "type: unknown" in result
        assert "tokens: 0" in result
        assert "title:" not in result

    @pytest.mark.unit
    def test_escapes_quotes_in_title(self):
        result = format_frontmatter(title='Title with "quotes"', source_type="html")
        assert r'title: "Title with \"quotes\""' in result

    @pytest.mark.unit
    def test_escapes_backslashes_in_title(self):
        result = format_frontmatter(title=r"Title with \ backslash", source_type="html")
        assert r'title: "Title with \\ backslash"' in result

    @pytest.mark.unit
    def test_frontmatter_ends_with_newlines(self):
        result = format_frontmatter(source_type="text", tokens=100)
        assert result.endswith("\n\n")

    @pytest.mark.unit
    def test_no_source_omits_source_line(self):
        result = format_frontmatter(source_type="text", tokens=100)
        assert "source:" not in result

    @pytest.mark.unit
    def test_no_language_omits_language_line(self):
        result = format_frontmatter(source_type="text", tokens=100)
        assert "language:" not in result


class TestMetadataExtractor:
    """Test MetadataExtractor class."""

    @pytest.mark.unit
    def test_extract_all(self):
        markdown = "# English Document\n\nThis is a sample document with enough content for language detection to work properly."
        extractor = MetadataExtractor()
        metadata = extractor.extract(markdown)

        assert metadata.title == "English Document"
        assert metadata.estimated_tokens > 0
        assert metadata.detected_language == "en"

    @pytest.mark.unit
    def test_extract_returns_extracted_metadata(self):
        markdown = "# Test\n\nContent"
        extractor = MetadataExtractor()
        metadata = extractor.extract(markdown)

        assert isinstance(metadata, ExtractedMetadata)

    @pytest.mark.unit
    def test_with_frontmatter(self):
        markdown = "# Test Title\n\nThis is some content here for testing purposes and language detection."
        extractor = MetadataExtractor()
        result, metadata = extractor.with_frontmatter(
            markdown,
            source="https://example.com",
            source_type="html",
        )

        assert result.startswith("---")
        assert "# Test Title" in result
        assert metadata.title == "Test Title"

    @pytest.mark.unit
    def test_with_frontmatter_no_source(self):
        markdown = "# Title\n\nContent for testing."
        extractor = MetadataExtractor()
        result, metadata = extractor.with_frontmatter(
            markdown,
            source=None,
            source_type="text",
        )

        assert result.startswith("---")
        assert "source:" not in result.split("---")[1]

    @pytest.mark.unit
    def test_custom_encoding(self):
        extractor = MetadataExtractor(encoding="cl100k_base")
        markdown = "Test content"
        metadata = extractor.extract(markdown)
        assert metadata.estimated_tokens > 0

    @pytest.mark.unit
    def test_empty_markdown(self):
        extractor = MetadataExtractor()
        metadata = extractor.extract("")

        assert metadata.title is None
        assert metadata.estimated_tokens == 0
        assert metadata.detected_language is None
