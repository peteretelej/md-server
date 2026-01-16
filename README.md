# md-server

**Convert any document, webpage, or media file to markdown. Works as an HTTP API or directly with AI tools via MCP.**

[![CI](https://github.com/peteretelej/md-server/actions/workflows/ci.yml/badge.svg)](https://github.com/peteretelej/md-server/actions/workflows/ci.yml)
[![Coverage Status](https://coveralls.io/repos/github/peteretelej/md-server/badge.svg?branch=main)](https://coveralls.io/github/peteretelej/md-server?branch=main)
[![PyPI version](https://img.shields.io/pypi/v/md-server.svg)](https://pypi.org/project/md-server/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/docker-ghcr.io-blue)](https://github.com/peteretelej/md-server/pkgs/container/md-server)

md-server converts files, URLs, or raw content into markdown. It automatically detects input types, handles everything from PDFs and Office documents, YouTube videos, images, to web pages with JavaScript rendering, and requires zero configuration to get started.

**Two ways to use it:**

- **[HTTP API](#http-api)** — REST API to convert documents and websites to markdown
- **[MCP Server](#mcp-server-for-ai-assistants)** — Local MCP Server for integration with AI tools (OpenCode, Claude Desktop, Cursor, custom agents)

Under the hood, it uses Microsoft's MarkItDown for document conversion and Crawl4AI for intelligent web scraping.

## HTTP API

**Prerequisites:**

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- _(Optional)_ Install browser for JavaScript-rendered pages: `uvx playwright install --with-deps chromium`

```bash
# Starts server at localhost:8080
uvx md-server

# Convert a file
curl -X POST localhost:8080/convert --data-binary @document.pdf

# Convert a URL
curl -X POST localhost:8080/convert \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'

# Convert HTML text
curl -X POST localhost:8080/convert \
  -H "Content-Type: application/json" \
  -d '{"text": "<h1>Title</h1><p>Content</p>", "mime_type": "text/html"}'
```

## MCP Server for AI Assistants

md-server runs as a local [MCP server](https://modelcontextprotocol.io), giving AI assistants like Claude Desktop, Cursor, Copilot, and OpenCode the ability to read documents and web pages directly.

**Prerequisites:**

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- _(Optional)_ Install browser for JavaScript-rendered pages: `uvx playwright install --with-deps chromium`

Add to your MCP configuration:

```json
{
  "mcpServers": {
    "md-server": {
      "command": "uvx",
      "args": ["md-server[mcp]", "--mcp-stdio"]
    }
  }
}
```

The first run downloads dependencies and may take a minute.

Once configured, your AI gets the **`read_resource`** tool:

- Fetch web pages, articles, documentation, online PDFs via URL
- Read uploaded documents (PDF, DOCX, XLSX, PPTX, images with OCR)
- Supports token-based truncation and markdown-aware sectioning

See [MCP Guide](docs/mcp.md) for all options and troubleshooting.

## HTTP API Server Installation

For MCP server setup (AI tools), see [MCP Server](#mcp-server-for-ai-assistants) above.

### Using uvx (Recommended)

```bash
uvx md-server
```

### Using Docker

The [Docker image](https://github.com/peteretelej/md-server/pkgs/container/md-server) includes browser support for JavaScript rendering.

```bash
docker run -p 127.0.0.1:8080:8080 ghcr.io/peteretelej/md-server
```

- Memory: 1GB recommended (minimum 512MB)
- Storage: ~1.2GB image size

## API

### `POST /convert`

Single endpoint that accepts multiple input types and automatically detects what you're sending.

#### Input Methods

```bash
# Binary file upload
curl -X POST localhost:8080/convert --data-binary @document.pdf

# Multipart form upload
curl -X POST localhost:8080/convert -F "file=@presentation.pptx"

# URL conversion
curl -X POST localhost:8080/convert \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'

# Base64 content
curl -X POST localhost:8080/convert \
  -H "Content-Type: application/json" \
  -d '{"content": "base64_encoded_file_here", "filename": "report.docx"}'

# Raw text
curl -X POST localhost:8080/convert \
  -H "Content-Type: application/json" \
  -d '{"text": "# Already Markdown\n\nBut might need cleaning"}'

# Text with specific format (HTML, XML, etc.)
curl -X POST localhost:8080/convert \
  -H "Content-Type: application/json" \
  -d '{"text": "<h1>HTML Title</h1><p>Convert HTML to markdown</p>", "mime_type": "text/html"}'
```

#### Response Format

```json
{
  "success": true,
  "markdown": "# Converted Content\n\nYour markdown here...",
  "metadata": {
    "source_type": "pdf",
    "source_size": 102400,
    "markdown_size": 8192,
    "conversion_time_ms": 245,
    "detected_format": "application/pdf"
  },
  "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
}
```

#### Options

```json
{
  "url": "https://example.com",
  "options": {
    "js_rendering": true, // Use headless browser for JavaScript sites
    "extract_images": true, // Extract and link images
    "ocr_enabled": true, // OCR for scanned PDFs/images
    "preserve_formatting": true // Keep complex formatting
  }
}
```

### `GET /formats`

Returns supported formats and capabilities.

```bash
curl localhost:8080/formats
```

### `GET /health`

Health check endpoint.

```bash
curl localhost:8080/health
```

## Supported Formats

**Documents**: PDF, DOCX, XLSX, PPTX, ODT, ODS, ODP
**Web**: HTML, URLs (with JavaScript rendering)
**Images**: PNG, JPG, JPEG (with OCR)
**Audio**: MP3, WAV (transcription) — requires [ffmpeg](https://ffmpeg.org/download.html)
**Video**: YouTube URLs
**Text**: TXT, MD, CSV, XML, JSON

## Advanced Usage

### JavaScript-Rendered Pages

**Docker** includes browser support out of the box.

**Local installations** use MarkItDown for URL conversion by default. To read pages that require JavaScript (SPAs, dashboards, interactive apps):

```bash
uvx playwright install --with-deps chromium
```

When a browser is available, md-server automatically uses Crawl4AI for these pages.

### Pipe from Other Commands

```bash
# Convert HTML from stdin
echo "<h1>Hello</h1>" | curl -X POST localhost:8080/convert \
  --data-binary @- \
  -H "Content-Type: text/html"

# Chain with other tools
pdftotext document.pdf - | curl -X POST localhost:8080/convert \
  --data-binary @-
```

### Python SDK

```bash
pip install md-server[sdk]
```

```python
from md_server.sdk import MDConverter

converter = MDConverter(ocr_enabled=True, js_rendering=True)

# Async
result = await converter.convert_file('document.pdf')
result = await converter.convert_url('https://example.com')
print(result.markdown)

# Sync
result = converter.convert_file_sync('document.pdf')
```

For remote API usage and advanced patterns, see the [Python SDK documentation](docs/sdk/README.md).

## Error Handling

Errors include actionable information:

```json
{
  "success": false,
  "error": {
    "code": "UNSUPPORTED_FORMAT",
    "message": "File format not supported",
    "details": {
      "detected_format": "application/x-rar",
      "supported_formats": ["pdf", "docx", "html", "..."]
    }
  },
  "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
}
```

## Documentation

Full documentation is available in the [docs](docs/) directory:

- [API Reference](docs/API.md) - HTTP endpoints, options, and responses
- [MCP Guide](docs/mcp.md) - Claude Desktop, Cursor, and AI tool setup
- [Python SDK](docs/sdk/README.md) - Library usage for Python applications
- [Configuration](docs/configuration.md) - Environment variables reference
- [Troubleshooting](docs/troubleshooting.md) - Common issues and solutions

## Development

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for development setup, testing, and contribution guidelines.

## Powered By

This project makes use of these excellent tools:

[![Powered by Crawl4AI](https://raw.githubusercontent.com/unclecode/crawl4ai/main/docs/assets/powered-by-light.svg)](https://github.com/unclecode/crawl4ai) [![microsoft/markitdown](https://img.shields.io/badge/microsoft-MarkItDown-0078D4?style=for-the-badge&logo=microsoft)](https://github.com/microsoft/markitdown) [![Litestar Project](https://img.shields.io/badge/Litestar%20Org-%E2%AD%90%20Litestar-202235.svg?logo=python&labelColor=202235&color=edb641&logoColor=edb641)](https://github.com/litestar-org/litestar)

## License

[MIT](./LICENSE)
