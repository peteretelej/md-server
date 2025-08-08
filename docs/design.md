# md-server Design Document

## Overview

md-server is a FastAPI-based HTTP service that converts various document types (PDFs, Office docs, images, web pages) to markdown using the MarkItDown library. The service provides async processing with proper error handling and configuration management.

## Architecture

### Entry Points
- `src/md_server/__main__.py` - CLI entry with argument parsing (host, port)
- `src/md_server/main.py` - FastAPI application initialization with router registration

### API Layer
- `src/md_server/api/routes/health.py` - Health check endpoint (`GET /healthz`)
- `src/md_server/api/routes/convert.py` - Conversion endpoints:
  - `POST /convert` - File upload conversion
  - `POST /convert/url` - URL content conversion
- `src/md_server/api/models.py` - Pydantic models for request/response validation
- `src/md_server/api/deps.py` - Dependency injection for converters and settings

### Business Logic Layer
- `src/md_server/converters/base_converter.py` - Abstract converter interface
- `src/md_server/converters/file_converter.py` - File upload processing with validation
- `src/md_server/converters/url_converter.py` - URL content processing with validation

### Integration Layer  
- `src/md_server/adapters/markitdown_adapter.py` - Comprehensive MarkItDown wrapper with:
  - Async interface over sync library
  - Retry logic with exponential backoff
  - Connection pooling
  - Metrics collection
  - Memory management
  - Health checks

### Configuration Layer
- `src/md_server/core/config.py` - Basic service settings (file size limits, timeouts, allowed types)
- `src/md_server/core/markitdown_config.py` - Advanced MarkItDown configuration:
  - LLM integration (OpenAI, Azure OpenAI, Anthropic)
  - Azure Document Intelligence
  - Custom converters
  - Request session configuration
- `src/md_server/core/exceptions.py` - Custom exception hierarchy

## Data Flow

### File Conversion Flow
```
POST /convert → FileConverter → MarkItDownAdapter → MarkItDown → markdown response
```

1. API receives multipart file upload
2. FileConverter validates file type and size
3. MarkItDownAdapter processes content asynchronously
4. Response returns markdown or error

### URL Conversion Flow
```
POST /convert/url → URLConverter → MarkItDownAdapter → MarkItDown → markdown response
```

1. API receives URL in JSON payload
2. URLConverter validates URL format
3. MarkItDownAdapter fetches and converts content
4. Response returns markdown or error

## Key Components

### MarkItDownAdapter
- **Purpose**: Async wrapper for sync MarkItDown library
- **Features**:
  - Executor-based async processing
  - Configurable timeouts and retries
  - Memory optimization with garbage collection
  - Comprehensive error handling
  - Metrics tracking
  - Resource cleanup

### Dependency Injection
- Settings and converters injected via FastAPI dependencies
- Enables clean testing and configuration management
- Type-annotated dependencies for validation

### Exception Hierarchy
- `MarkdownConversionError` - Base conversion error
- `UnsupportedFileTypeError` - Invalid file type
- `FileTooLargeError` - Size limit exceeded
- `URLFetchError` - URL retrieval failure
- `ConversionTimeoutError` - Processing timeout

### Configuration Management
- Environment-based settings with Pydantic validation
- Support for advanced MarkItDown features (LLM, Azure services)
- Fallback to standard environment variables
- Comprehensive validation and error reporting

## Error Handling

### API Level
- HTTP status code mapping for specific errors
- Structured error responses
- Request validation via Pydantic models

### Service Level
- Timeout protection on all conversions
- Retry logic for transient failures
- Resource cleanup on errors
- Detailed logging with context

## Performance Considerations

- Async processing prevents blocking
- Connection pooling for HTTP requests
- Memory management for large files
- Configurable timeouts and limits
- Metrics collection for monitoring

## Security Features

- File type validation
- File size limits
- URL validation and sanitization
- Environment-based secret management
- No temporary file creation (in-memory processing)