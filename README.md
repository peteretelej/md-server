# md-server

HTTP API server for document-to-markdown conversion.

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

# Health check
curl http://localhost:8000/healthz
```

## Endpoints

- `GET /healthz` - Health check
- `POST /convert` - Convert uploaded file
- `POST /convert/url` - Convert from URL

## TODO

- [ ] API endpoints for file upload & conversion
- [ ] Support for URL input
- [ ] Health endpoint for health check
- [ ] Format support validation: PDF, ppt, docx, excel etc
- [ ] tests + 90%+ coverage
- [ ] Dockerfile & run guidance
- [ ] CI/CD for for repo + PyPI publishing
