# Testing Design

## Overview

md-server uses user-centric testing focused on real workflows and practical use cases. Tests validate functionality from the perspective of actual users rather than internal implementation details.

## Test Structure

### User-Focused Organization

Tests are organized by user personas and workflows:

- **HTTP API Users** (`test_http_api.py`) - Web developers using curl, REST clients
- **SDK Users** (`test_sdk.py`) - Python developers using programmatic interface  
- **Remote SDK Users** (`test_remote_sdk.py`) - Clients connecting to remote servers
- **CLI Users** (`test_cli.py`) - Command-line server management
- **Security Validation** (`test_security.py`) - Security through user workflows
- **Capability Testing** (`test_capabilities.py`) - Feature detection and browser support

### Test Categories

#### 1. HTTP API Testing (`test_http_api.py`)

**Core User Workflows:**
- Binary file upload (PDF, DOCX, images)
- Multipart form upload 
- URL conversion with JavaScript rendering
- Base64 content conversion
- Text/HTML direct processing

**User Experience:**
- Error handling with actionable messages
- Health checks for monitoring
- Format discovery for capability detection
- Authentication flows (when configured)
- Large file handling and limits

#### 2. SDK Testing (`test_sdk.py`)

**Direct SDK Usage:**
- Local file conversion with custom options
- URL processing with browser detection
- Content conversion from binary data
- Text processing with MIME type hints
- Synchronous wrapper methods for blocking APIs

**Configuration and Advanced Features:**
- Custom timeout and size limits
- OCR, image extraction, formatting options
- Error handling with specific exception types
- Concurrent operations and thread safety
- Browser capability integration

#### 3. Remote SDK Testing (`test_remote_sdk.py`)

**Remote Connection Patterns:**
- Client-server communication validation
- Authentication with API keys
- Network error handling and retries
- Timeout configuration and handling
- Connection pooling and persistence

**User Experience:**
- Simple endpoint configuration
- Clear error messages for network issues
- Graceful degradation on connection failures
- Sync/async method consistency

#### 4. CLI Testing (`test_cli.py`)

**Command-Line Workflows:**
- Server startup with custom host/port
- Argument parsing and validation
- Port conflict detection and suggestions
- Help output and error messages
- Graceful shutdown handling

**Integration Testing:**
- Real server startup validation
- Browser detection during startup
- Health endpoint accessibility
- Process lifecycle management

#### 5. Security Testing (`test_security.py`)

**Security Through User Workflows:**
- SSRF protection via URL validation
- File type detection accuracy
- Path traversal prevention
- Malicious content sanitization
- Size limits and DoS protection

**Validation Patterns:**
- Input validation across all interfaces
- Content type verification
- Format support boundary testing
- Error message safety (no information leakage)

#### 6. Capability Testing (`test_capabilities.py`)

**Browser Detection:**
- JavaScript rendering availability
- Fallback behavior when browser unavailable
- Performance impact measurement
- Feature detection accuracy

**Format Support:**
- Content type detection through magic bytes
- Format validation across entry points
- Capability reporting consistency
- Detection performance optimization

## Testing Patterns

### User-Centric Approach

Tests validate complete user journeys:

```python
def test_upload_binary_file(self, client, test_files):
    """Test binary file upload - core user workflow."""
    with open(test_files["pdf"], "rb") as f:
        pdf_content = f.read()
    
    response = client.post("/convert", content=pdf_content, 
                          headers={"Content-Type": "application/pdf"})
    
    assert response.status_code == 200
    assert data["success"] is True
    assert "markdown" in data
```

### Realistic Error Scenarios

Tests cover errors users actually encounter:

```python
def test_network_timeout_handling(self, client):
    """Test timeout handling for slow URLs."""
    payload = {"url": "https://httpbin.org/delay/30", "options": {"timeout": 1}}
    
    response = client.post("/convert", json=payload)
    # Validates graceful timeout handling
```

### Configuration Validation

Tests verify user configuration patterns:

```python
def test_remote_initialization_custom(self):
    """Test remote SDK with custom configuration."""
    converter = RemoteMDConverter(
        endpoint="https://custom.api.com/",
        api_key="secret-key",
        timeout=60,
        max_retries=5
    )
```

## Test Data

### File Assets (`tests/test_data/`)

Real file samples for format testing:
- `test.pdf` - PDF document conversion
- `test.docx` - Office document processing  
- `test_blog.html` - Web content with structure
- `test.jpg` - Image with potential OCR
- `test.json` - Structured data conversion

### Dynamic Test Content

Generated content for specific scenarios:
- Large files for size limit testing
- Malicious content for security validation
- Edge cases for format detection
- Network scenarios for timeout testing

## Integration Points

### Server Lifecycle

Tests manage real server instances:
- Port allocation and conflict detection
- Startup time measurement
- Health check validation
- Graceful shutdown verification

### External Dependencies

Tests handle optional dependencies:
- Browser availability detection
- Network connectivity requirements
- File system permissions
- System resource constraints

## Performance Considerations

### Test Speed

- Unit tests complete under 100ms
- Integration tests with server startup under 15s
- Network tests include appropriate timeouts
- Large file tests use reasonable size limits

### Resource Management

- Temporary files cleaned up automatically
- Server processes terminated properly
- Network connections closed after tests
- Memory usage monitored for large operations

## Maintenance Guidelines

### Test Updates

When adding features:
1. Add user workflow test first
2. Cover error scenarios users might encounter  
3. Test configuration options users will need
4. Validate integration points
5. Update this documentation

### Documentation Sync

Tests serve as living documentation:
- Test names describe user scenarios
- Comments explain user perspective
- Error cases show expected behavior
- Configuration examples match real usage

Each test validates real user value rather than implementation details.