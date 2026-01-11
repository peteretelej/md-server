import re
from dataclasses import dataclass
from typing import Optional


def clean_title(title: Optional[str]) -> Optional[str]:
    """
    Remove markdown formatting from title to provide clean plain text.

    Handles: links, images, bold, italic, inline code, heading prefixes.
    """
    if not title:
        return title

    # Remove image syntax: ![alt](url) -> alt (must come before links)
    title = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", title)

    # Remove link syntax: [text](url) -> text
    title = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", title)

    # Remove bold/italic (handle nested by running multiple times)
    for _ in range(3):
        title = re.sub(r"[*_]{1,3}([^*_]+)[*_]{1,3}", r"\1", title)

    # Remove inline code: `code` -> code
    title = re.sub(r"`([^`]+)`", r"\1", title)

    # Remove any remaining stray backticks
    title = title.replace("`", "")

    # Remove heading prefixes: # Title -> Title
    title = re.sub(r"^#{1,6}\s+", "", title)

    # Collapse multiple spaces
    title = re.sub(r"\s+", " ", title)

    return title.strip()


@dataclass
class ExtractedMetadata:
    """Container for extracted metadata."""

    title: Optional[str] = None
    estimated_tokens: int = 0
    detected_language: Optional[str] = None


def estimate_tokens(text: str, encoding: str = "cl100k_base") -> int:
    """
    Estimate token count using tiktoken.

    Falls back to char_count / 4 if tiktoken unavailable or fails.

    Args:
        text: Text to tokenize
        encoding: Tiktoken encoding name (default: cl100k_base for GPT-4/Claude)

    Returns:
        Estimated token count
    """
    if not text:
        return 0

    try:
        import tiktoken

        enc = tiktoken.get_encoding(encoding)
        return len(enc.encode(text))
    except ImportError:
        return len(text) // 4
    except Exception:
        return len(text) // 4


def detect_language(text: str) -> Optional[str]:
    """
    Detect language from text sample.

    Args:
        text: Text to analyze

    Returns:
        ISO 639-1 language code (e.g., "en", "fr", "de") or None
    """
    if not text or len(text.strip()) < 20:
        return None

    sample = text[:5000]

    try:
        from langdetect import LangDetectException, detect

        return detect(sample)
    except ImportError:
        return None
    except LangDetectException:
        return None
    except Exception:
        return None


def extract_title(markdown: str) -> Optional[str]:
    """
    Extract title from Markdown content.

    Checks for:
    1. First H1 heading (# Title)
    2. First non-empty line if short enough to be a title

    The extracted title is cleaned of markdown formatting.

    Args:
        markdown: Markdown content

    Returns:
        Extracted title (plain text) or None
    """
    if not markdown:
        return None

    h1_match = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
    if h1_match:
        title = h1_match.group(1).strip()
        title = re.sub(r"\s*[#*_`]+\s*$", "", title)
        return clean_title(title) if title else None

    lines = markdown.strip().split("\n")
    for line in lines:
        line = line.strip()
        if line and len(line) < 200:
            if line.startswith("```") or line.startswith("---"):
                continue
            return clean_title(line)

    return None


def format_frontmatter(
    title: Optional[str] = None,
    source: Optional[str] = None,
    source_type: str = "unknown",
    language: Optional[str] = None,
    tokens: int = 0,
) -> str:
    """
    Generate YAML frontmatter block.

    Args:
        title: Document title
        source: Source URL or filename
        source_type: Type of source (pdf, html, etc.)
        language: ISO 639-1 language code
        tokens: Estimated token count

    Returns:
        YAML frontmatter string with trailing newlines
    """
    lines = ["---"]

    if title:
        safe_title = title.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'title: "{safe_title}"')

    if source:
        lines.append(f"source: {source}")

    lines.append(f"type: {source_type}")

    if language:
        lines.append(f"language: {language}")

    lines.append(f"tokens: {tokens}")
    lines.append("---")

    return "\n".join(lines) + "\n\n"


class MetadataExtractor:
    """Convenience class for extracting all metadata at once."""

    def __init__(self, encoding: str = "cl100k_base"):
        self.encoding = encoding

    def extract(self, markdown: str) -> ExtractedMetadata:
        """
        Extract all metadata from Markdown content.

        Args:
            markdown: Markdown content

        Returns:
            ExtractedMetadata with title, tokens, and language
        """
        return ExtractedMetadata(
            title=extract_title(markdown),
            estimated_tokens=estimate_tokens(markdown, self.encoding),
            detected_language=detect_language(markdown),
        )

    def with_frontmatter(
        self,
        markdown: str,
        source: Optional[str] = None,
        source_type: str = "unknown",
    ) -> tuple[str, ExtractedMetadata]:
        """
        Extract metadata and prepend frontmatter to Markdown.

        Args:
            markdown: Original Markdown content
            source: Source URL or filename
            source_type: Type of source

        Returns:
            Tuple of (markdown_with_frontmatter, metadata)
        """
        metadata = self.extract(markdown)

        frontmatter = format_frontmatter(
            title=metadata.title,
            source=source,
            source_type=source_type,
            language=metadata.detected_language,
            tokens=metadata.estimated_tokens,
        )

        return frontmatter + markdown, metadata
