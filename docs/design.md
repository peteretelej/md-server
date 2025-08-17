# Design Document

## Overview

HTTP server for converting documents to markdown. Uses Litestar framework with MarkItDown for conversion and optional Crawl4AI for web scraping.

## Architecture

### Entry Points
- `src/md_server/__main__.py` - CLI entry
- `src/md_server/app.py` - Litestar app configuration

### API Layer
- `src/md_server/controllers.py` - Request handlers
  - `POST /convert` - Main conversion endpoint
  - `GET /health` - Health check
  - `GET /formats` - Supported formats
- `src/md_server/models.py` - Pydantic models

### Business Logic
- `src/md_server/converter.py` - Conversion orchestration
  - MarkItDown integration
  - Crawl4AI integration (when available)
  - Input type detection

### Configuration
- `src/md_server/core/config.py` - Settings management

## Data Flow

```
Request → Controller → Input Detection → Converter → Response
```

### Input Detection

1. Check Content-Type header
2. For multipart: extract file
3. For JSON: check fields (url, content, text)
4. For binary: use magic bytes
5. Apply options and convert

## Request/Response

### Request Format
```json
{
  "url": "string",
  "content": "string",      // base64
  "text": "string",
  "filename": "string",
  "options": {}
}
```

### Response Format
```json
{
  "success": true,
  "markdown": "...",
  "metadata": {},
  "request_id": "req_..."
}
```

### Error Format
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "...",
    "details": {}
  },
  "request_id": "req_..."
}
```

## Technical Details

### Async Processing
- `asyncio.run_in_executor()` for sync libraries
- Non-blocking request handling
- Configurable timeouts

### Dependency Injection
- Singleton converters via Litestar DI
- Settings injection
- Clean testability

### Security
- SSRF protection (blocked IPs)
- Magic bytes validation
- Size limits per format
- URL scheme validation
- Path traversal prevention

## Project Structure

```
src/md_server/
├── __init__.py
├── __main__.py
├── app.py
├── controllers.py
├── converter.py
├── models.py
└── core/
    └── config.py
```

## Configuration

Environment variables:
- `MD_SERVER_DEBUG` - Debug mode
- `MD_SERVER_MAX_FILE_SIZE` - Max file size
- `MD_SERVER_TIMEOUT_SECONDS` - Conversion timeout
- `MD_SERVER_HOST` - Server host
- `MD_SERVER_PORT` - Server port

## Testing

- Unit tests for converters
- Integration tests for endpoints
- Security validation tests
- Performance benchmarks

## Documentation Structure

- `README.md` - Concise intro, quick start, basic examples
- `docs/API.md` - Consolidated API reference (HTTP, SDK, MCP)
- `docs/sdk/README.md` - SDK usage guide, examples, patterns
- `docs/mcp/README.md` - MCP integration guide (future)
- `docs/design.md` - Architecture documentation