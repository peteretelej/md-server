# md-server Design Document

md-server is an HTTP server for converting documents and web content to markdown.

## Overview

The server provides a simple HTTP API for converting various document types (PDFs, Office documents, images, web pages) to markdown format. It uses Litestar as the web framework to handle HTTP requests and responses, while leveraging the MarkItDown library for the actual document conversion processing. The architecture supports both file uploads and URL-based content conversion through dedicated endpoints.

## Architecture

### Entry Points
- `src/md_server/__main__.py` - CLI entry with argument parsing (host, port)
- `src/md_server/app.py` - Litestar application with dependency injection and route configuration

### API Layer
- `src/md_server/app.py` - Health check endpoint (`GET /healthz`)
- `src/md_server/controllers.py` - Controller class with conversion endpoints:
  - `POST /convert` - File upload conversion
  - `POST /convert/url` - URL content conversion
- `src/md_server/models.py` - Dataclass models for request/response

### Business Logic Layer
- `src/md_server/converter.py` - Direct MarkItDown integration with async executors

### Configuration Layer
- `src/md_server/core/config.py` - Service settings (file size limits, timeouts, debug mode)

## Data Flow

### File Conversion Flow
```
POST /convert → ConvertController.convert_file → convert_content → MarkItDown → markdown response
```

1. API receives multipart file upload
2. Controller validates and processes file content
3. Converter uses async executor to process content with MarkItDown
4. Response returns markdown or error

### URL Conversion Flow
```
POST /convert/url → ConvertController.convert_url_endpoint → convert_url → MarkItDown → markdown response
```

1. API receives URL in JSON payload
2. Controller validates URL format
3. Converter fetches and converts content via async executor
4. Response returns markdown or error

## Key Components

### Dependency Injection
- MarkItDown converter instances injected as singletons
- Settings injected via Litestar's dependency system
- Clean separation of concerns and testability

### Async Processing
- `asyncio.run_in_executor()` for sync MarkItDown operations
- Non-blocking request handling
- Configurable timeouts with `asyncio.wait_for()`

### Error Handling
- Litestar HTTPException for structured error responses
- Timeout protection on all conversions
- Proper error classification and status codes

## Performance Considerations

- Async processing prevents blocking
- Singleton MarkItDown instances reduce initialization overhead
- Memory-efficient file processing
- Configurable timeouts and limits

## Security Features

- File type validation through MarkItDown
- File size limits via configuration
- URL validation and sanitization
- Environment-based configuration management
- In-memory processing without temporary files

## Project Structure

```
src/md_server/
├── __init__.py
├── __main__.py         # CLI entry point
├── app.py             # Litestar app with DI configuration
├── controllers.py     # Single controller with all endpoints
├── converter.py       # Direct MarkItDown integration
├── models.py          # Dataclass models
└── core/
    ├── __init__.py
    └── config.py      # Settings and configuration
```

## Configuration Management

- Environment-based settings with Pydantic validation
- Debug mode configuration
- File size and timeout limits
- Singleton dependency injection for performance

## Testing

- Simple test suite focused on API functionality
- Litestar AsyncTestClient for endpoint testing
- Essential test data preserved for comprehensive validation
- Clean separation between unit and integration tests