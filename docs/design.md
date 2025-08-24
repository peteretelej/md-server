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

### Core Business Logic
- `src/md_server/core/converter.py` - Document conversion orchestration
  - MarkItDown integration
  - Crawl4AI integration (when available)
  - Input type detection and routing
- `src/md_server/core/detection.py` - Content type detection
- `src/md_server/core/browser.py` - Browser capability management
- `src/md_server/core/security.py` - Security validations
- `src/md_server/core/factories.py` - Service factories
- `src/md_server/core/validation.py` - Input validation

### SDK Layer
- `src/md_server/sdk/converter.py` - Local SDK interface (91 lines)
- `src/md_server/sdk/remote.py` - Remote API client (146 lines)
- `src/md_server/sdk/models.py` - SDK data models (reuses core models)
- `src/md_server/sdk/__init__.py` - Clean public API (14 lines)

### Configuration
- `src/md_server/core/config.py` - Settings management

## Data Flow

### HTTP API Flow
```
Request → Controller → Core.DocumentConverter → Response
```

### SDK Flow

#### Local SDK
```
User Code → MDConverter → DocumentConverter → ConversionResult
```

#### Remote SDK  
```
User Code → RemoteMDConverter → HTTP Client → API → ConversionResult
```

### Input Detection

1. Check Content-Type header
2. For multipart: extract file
3. For JSON: check fields (url, content, text)
4. For binary: use magic bytes
5. Route to appropriate core converter method

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
├── app.py                    # Litestar app setup
├── controllers.py            # HTTP request handlers
├── models.py                 # API request/response models
├── core/                     # Business logic (moved from root)
│   ├── __init__.py
│   ├── config.py            # Settings management
│   ├── converter.py         # Core conversion logic
│   ├── detection.py         # Content type detection  
│   ├── browser.py           # Browser capabilities
│   ├── security.py          # Security validation
│   ├── factories.py         # Service factories
│   └── validation.py        # Input validation
└── sdk/                      # Python SDK
    ├── __init__.py          # Clean public exports (14 lines)
    ├── converter.py         # Local converter wrapper (91 lines)  
    ├── remote.py            # HTTP client (146 lines)
    └── models.py            # SDK data models (reuses core models)
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