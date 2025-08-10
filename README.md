# md-server

**Convert any document, webpage, or media file to markdown via HTTP API.**

[![CI](https://github.com/peteretelej/md-server/actions/workflows/ci.yml/badge.svg)](https://github.com/peteretelej/md-server/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/peteretelej/md-server/branch/main/graph/badge.svg)](https://codecov.io/gh/peteretelej/md-server)
[![PyPI version](https://img.shields.io/pypi/v/md-server.svg)](https://pypi.org/project/md-server/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/docker-ghcr.io-blue)](https://github.com/peteretelej/md-server/pkgs/container/md-server)

md-server provides a HTTP API that accepts files, URLs, or raw content converts it into markdown. It automatically detects input types, handles everything from PDFs and Office documents, Youtube videos, images, to web pages with JavaScript rendering, and requires zero configuration to get started. Under the hood, it uses Microsoft's MarkItDown for document conversion and Crawl4AI for intelligent web scraping.

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
```

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

### Python Client Example

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

## Development

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for development setup, testing, and contribution guidelines.

## Powered By

This project makes use of these excellent tools:

[![Powered by Crawl4AI](https://raw.githubusercontent.com/unclecode/crawl4ai/main/docs/assets/powered-by-light.svg)](https://github.com/unclecode/crawl4ai) [![microsoft/markitdown](https://img.shields.io/badge/microsoft-MarkItDown-0078D4?style=for-the-badge&logo=microsoft)](https://github.com/microsoft/markitdown) [![Litestar Project](https://img.shields.io/badge/Litestar%20Org-%E2%AD%90%20Litestar-202235.svg?logo=python&labelColor=202235&color=edb641&logoColor=edb641)](https://github.com/litestar-org/litestar)

## License

[MIT](./LICENSE)
