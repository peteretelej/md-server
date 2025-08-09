# md-server

[![CI](https://github.com/peteretelej/md-server/actions/workflows/ci.yml/badge.svg)](https://github.com/peteretelej/md-server/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/peteretelej/md-server/branch/main/graph/badge.svg)](https://codecov.io/gh/peteretelej/md-server)
[![PyPI version](https://img.shields.io/pypi/v/md-server.svg)](https://pypi.org/project/md-server/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/docker-ghcr.io-blue)](https://github.com/peteretelej/md-server/pkgs/container/md-server)

HTTP API server for converting documents (PDF, Office document types), audio, web pages, Youtube videos and more to markdown.

## Installation

```bash
uvx md-server
```

## Usage

```bash
# Start server (default: localhost:8080)
uvx md-server

# Listen on all interfaces (for Docker/remote access)
uvx md-server --host 0.0.0.0

# Start on custom port
uvx md-server --port 9000

# Convert file
curl -X POST http://localhost:8080/convert -F "file=@document.pdf"

# Convert URL
curl -X POST http://localhost:8080/convert/url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article"}'

# Health check
curl http://localhost:8080/healthz
```

### Using Docker

```bash
# Run Docker image
docker run -d -p 127.0.0.1:8080:8080 --name md-server \
  --restart unless-stopped \
  ghcr.io/peteretelej/md-server

# Convert file
curl -X POST http://localhost:8080/convert -F "file=@document.pdf"
```

## Example Output

Convert a file to markdown:

```bash
$ curl -X POST http://localhost:8080/convert -F "file=@document.pdf"
{
  "markdown": "# Document Title\n\nThis is the converted content from the PDF...\n\n## Section 1\n\nMore content here."
}
```

Health check response:

```bash
$ curl http://localhost:8080/healthz
{
  "status": "healthy"
}
```

## Enhanced URL Conversion (Optional)

By default, md-server uses MarkItDown for URL conversion. To enable **Crawl4AI** for advanced web crawling with JavaScript rendering, install Playwright browsers:

```bash
uvx playwright install-deps
uvx playwright install chromium
```

If Playwright browsers are available, md-server will use Crawl4AI automatically for URL conversions. It provides better handling of JavaScript-heavy sites, smart content extraction and cleaning, and many more features.

## Endpoints

- `GET /healthz` - Health check
- `POST /convert` - Convert uploaded file to markdown
- `POST /convert/url` - Convert content from URL to markdown

## Development

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for development setup, testing, and contribution guidelines.

## Powered By

This project makes use of these excellent tools:

[![Powered by Crawl4AI](https://raw.githubusercontent.com/unclecode/crawl4ai/main/docs/assets/powered-by-light.svg)](https://github.com/unclecode/crawl4ai) [![microsoft/markitdown](https://img.shields.io/badge/microsoft-MarkItDown-0078D4?style=for-the-badge&logo=microsoft)](https://github.com/microsoft/markitdown)

## License

[MIT](./LICENSE)
