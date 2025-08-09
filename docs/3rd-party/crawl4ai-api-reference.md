# Crawl4AI Technical API Documentation

## Overview

Crawl4AI is an LLM-friendly web crawler and scraper for converting web content to markdown with intelligent content filtering and extraction capabilities.

## Core Components

### AsyncWebCrawler

Primary asynchronous crawler for web content extraction.

```python
from crawl4ai import AsyncWebCrawler

async with AsyncWebCrawler(config=browser_config) as crawler:
    result = await crawler.arun(url, config=run_config)
```

### Configuration Classes

#### BrowserConfig

Controls browser behavior and execution environment.

```python
from crawl4ai import BrowserConfig

browser_config = BrowserConfig(
    browser_type="chromium",          # "chromium", "firefox", "webkit"
    headless=True,                    # Boolean: headless execution
    proxy="http://proxy:8080",        # Proxy URL or config dict
    viewport_width=1080,              # Browser viewport width
    viewport_height=600,              # Browser viewport height
    user_agent=None,                  # Custom user agent string
    user_data_dir=None,               # Persistent browser profile path
    cookies=[],                       # List of cookie dicts
    headers={},                       # Global headers dict
    verbose=True,                     # Enable debug logging
    text_mode=False,                  # Disable images for performance
    light_mode=False,                 # Reduced features for performance
    extra_args=[]                     # Additional browser arguments
)
```

**Proxy Configuration:**

```python
# Simple proxy
BrowserConfig(proxy="http://proxy.example.com:8080")

# Authenticated proxy
BrowserConfig(proxy="http://user:pass@proxy.example.com:8080")

# SOCKS proxy
BrowserConfig(proxy="socks5://proxy.example.com:1080")

# Detailed proxy config
BrowserConfig(proxy_config={
    "server": "http://proxy.example.com:8080",
    "username": "user",
    "password": "pass"
})
```

#### CrawlerRunConfig

Controls individual crawl execution parameters.

```python
from crawl4ai import CrawlerRunConfig, CacheMode

run_config = CrawlerRunConfig(
    # Content Processing
    word_count_threshold=200,         # Minimum words per content block
    markdown_generator=None,          # Custom markdown generator
    extraction_strategy=None,         # Data extraction strategy

    # Caching
    cache_mode=CacheMode.ENABLED,     # ENABLED, BYPASS, DISABLED

    # JavaScript & Dynamic Content
    js_code=None,                     # JavaScript to execute
    wait_for=None,                    # CSS/JS condition to wait for
    wait_until="networkidle",         # Page load completion condition

    # Output Formats
    screenshot=False,                 # Capture page screenshot
    pdf=False,                        # Generate PDF
    capture_mhtml=False,              # Save MHTML archive

    # Security & SSL
    fetch_ssl_certificate=False,      # Extract SSL certificate

    # Performance & Limits
    page_timeout=60000,               # Page load timeout (ms)
    verbose=False,                    # Debug logging
    stream=False,                     # Enable streaming for batch operations

    # Content Filtering
    excluded_tags=['form', 'header'], # HTML tags to exclude
    exclude_external_links=True,      # Remove external links
    process_iframes=True,             # Process iframe content
    remove_overlay_elements=True      # Remove popups/modals
)
```

**Cache Modes:**

- `CacheMode.ENABLED`: Use cached content when available
- `CacheMode.BYPASS`: Always fetch fresh content
- `CacheMode.DISABLED`: No caching

### LLMConfig

Configuration for LLM-based operations.

```python
from crawl4ai import LLMConfig

llm_config = LLMConfig(
    provider="openai/gpt-4o-mini",    # Model provider/name
    api_token="your-api-key",         # API token (or "env:VAR_NAME")
    base_url=None,                    # Custom endpoint URL
    temperature=0.7,                  # Model temperature
    max_tokens=2000                   # Maximum response tokens
)
```

**Supported Providers:**

- OpenAI: `openai/gpt-4o`, `openai/gpt-4o-mini`, `openai/o1-mini`
- Anthropic: `anthropic/claude-3-5-sonnet-20240620`
- Google: `gemini/gemini-pro`, `gemini/gemini-2.0-flash`
- Ollama: `ollama/llama3.3` (local, no token required)
- Groq: `groq/llama3-70b-8192`
- DeepSeek: `deepseek/deepseek-chat`

## Markdown Generation

### DefaultMarkdownGenerator

Primary markdown conversion engine with content filtering capabilities.

```python
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter

md_generator = DefaultMarkdownGenerator(
    content_filter=None,              # Content filter instance
    content_source="cleaned_html",    # HTML source selection
    options={}                        # HTML-to-markdown options
)
```

**Content Sources:**

- `"cleaned_html"` (default): Processed HTML after scraping strategy
- `"raw_html"`: Original HTML before processing
- `"fit_html"`: HTML optimized for schema extraction

**Markdown Options:**

```python
options = {
    "ignore_links": True,             # Remove all hyperlinks
    "ignore_images": True,            # Remove image references
    "escape_html": False,             # Handle HTML entities
    "body_width": 80,                 # Text wrapping width (0 = no wrap)
    "skip_internal_links": True,      # Skip same-page anchors
    "include_sup_sub": True           # Handle superscript/subscript
}
```

### Content Filters

#### PruningContentFilter

Removes noise and boilerplate content using structural analysis.

```python
from crawl4ai.content_filter_strategy import PruningContentFilter

filter = PruningContentFilter(
    threshold=0.5,                    # Content quality threshold (0.0-1.0)
    threshold_type="fixed",           # "fixed" or "dynamic"
    min_word_threshold=50             # Minimum words per block
)
```

#### BM25ContentFilter

Ranks content relevance based on search query using BM25 algorithm.

```python
from crawl4ai.content_filter_strategy import BM25ContentFilter

filter = BM25ContentFilter(
    user_query="machine learning",    # Search query
    bm25_threshold=1.2,              # Relevance threshold
    use_stemming=True,               # Enable word stemming
    language="english"               # Language for stemming
)
```

#### LLMContentFilter

AI-powered content filtering with custom instructions.

```python
from crawl4ai.content_filter_strategy import LLMContentFilter

filter = LLMContentFilter(
    llm_config=llm_config,           # LLM configuration
    instruction="Extract technical content only...",  # Custom filtering instruction
    chunk_token_threshold=4096,      # Chunk size for processing
    verbose=True                     # Enable debug output
)
```

### Markdown Result Structure

```python
result = await crawler.arun(url, config=config)

# Markdown access
print(result.markdown)                    # Default markdown output
print(result.markdown.raw_markdown)       # Unfiltered markdown
print(result.markdown.fit_markdown)       # Filtered markdown (when filter applied)
print(result.markdown.markdown_with_citations)  # With reference-style links
print(result.markdown.references_markdown)      # Link references only
```

## Data Extraction

### JsonCssExtractionStrategy

CSS/XPath-based structured data extraction.

```python
from crawl4ai import JsonCssExtractionStrategy

# Manual schema definition
schema = {
    "name": "Product Listings",
    "baseSelector": "div.product",
    "fields": [
        {"name": "title", "selector": "h2", "type": "text"},
        {"name": "price", "selector": ".price", "type": "text"},
        {"name": "link", "selector": "a", "type": "attribute", "attribute": "href"}
    ]
}

strategy = JsonCssExtractionStrategy(schema)

# LLM-generated schema (one-time cost)
schema = JsonCssExtractionStrategy.generate_schema(
    html_sample,
    llm_config=LLMConfig(provider="openai/gpt-4o", api_token="key")
)
```

### LLMExtractionStrategy

AI-powered content extraction with Pydantic schemas.

```python
from crawl4ai import LLMExtractionStrategy
from pydantic import BaseModel, Field

class Product(BaseModel):
    name: str = Field(description="Product name")
    price: float = Field(description="Product price")
    description: str = Field(description="Product description")

strategy = LLMExtractionStrategy(
    llm_config=llm_config,
    schema=Product.model_json_schema(),
    extraction_type="schema",
    instruction="Extract product information from the page",
    extra_args={"temperature": 0, "max_tokens": 2000}
)
```

## Advanced Features

### Deep Crawling

Multi-level crawling with intelligent link following.

```python
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy, BestFirstCrawlingStrategy
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer

# Breadth-first crawling
bfs_strategy = BFSDeepCrawlStrategy(
    max_depth=2,                     # Crawl depth limit
    include_external=False,          # Stay within domain
    max_pages=50,                    # Maximum pages to crawl
    score_threshold=0.3              # Minimum relevance score
)

# Best-first crawling with scoring
scorer = KeywordRelevanceScorer(
    keywords=["api", "documentation", "guide"],
    weight=0.7
)

best_strategy = BestFirstCrawlingStrategy(
    max_depth=2,
    url_scorer=scorer,
    max_pages=25
)

config = CrawlerRunConfig(
    deep_crawl_strategy=bfs_strategy,
    stream=True                      # Process results as available
)
```

### Adaptive Crawling

Intelligent crawling that stops when sufficient information is gathered.

```python
from crawl4ai import AdaptiveCrawler, AdaptiveConfig

# Statistical strategy (default)
config = AdaptiveConfig(
    strategy="statistical",
    confidence_threshold=0.8,        # Stop when 80% confident
    max_pages=50,                    # Safety limit
    top_k_links=5                    # Links to follow per page
)

# Semantic embedding strategy
config = AdaptiveConfig(
    strategy="embedding",
    embedding_model="sentence-transformers/all-MiniLM-L6-v2",
    n_query_variations=10,           # Generate query variations
    confidence_threshold=0.8
)

adaptive = AdaptiveCrawler(crawler, config)
result = await adaptive.digest(
    start_url="https://docs.python.org/3/",
    query="async context managers"
)
```

### Multi-URL Crawling

Concurrent crawling of multiple URLs.

```python
urls = ["https://example1.com", "https://example2.com", "https://example3.com"]

# Streaming mode
config = CrawlerRunConfig(stream=True)
async for result in await crawler.arun_many(urls, config=config):
    if result.success:
        print(f"Processed: {result.url}")

# Batch mode
config = CrawlerRunConfig(stream=False)
results = await crawler.arun_many(urls, config=config)
```

### Session Management

Preserve browser state across crawls.

```python
# Using storage state dictionary
storage_state = {
    "cookies": [
        {
            "name": "session",
            "value": "token123",
            "domain": "example.com",
            "path": "/",
            "expires": 1699999999.0
        }
    ],
    "origins": [
        {
            "origin": "https://example.com",
            "localStorage": [
                {"name": "auth_token", "value": "abc123"}
            ]
        }
    ]
}

async with AsyncWebCrawler(storage_state=storage_state) as crawler:
    result = await crawler.arun("https://example.com/protected")

# Using storage state file
async with AsyncWebCrawler(storage_state="session.json") as crawler:
    result = await crawler.arun("https://example.com")
```

## Error Handling and Response Structure

### CrawlResult Object

```python
result = await crawler.arun(url, config)

# Status and content
result.success                       # Boolean: crawl success
result.status_code                   # HTTP status code
result.error_message                 # Error details if failed
result.url                          # Final URL (after redirects)

# Content formats
result.html                         # Raw HTML
result.cleaned_html                 # Processed HTML
result.markdown                     # Markdown content
result.extracted_content            # JSON from extraction strategy

# Media and links
result.media                        # Dict of images, videos, audio
result.links                        # Dict of internal/external links
result.metadata                     # Page metadata

# Optional outputs
result.screenshot                   # Base64 screenshot (if enabled)
result.pdf                          # PDF bytes (if enabled)
result.ssl_certificate             # SSL cert info (if enabled)
```

### Error Handling Best Practices

```python
async with AsyncWebCrawler() as crawler:
    result = await crawler.arun(url, config)

    if not result.success:
        print(f"Crawl failed: {result.error_message}")
        print(f"Status code: {result.status_code}")
        return

    # Process successful result
    if result.extracted_content:
        try:
            data = json.loads(result.extracted_content)
            # Process extracted data
        except json.JSONDecodeError:
            print("Failed to parse extracted content as JSON")
```

## Common Usage Patterns

### Basic Markdown Extraction

```python
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

async def extract_markdown(url):
    config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        word_count_threshold=10,
        remove_overlay_elements=True
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url, config=config)

        if result.success:
            return result.markdown
        else:
            raise Exception(f"Failed to crawl {url}: {result.error_message}")

# Usage
markdown_content = await extract_markdown("https://example.com")
```

### Advanced Markdown with Filtering

```python
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter

async def extract_clean_markdown(url, query=None):
    # Choose filter based on whether we have a query
    if query:
        from crawl4ai.content_filter_strategy import BM25ContentFilter
        content_filter = BM25ContentFilter(
            user_query=query,
            bm25_threshold=1.2
        )
    else:
        content_filter = PruningContentFilter(
            threshold=0.6,
            min_word_threshold=50
        )

    md_generator = DefaultMarkdownGenerator(
        content_filter=content_filter,
        options={"ignore_links": True, "body_width": 0}
    )

    config = CrawlerRunConfig(
        markdown_generator=md_generator,
        cache_mode=CacheMode.BYPASS
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url, config=config)

        if result.success:
            # Return filtered markdown if filter was applied
            return result.markdown.fit_markdown or result.markdown
        else:
            raise Exception(f"Failed to crawl {url}: {result.error_message}")

# Usage
clean_content = await extract_clean_markdown("https://example.com", "machine learning")
```

### Dynamic Content Handling

```python
async def crawl_dynamic_content(url):
    # JavaScript to click "Load More" button
    js_code = """
    (async () => {
        const loadMore = document.querySelector('.load-more-btn');
        if (loadMore) {
            loadMore.click();
            await new Promise(resolve => setTimeout(resolve, 2000));
        }
    })();
    """

    config = CrawlerRunConfig(
        js_code=[js_code],
        wait_for="css:.content-loaded",  # Wait for content indicator
        page_timeout=30000
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url, config=config)
        return result.markdown if result.success else None
```
