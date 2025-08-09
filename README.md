# md-server

[![CI](https://github.com/peteretelej/md-server/actions/workflows/ci.yml/badge.svg)](https://github.com/peteretelej/md-server/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/peteretelej/md-server/branch/main/graph/badge.svg)](https://codecov.io/gh/peteretelej/md-server)
[![PyPI version](https://img.shields.io/pypi/v/md-server.svg)](https://pypi.org/project/md-server/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

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
  etelej/md-server

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

## Endpoints

- `GET /healthz` - Health check
- `POST /convert` - Convert uploaded file to markdown
- `POST /convert/url` - Convert content from URL to markdown

## Development

```bash
# Clone repository
git clone https://github.com/peteretelej/md-server.git
cd md-server

# Create virtual environment and install dependencies
uv sync

# Run development server (localhost:8080)
uv run python -m md_server
# or
uv run md-server

# Run on custom port
uv run md-server --port 9000

# Run tests
uv run pytest

# Add new dependencies
uv add package-name

# Add dev dependencies
uv add --dev pytest ruff mypy
```

### Building Docker Image

```bash
# Build manually
docker build -t md-server .

# You can add env variables to a .env and use it

# Launch it locally
docker run -p 127.0.0.1:8080:8080 \
  --restart unless-stopped \
  --name md-server \
  --env-file .env \
  md-server
```

## Powered By

This project makes use of these excellent tools:

[![Powered by Crawl4AI](https://raw.githubusercontent.com/unclecode/crawl4ai/main/docs/assets/powered-by-light.svg)](https://github.com/unclecode/crawl4ai) [![microsoft/markitdown](https://img.shields.io/badge/microsoft-MarkItDown-0078D4?style=for-the-badge&logo=microsoft)](https://github.com/microsoft/markitdown)
