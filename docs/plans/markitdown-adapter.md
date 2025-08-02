# MarkItDown Adapter Improvement Plan

## Overview

Comprehensive plan to improve the MarkItDown adapter implementation to leverage the full API capabilities, eliminate inefficiencies, and support all required endpoints.

## Current Issues Analysis

### Critical Issues
- **Deprecated API**: Uses `result.text_content` instead of `result.markdown`
- **Inefficient Processing**: Creates temporary files for content conversion instead of using stream API
- **Missing URL Support**: No implementation for `/convert/url` endpoint requirement
- **No StreamInfo Usage**: Missing format detection hints for better conversion accuracy
- **Limited Error Handling**: Doesn't leverage MarkItDown's specific exception types
- **No Configuration**: Missing support for MarkItDown's extensive configuration options

### Missing Features
- Direct stream conversion without temporary files
- URL conversion capability
- StreamInfo metadata utilization
- Advanced configuration (LLM integration, Azure Document Intelligence, etc.)
- Proper exception mapping
- Async-compatible initialization

## Implementation Plan

### Phase 1: Core API Updates
**Goal**: Fix deprecated API usage and improve basic functionality

#### Tasks
- [x] Replace `result.text_content` with `result.markdown` in both conversion methods
- [x] Add proper StreamInfo import and usage with format detection hints
- [x] Add proper exception imports and mapping from MarkItDown library
- [x] Update error handling to use specific MarkItDown exceptions
- [x] Improve type hints and documentation for all methods
- [x] Add basic configuration options (enable_plugins, enable_builtins)
- [x] Run tests to ensure basic functionality still works
- [x] Mark Phase 1 complete

**Expected Outcome**: Adapter uses current MarkItDown API and has better error reporting

### Phase 2: Stream-Based Content Conversion
**Goal**: Eliminate temporary file creation for content conversion

#### Tasks
- [ ] Implement `convert_stream` method using MarkItDown's `convert_stream` API
- [ ] Replace temporary file approach in `convert_content` with direct stream conversion
- [ ] Add StreamInfo creation from filename parameter for better format detection
- [ ] Add support for BytesIO stream conversion
- [ ] Test stream conversion with various file formats
- [ ] Verify no temporary files are created during content conversion
- [ ] Run tests and ensure performance improvement
- [ ] Mark Phase 2 complete

**Expected Outcome**: Content conversion uses streams directly, improving performance and eliminating temporary files

### Phase 3: URL Conversion Support
**Goal**: Add URL conversion capability for `/convert/url` endpoint

#### Tasks
- [ ] Implement `convert_url` method using MarkItDown's `convert` method with URL support
- [ ] Add URL validation and sanitization
- [ ] Implement proper timeout handling for URL fetching
- [ ] Add support for custom headers if needed
- [ ] Handle URL-specific errors (network issues, invalid URLs, etc.)
- [ ] Add StreamInfo support for URL conversions
- [ ] Test URL conversion with various document types
- [ ] Run tests and verify URL conversion works correctly
- [ ] Mark Phase 3 complete

**Expected Outcome**: Adapter supports URL conversion for all MarkItDown-supported URL formats

### Phase 4: Advanced Configuration Support
**Goal**: Add support for MarkItDown's advanced configuration options

#### Tasks
- [ ] Add configuration class for MarkItDown options
- [ ] Implement LLM client configuration support
- [ ] Add Azure Document Intelligence configuration
- [ ] Add support for custom converter registration
- [ ] Implement plugin system integration
- [ ] Add configuration validation
- [ ] Update constructor to accept configuration parameters
- [ ] Add environment variable support for sensitive configurations
- [ ] Test configuration options work correctly
- [ ] Run tests and verify advanced features
- [ ] Mark Phase 4 complete

**Expected Outcome**: Adapter supports full MarkItDown configuration including LLM and Azure integration

### Phase 5: Performance and Reliability Improvements
**Goal**: Optimize performance and improve reliability

#### Tasks
- [ ] Add connection pooling for URL conversions using custom requests session
- [ ] Implement proper resource cleanup for all conversion methods
- [ ] Add retry logic for transient failures
- [ ] Optimize memory usage for large file handling
- [ ] Add comprehensive logging for debugging
- [ ] Implement health check method for dependency validation
- [ ] Add metrics collection points for monitoring
- [ ] Test performance improvements
- [ ] Run full test suite
- [ ] Mark Phase 5 complete

**Expected Outcome**: Adapter is optimized for production use with proper error recovery and monitoring

### Phase 6: Code Quality and Documentation
**Goal**: Simplify code structure and ensure maintainability

#### Tasks
- [ ] Review all new code for simplicity and clarity
- [ ] Refactor any complex methods into smaller, focused functions
- [ ] Ensure consistent async/await patterns throughout
- [ ] Add comprehensive type hints
- [ ] Remove any code duplication
- [ ] Verify error messages are clear and actionable
- [ ] Ensure code follows FastAPI async best practices
- [ ] Compare implementation with main branch for improvements
- [ ] Run final test suite
- [ ] Mark Phase 6 complete

**Expected Outcome**: Clean, maintainable adapter implementation ready for production

## Implementation Details

### New Adapter Structure

```python
class MarkItDownAdapter:
    def __init__(self, config: MarkItDownConfig = None, timeout_seconds: int = 30):
        # Initialize MarkItDown instance with configuration
        # Set up session management and timeouts
        
    async def convert_file(self, file_path: Union[str, Path], stream_info: StreamInfo = None) -> str:
        # Convert local file using convert_local
        
    async def convert_content(self, content: bytes, filename: str = None, mimetype: str = None) -> str:
        # Convert using convert_stream with BytesIO
        
    async def convert_url(self, url: str, stream_info: StreamInfo = None) -> str:
        # Convert URL using convert method
        
    async def health_check(self) -> bool:
        # Validate MarkItDown dependencies
```

### Configuration Support

```python
class MarkItDownConfig:
    enable_builtins: bool = True
    enable_plugins: bool = False
    llm_client: Optional[Any] = None
    llm_model: Optional[str] = None
    docintel_endpoint: Optional[str] = None
    docintel_credential: Optional[Any] = None
    requests_session: Optional[requests.Session] = None
```

### StreamInfo Utilization

- Extract MIME type from filename extensions
- Pass content length hints when available
- Include original filename for better format detection
- Add URL information for web-based conversions

### Exception Mapping

- Map MarkItDown exceptions to adapter-specific exceptions
- Provide detailed error context for debugging
- Maintain backward compatibility with existing error types

## Success Criteria

### Functional Requirements
- All conversion methods work without temporary files
- URL conversion supports all MarkItDown-compatible URLs
- StreamInfo metadata improves conversion accuracy
- Advanced configurations work correctly
- Error handling provides clear, actionable messages

### Performance Requirements
- Content conversion shows measurable performance improvement
- Memory usage remains stable for large files
- URL conversion completes within timeout limits
- No resource leaks in any conversion path

### Quality Requirements
- Code is simple, clear, and maintainable
- Full async compatibility with FastAPI
- Comprehensive error handling
- All existing functionality preserved

## Testing Strategy

### Unit Tests
- Test each conversion method independently
- Verify error handling for all failure modes
- Test configuration options thoroughly
- Validate StreamInfo usage improves results

### Integration Tests
- Test with real files of various formats
- Verify URL conversion with live URLs
- Test timeout and error scenarios
- Validate memory usage patterns

### Performance Tests
- Compare before/after conversion times
- Measure memory usage during conversion
- Test with large files and concurrent requests
- Verify no resource leaks over time

## Risk Mitigation

### Compatibility Risks
- Maintain existing method signatures
- Preserve error types for backward compatibility
- Test with existing integration points

### Performance Risks
- Monitor memory usage during stream conversion
- Implement proper timeout handling
- Add circuit breaker for problematic URLs

### Security Risks
- Validate URLs before conversion
- Implement resource limits for large files
- Sanitize file paths and URLs properly