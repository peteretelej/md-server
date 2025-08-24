# Testing Design (Simplified)

## Overview

md-server uses **simple, fast, user-centric testing** focused on real workflows and 100% code coverage. Tests validate functionality from the user perspective while ensuring every line of code is tested efficiently.

**Core Principles:**
- **User-first:** Test what users actually do
- **Simple:** Direct tests without over-engineering  
- **Fast:** Complete test suite runs in <2 minutes
- **Complete:** 100% code coverage of core business logic
- **Reliable:** Zero flaky tests, deterministic behavior

---

## Test Architecture Alignment

### Core-First Testing Structure

Tests mirror the simplified architecture:

```
tests/
├── test_data/              # Real file samples (preserved)
│   ├── test.pdf            # PDF for conversion testing
│   ├── test.docx           # Office document
│   ├── test_blog.html      # Web content structure
│   ├── test.jpg            # Image with OCR potential
│   └── test.json           # Structured data
├── test_server/            # Local HTTP server content (NEW)
│   ├── simple.html         # Basic HTML for URL tests
│   ├── javascript.html     # HTML with JS for browser tests
│   ├── large.html          # Larger content for performance
│   ├── malformed.html      # Invalid HTML for error testing
│   └── slow_response.html  # Simulated slow response
├── core/                   # Core business logic tests (100% coverage)
│   ├── test_converter.py   # Document conversion engine
│   ├── test_detection.py   # Content type detection
│   ├── test_security.py    # Security validation  
│   └── test_browser.py     # Browser capabilities
├── test_http_api.py        # HTTP API user workflows
├── test_sdk.py             # SDK user workflows
├── test_remote_sdk.py      # Remote client workflows (simplified)
└── test_cli.py             # CLI user workflows
```

### Test Categories by Priority

#### 1. Core Logic Tests (HIGHEST Priority - 100% Coverage Required)
**Location:** `tests/core/`  
**Purpose:** Unit test every function in `src/md_server/core/`  
**Coverage Target:** 100% - no exceptions  

**Files to test completely:**
- `src/md_server/core/converter.py` → `tests/core/test_converter.py`
- `src/md_server/core/detection.py` → `tests/core/test_detection.py`  
- `src/md_server/core/security.py` → `tests/core/test_security.py`
- `src/md_server/core/browser.py` → `tests/core/test_browser.py`

**Testing Pattern:**
```python
def test_convert_file_success():
    """Test successful file conversion - happy path."""
    converter = DocumentConverter(test_config)
    result = await converter.convert_file(Path("test.pdf"), {})
    
    assert result.success
    assert result.markdown
    assert result.metadata.source_type == "pdf"

def test_convert_file_not_found():
    """Test file not found error - user error scenario."""
    converter = DocumentConverter(test_config)
    
    with pytest.raises(FileNotFoundError):
        await converter.convert_file(Path("missing.pdf"), {})
```

#### 2. User Workflow Tests (HIGH Priority)
**Location:** Root `tests/` directory  
**Purpose:** Validate complete user journeys  
**Coverage Target:** All user-facing functionality  

**Key User Personas:**
- **HTTP API Users** - Web developers using REST endpoints
- **SDK Users** - Python developers using programmatic interface
- **Remote SDK Users** - Clients connecting to remote servers  
- **CLI Users** - Command-line server management

#### 3. Integration Tests (MEDIUM Priority)
**Purpose:** Verify components work together  
**Focus:** Critical integration points only  
**Performance:** Fast startup, efficient cleanup

---

## Simplified Test Structure

### Core Logic Testing (`tests/core/`)

**Focus:** Every function, every branch, every error condition

```python
# tests/core/test_converter.py
class TestDocumentConverter:
    """Test core document conversion logic - 100% coverage required."""
    
    def test_convert_pdf_success(self):
        """Test PDF conversion success path."""
        # Test main conversion logic
        pass
    
    def test_convert_pdf_corrupted(self):
        """Test corrupted PDF handling."""
        # Test error handling branch
        pass
    
    def test_convert_with_options(self):
        """Test conversion with all option combinations."""
        # Test option processing branches
        pass
    
    def test_convert_timeout(self):
        """Test conversion timeout handling."""
        # Test timeout branch
        pass
```

### User Workflow Testing

#### HTTP API Testing (`test_http_api.py`)
```python
class TestHTTPWorkflows:
    """Test HTTP API from user perspective - key workflows only."""
    
    def test_upload_pdf_file(self, client):
        """Core workflow: Upload PDF file via HTTP."""
        with open("tests/test_data/test.pdf", "rb") as f:
            response = client.post("/convert", content=f.read())
        
        assert response.status_code == 200
        assert response.json()["success"]
        assert "markdown" in response.json()
    
    def test_convert_url_local(self, client, local_test_server):
        """Core workflow: Convert URL via HTTP using local server."""
        test_url = f"{local_test_server}/simple.html"
        response = client.post("/convert", json={"url": test_url})
        
        assert response.status_code == 200
        assert response.json()["success"]
        assert "Test Content" in response.json()["markdown"]  # Expected content
    
    def test_convert_url_with_javascript(self, client, local_test_server):
        """Browser workflow: URL with JavaScript rendering."""
        test_url = f"{local_test_server}/javascript.html"
        response = client.post("/convert", json={
            "url": test_url,
            "options": {"js_rendering": True}
        })
        
        assert response.status_code == 200
        assert response.json()["success"]
    
    def test_convert_url_timeout(self, client, local_test_server):
        """Timeout workflow: URL that responds slowly."""
        test_url = f"{local_test_server}/slow_response.html"
        response = client.post("/convert", json={
            "url": test_url,
            "options": {"timeout": 0.1}  # Very short timeout
        })
        
        assert response.status_code == 408  # Timeout
        assert not response.json()["success"]
    
    def test_invalid_format_error(self, client):
        """Error workflow: Unsupported format handling."""
        response = client.post("/convert", content=b"invalid data")
        
        assert response.status_code == 415  # Unsupported format
        assert not response.json()["success"]
```

#### SDK Testing (`test_sdk.py`)
```python
class TestSDKWorkflows:
    """Test SDK from Python developer perspective."""
    
    async def test_convert_file(self):
        """SDK workflow: Convert local file."""
        converter = MDConverter()
        result = await converter.convert_file("tests/test_data/test.pdf")
        
        assert result.success
        assert result.markdown
    
    def test_convert_file_sync(self):
        """SDK workflow: Synchronous conversion."""
        converter = MDConverter()
        result = converter.convert_file_sync("tests/test_data/test.pdf")
        
        assert result.success
        assert result.markdown
    
    async def test_convert_url_local(self, local_test_server):
        """SDK workflow: Convert URL using local server."""
        converter = MDConverter()
        test_url = f"{local_test_server}/simple.html"
        result = await converter.convert_url(test_url)
        
        assert result.success
        assert "Test Content" in result.markdown
    
    async def test_convert_with_options(self):
        """SDK workflow: Conversion with options."""
        converter = MDConverter()
        result = await converter.convert_file(
            "tests/test_data/test.pdf",
            ocr_enabled=True,
            extract_images=True
        )
        
        assert result.success
        assert "ocr_enabled" in result.metadata.options_used
```

#### Remote SDK Testing (`test_remote_sdk.py`)
**Simplified:** Focus on connection and basic functionality only

```python
class TestRemoteSDKWorkflows:
    """Test remote SDK - basic functionality only."""
    
    async def test_remote_convert_file(self, test_server):
        """Remote workflow: Convert file via API."""
        client = RemoteMDConverter(f"http://localhost:{test_server.port}")
        result = await client.convert_file("tests/test_data/test.pdf")
        
        assert result.success
    
    async def test_remote_convert_url_local(self, test_server, local_test_server):
        """Remote workflow: Convert URL via remote API using local content."""
        client = RemoteMDConverter(f"http://localhost:{test_server.port}")
        test_url = f"{local_test_server}/simple.html"
        result = await client.convert_url(test_url)
        
        assert result.success
        assert "Test Content" in result.markdown
    
    async def test_remote_network_error(self):
        """Remote workflow: Handle connection errors."""
        client = RemoteMDConverter("http://127.0.0.1:1")  # Invalid port
        
        with pytest.raises(httpx.ConnectError):
            await client.convert_file("tests/test_data/test.pdf")
```

---

## Performance & Simplicity Guidelines

### Test Speed Targets
- **Core tests:** <10ms each (pure functions, no I/O)
- **SDK tests:** <100ms each (minimal I/O)  
- **HTTP tests:** <1s each (real server, fast cleanup)
- **Total suite:** <2 minutes (down from 10+ minutes)

### Fast Test Patterns

#### Use Real Files, Skip Complex Mocking
```python
# GOOD: Use real test files
def test_convert_pdf():
    result = convert_file("tests/test_data/test.pdf")
    assert result.success

# AVOID: Complex mocking that's slower than real operations
def test_convert_pdf_mocked():
    with patch("markitdown.convert") as mock:
        mock.return_value = MockResult()
        # Complex mock setup slower than real conversion
```

#### Direct Function Testing
```python  
# GOOD: Test functions directly
def test_detect_content_type():
    content_type = detect_content_type(pdf_bytes)
    assert content_type == "application/pdf"

# AVOID: Testing through multiple layers
def test_detect_content_type_via_controller():
    # Tests too many things at once, slower, harder to debug
```

#### Minimal Server Startup
```python
# GOOD: Single server for all HTTP tests
@pytest.fixture(scope="module")
def test_server():
    with TestServer() as server:
        yield server

# AVOID: Server per test (adds 15s+ per test)
```

---

## Code Coverage Strategy

### 100% Core Coverage (Non-Negotiable)
Every function in `src/md_server/core/` must be tested:

```bash
# Coverage commands
uv run pytest tests/core/ --cov=src/md_server/core --cov-report=html --cov-fail-under=100

# Should show:
# src/md_server/core/converter.py     100%
# src/md_server/core/detection.py     100%  
# src/md_server/core/security.py      100%
# src/md_server/core/browser.py       100%
# TOTAL                               100%
```

### Coverage Enforcement
- **CI Requirement:** 100% core coverage to pass
- **Pre-commit Hook:** Run coverage check locally
- **Coverage Reports:** Generate HTML reports for review

### Coverage Patterns
```python
def test_all_branches():
    """Test ensures 100% branch coverage."""
    
    # Test success path
    result = function_under_test(valid_input)
    assert result.success
    
    # Test each error condition
    with pytest.raises(SpecificError):
        function_under_test(invalid_input_type_1)
    
    with pytest.raises(AnotherError):
        function_under_test(invalid_input_type_2)
    
    # Test edge cases
    result = function_under_test(edge_case_input)
    assert result.handled_edge_case
```

---

## Test Data & Fixtures

### Preserved Test Assets (`tests/test_data/`)
Keep existing real file samples:
- `test.pdf` - PDF document conversion  
- `test.docx` - Office document processing
- `test_blog.html` - Web content structure
- `test.jpg` - Image with OCR potential
- `test.json` - Structured data conversion

### Local Test Server (`tests/test_server/`)
Replace external URL calls with local test server:
- `simple.html` - Basic HTML content for URL conversion tests
- `javascript.html` - HTML with JS for browser testing
- `large.html` - Larger content for performance testing
- `malformed.html` - Invalid HTML for error testing
- `slow_response.html` - Simulated slow response (with delay)

### Simple Fixtures
```python
@pytest.fixture
def test_config():
    """Minimal test configuration."""
    return Settings(
        debug=True,
        max_file_size=10_000_000,
        timeout_seconds=30
    )

@pytest.fixture  
def converter(test_config):
    """Document converter with test config."""
    return DocumentConverter(test_config)

@pytest.fixture(scope="module")
def test_files():
    """Test file paths."""
    return {
        "pdf": Path("tests/test_data/test.pdf"),
        "docx": Path("tests/test_data/test.docx"),
        "html": Path("tests/test_data/test_blog.html"),
        "jpg": Path("tests/test_data/test.jpg"),
    }

@pytest.fixture(scope="module")
def local_test_server():
    """Fast local HTTP server for URL testing."""
    import threading
    import http.server
    import socketserver
    from pathlib import Path
    
    # Serve files from tests/test_server/
    test_server_dir = Path("tests/test_server")
    
    class TestHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(test_server_dir), **kwargs)
        
        def do_GET(self):
            # Add delay for slow_response.html
            if self.path.endswith('slow_response.html'):
                import time
                time.sleep(0.5)  # Predictable 500ms delay
            super().do_GET()
    
    # Start server on random available port
    with socketserver.TCPServer(("", 0), TestHandler) as server:
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        
        yield f"http://localhost:{port}"
        
        server.shutdown()
```

---

## Migration Plan

### Phase 1: Delete & Reset
1. **Move current tests:** `tests/` → `tests.bak/`
2. **Keep test data:** Preserve `tests/test_data/` directory
3. **Create test server directory:** `tests/test_server/` with HTML files
4. **Clean slate:** Start with empty `tests/` directory for new tests

### Phase 2: Core Coverage First  
1. **Create `tests/core/`** directory
2. **Write core tests** with 100% coverage requirement
3. **Validate coverage** before proceeding

### Phase 3: User Workflow Tests
1. **Create user workflow tests** in root `tests/`
2. **Focus on key scenarios** only
3. **Optimize for speed** and reliability

### Phase 4: Integration & Polish
1. **Add minimal integration tests**
2. **Optimize test performance**
3. **Validate total runtime <2 minutes**

---

## Success Metrics

### Quantitative Goals
- [ ] **100% code coverage** of `src/md_server/core/`
- [ ] **Test suite completes** in <2 minutes  
- [ ] **Zero test failures** in CI
- [ ] **<20 total test files** (down from 26)
- [ ] **<200 total tests** (down from 537)

### Qualitative Goals
- [ ] **Tests are readable** by new developers
- [ ] **Test failures are obvious** to debug
- [ ] **Adding tests is trivial** for new features
- [ ] **Tests serve as documentation** of user workflows

---

## Maintenance Guidelines

### Adding New Features
1. **Write core tests first** - ensure 100% coverage
2. **Add user workflow test** - validate end-to-end usage  
3. **Run performance check** - maintain <2 minute total
4. **Update this doc** if testing approach changes

### Test Quality Checks
- **Test names are user scenarios** - not implementation details
- **Each test validates one thing** - clear pass/fail criteria
- **Error scenarios are realistic** - what users actually encounter
- **Setup/teardown is minimal** - fast and reliable

---

## Examples of Good vs Bad Tests

### ✅ Good: User-Focused, Fast, Clear
```python
def test_convert_large_pdf():
    """User workflow: Convert large PDF file under size limit."""
    large_pdf = create_test_pdf(size_mb=5)  # Under 10MB limit
    
    converter = MDConverter()
    result = converter.convert_file_sync(large_pdf)
    
    assert result.success
    assert len(result.markdown) > 100

def test_convert_oversized_pdf():
    """User error: PDF exceeds size limit."""
    huge_pdf = create_test_pdf(size_mb=50)  # Over 10MB limit
    
    converter = MDConverter()
    
    with pytest.raises(FileSizeError, match="File too large"):
        converter.convert_file_sync(huge_pdf)
```

### ❌ Bad: Implementation-Focused, Complex, Slow
```python
def test_markitdown_integration_with_retry_logic_and_error_mapping():
    """Complex test that tests too many things."""
    with patch("markitdown.MarkItDown") as mock_md:
        with patch("sdk.core.utils.should_retry_request") as mock_retry:
            with patch("sdk.core.remote.map_status_code_to_exception") as mock_map:
                # 50 lines of complex mocking
                # Tests implementation details
                # Breaks when refactoring
                # Slow to run
                # Hard to understand what's actually being tested
```

---

This simplified testing approach will ensure **100% code coverage** while making tests **fast, reliable, and easy to maintain**. The focus on user workflows ensures we're testing what actually matters while the core coverage ensures no bugs slip through.