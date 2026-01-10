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
- **HTTP API** — Run as a server for any application
- **MCP Server** — Direct integration with AI tools (Claude Desktop, Cursor, custom agents)

Under the hood, it uses Microsoft's MarkItDown for document conversion and Crawl4AI for intelligent web scraping.

## Quick Start

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

## AI Integration (MCP)

md-server works directly with AI tools via [Model Context Protocol (MCP)](https://modelcontextprotocol.io). This lets Claude Desktop, Cursor, and other AI tools convert documents and read web pages without any HTTP setup.

### Claude Desktop / Cursor

Add to your MCP configuration:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Linux:** `~/.config/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

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

Once configured, your AI can convert documents directly:

> "Read the Python asyncio documentation and summarize it"
> "What's in this PDF?" *(with file attached)*
> "Convert this webpage to markdown: https://example.com"

### MCP Modes

```bash
# For local AI tools (Claude Desktop, Cursor)
uvx md-server[mcp] --mcp-stdio

# For network-based AI agents
uvx md-server[mcp] --mcp-sse --port 9000
```

See [MCP Integration Guide](docs/mcp-guide.md) for complete setup instructions and troubleshooting.

## Installation

### Using uvx (Recommended)

```bash
uvx md-server
```

### Using Docker

You can run on Docker using the [md-server docker image](https://github.com/peteretelej/md-server/pkgs/container/md-server). The Docker image includes full browser support for JavaScript rendering.

```bash
docker run -p 127.0.0.1:8080:8080 ghcr.io/peteretelej/md-server
```

**Resource Requirements:**
- Memory: 1GB recommended (minimum 512MB)
- Storage: ~1.2GB image size
- Initial startup: 10-15 seconds (browser initialization)

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
**Audio**: MP3, WAV (transcription)  
**Video**: YouTube URLs  
**Text**: TXT, MD, CSV, XML, JSON

## Advanced Usage

### Enhanced URL Conversion

**Docker deployments** include full browser support automatically - JavaScript rendering is enabled out of the box.

**Local installations** use MarkItDown for URL conversion by default. To enable **Crawl4AI** with JavaScript rendering:

```bash
uvx playwright install-deps
uvx playwright install chromium
```

When browsers are available, md-server automatically uses Crawl4AI for better handling of JavaScript-heavy sites, smart content extraction, and enhanced web crawling capabilities.

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

Install the SDK:

```bash
pip install md-server[sdk]
```

#### Local Conversion

```python
from md_server.sdk import MDConverter
import asyncio

# Create converter
converter = MDConverter(
    ocr_enabled=True,
    js_rendering=True,
    extract_images=True,
    timeout=60
)

# Async usage
async def convert_documents():
    # Convert file
    result = await converter.convert_file('document.pdf')
    print(result.markdown)
    
    # Convert URL
    result = await converter.convert_url('https://example.com')
    print(result.markdown)
    
    # Convert content
    with open('file.docx', 'rb') as f:
        result = await converter.convert_content(f.read(), filename='file.docx')
    print(result.markdown)
    
    # Convert text
    result = await converter.convert_text('<h1>HTML</h1>', mime_type='text/html')
    print(result.markdown)

asyncio.run(convert_documents())

# Sync usage
result = converter.convert_file_sync('document.pdf')
print(result.markdown)
```

#### Remote API Client

```python
from md_server.sdk import RemoteMDConverter
import asyncio

# Create remote client
async def use_remote_api():
    async with RemoteMDConverter('http://localhost:8080') as client:
        # Convert file
        result = await client.convert_file('document.pdf')
        print(result.markdown)
        
        # Convert URL
        result = await client.convert_url('https://example.com')
        print(result.markdown)
        
        # Convert text
        result = await client.convert_text('<h1>HTML</h1>', mime_type='text/html')
        print(result.markdown)

asyncio.run(use_remote_api())

# Or sync
client = RemoteMDConverter('http://localhost:8080')
result = client.convert_file_sync('document.pdf')
print(result.markdown)
```

#### Raw HTTP Client

```python
import requests

# Convert file
with open('document.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8080/convert',
        data=f.read(),
        headers={'Content-Type': 'application/pdf'}
    )
    markdown = response.json()['markdown']

# Convert URL
response = requests.post(
    'http://localhost:8080/convert',
    json={'url': 'https://example.com'}
)
markdown = response.json()['markdown']
```

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
- [MCP Integration](docs/mcp-guide.md) - Claude Desktop, Cursor, and AI tool setup
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
