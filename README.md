# md-server

HTTP API server for converting files, documents, web pages, and multimedia content to markdown.

## Installation

```bash
uvx md-server
```

## Usage

```bash
# Start server
uvx md-server

# Convert file
curl -X POST http://localhost:8000/convert -F "file=@document.pdf"

# Convert YouTube video
curl -X POST http://localhost:8000/convert/url -d '{"url": "https://youtube.com/watch?v=..."}'

# Convert web page
curl -X POST http://localhost:8000/convert/url -d '{"url": "https://example.com/article"}'

# Health check
curl http://localhost:8000/healthz
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

# Run development server
uv run python -m md_server
# or
uv run md-server

# Run tests (when available)
uv run pytest

# Add new dependencies
uv add package-name

# Add dev dependencies
uv add --dev pytest ruff mypy
```

## TODO

- [x] Health endpoint for health check
- [ ] API endpoints for file upload & conversion
- [ ] Determine response format
- [ ] Support for URL input
- [ ] Format support validation: PDF, ppt, docx, excel etc
- [ ] tests + 90%+ coverage
- [ ] Dockerfile & run guidance
- [ ] CI/CD for for repo + PyPI publishing
