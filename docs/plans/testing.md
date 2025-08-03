# Testing Plan

Testing strategy for md-server focused on integration tests with content validation.

## Testing Structure

```
tests/
├── test_data/               # Test files and fixtures from markitdown test suite
│   ├── test.pdf            # PDF document
│   ├── test.docx           # Word document
│   ├── equations.docx      # Word with equations
│   ├── test_with_comment.docx # Word with comments
│   ├── test.pptx           # PowerPoint presentation
│   ├── test.xlsx           # Excel spreadsheet
│   ├── test.epub           # EPUB ebook
│   ├── test.jpg            # Image file
│   ├── test_blog.html      # HTML blog content
│   ├── test_wikipedia.html # Complex HTML content
│   └── conftest.py         # Pytest fixtures
├── unit/                   # Unit tests for isolated components
│   ├── test_config.py
│   ├── test_markitdown_adapter.py
│   └── test_exceptions.py
└── integration/            # API integration tests (primary coverage)
    ├── test_health_api.py
    ├── test_convert_file_api.py
    └── test_convert_url_api.py
```

## Test Categories

**Integration Tests (Primary):** All API endpoints with content validation  
**Unit Tests (Selective):** Config, adapter, exceptions

## Implementation Phases

### Phase 1: Test Infrastructure Setup

- [x] Add test dependencies: `uv add --dev pytest-asyncio pytest-cov httpx`
- [x] Configure pytest in pyproject.toml
- [x] Set up coverage configuration  
- [x] Create tests/test_data/conftest.py with fixtures
- [x] Add test vectors for file validation
- [x] Test pytest runs: `uv run pytest --version`

**pyproject.toml additions:**
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "--strict-markers --strict-config"
markers = [
    "unit: Unit tests",
    "integration: Integration tests", 
    "slow: Slow tests"
]

[tool.coverage.run]
source = ["src"]
omit = ["tests/*", "src/md_server/__main__.py"]
```

### Phase 2: Core Unit Tests

- [x] Create tests/unit/test_config.py
  - [x] Test settings initialization and defaults
  - [x] Test environment variable overrides
  - [x] Test file type/size validation
- [x] Create tests/unit/test_markitdown_adapter.py  
  - [x] Test adapter initialization with configs
  - [x] Test timeout and retry logic
  - [x] Test error handling and exception mapping
  - [x] Test health check functionality
- [x] Create tests/unit/test_exceptions.py
  - [x] Test custom exception types and messages
  - [x] Test exception inheritance
- [x] Run unit tests: `uv run pytest tests/unit/ -v`

### Phase 3: Integration Test Suite

- [x] Create tests/integration/test_health_api.py
  - [x] Test GET /healthz endpoint 
  - [x] Test response format validation
  - [x] Test service availability checking
- [x] Create tests/integration/test_convert_file_api.py
  - [x] Test POST /convert with file uploads
  - [x] Test supported file types using test vectors
  - [x] Test file size limits and error responses
  - [x] Test content validation (must_include/must_not_include)
  - [x] Test timeout handling for large files
- [x] Create tests/integration/test_convert_url_api.py
  - [x] Test POST /convert/url endpoint
  - [x] Test URL validation and sanitization
  - [x] Test content validation for web content
  - [x] Test error handling for invalid URLs
  - [x] Test network timeout scenarios
- [x] Run integration tests: `uv run pytest tests/integration/ -v`

### Phase 4: Test Data and Fixtures

- [x] Update tests/test_data/conftest.py with test vectors
  - [x] Create FileTestVector dataclass
  - [x] Add test vectors for PDF, DOCX, PPTX, HTML files
  - [x] Add FastAPI test client fixture
  - [x] Add mock configuration fixtures
- [x] Verify test files are available (already copied from markitdown)
- [x] Test fixtures work: `uv run pytest tests/test_data/ -v`

**Key test files:** PDF, DOCX, PPTX, HTML, images, audio, unsupported formats

### Phase 5: Coverage and CI/CD Integration

- [x] Set up coverage configuration in pyproject.toml
- [x] Run tests with coverage: `uv run pytest --cov=src --cov-report=term-missing`
- [x] Create .github/workflows/ci.yml with Python CI pipeline
- [x] Add Ollama setup for LLM functionality testing
- [x] Configure codecov integration
- [x] Test CI pipeline runs successfully
- [x] Verify 85% coverage target achieved

**CI/CD Pipeline (.github/workflows/ci.yml):**
```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  # Fast checks first
  lint-and-type:
    name: Lint and Type Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install uv
        uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true
          cache-dependency-glob: "uv.lock"
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      
      - name: Install dependencies
        run: uv sync --dev
      
      - name: Run type checking
        run: uv run mypy src
      
      - name: Run linting
        run: uv run ruff check .
      
      - name: Check formatting
        run: uv run ruff format --check

  # Unit tests - no external services
  test-unit:
    name: Unit Tests
    runs-on: ${{ matrix.os }}
    needs: lint-and-type
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ["3.10", "3.11", "3.12"]
        exclude:
          # Reduce matrix on non-Linux to save resources
          - os: macos-latest
            python-version: "3.10"
          - os: windows-latest
            python-version: "3.12"
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Install uv
        uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true
          cache-dependency-glob: "uv.lock"
      
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: uv sync --dev
      
      - name: Run unit tests
        run: uv run pytest tests/unit/ -v --tb=short

  # Integration tests with LLM services
  test-integration:
    name: Integration Tests & Coverage
    runs-on: ubuntu-latest
    needs: [lint-and-type, test-unit]
    # Only run on main branch, PRs to main, or when forced
    if: >
      (github.event_name == 'push' && github.ref == 'refs/heads/main') ||
      (github.event_name == 'pull_request' && github.base_ref == 'main') ||
      contains(github.event.head_commit.message, '[integration]')

    steps:
      - uses: actions/checkout@v4
      
      - name: Install uv
        uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true
          cache-dependency-glob: "uv.lock"
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      
      - name: Cache Ollama models
        uses: actions/cache@v4
        with:
          path: /tmp/ollama-models
          key: ollama-models-${{ hashFiles('.github/workflows/ci.yml') }}-v1
          restore-keys: |
            ollama-models-
      
      - name: Setup Ollama for AI functionality testing
        run: |
          # Create directories for caching
          mkdir -p /tmp/ollama-models
          
          # Start Ollama with model volume mounted
          echo "Starting Ollama..."
          docker run -d --name ollama \
            -p 11434:11434 \
            -v /tmp/ollama-models:/root/.ollama \
            -e OLLAMA_HOST=0.0.0.0 \
            ollama/ollama:latest
          
          # Wait for Ollama
          echo "Waiting for Ollama..."
          timeout 180 bash -c 'until curl -f http://localhost:11434/api/tags; do echo "  Ollama not ready, waiting..."; sleep 5; done'
          echo "✅ Ollama is ready!"
          
          # Check if model is already cached, pull if needed
          if [ -f "/tmp/ollama-models/models/manifests/registry.ollama.ai/library/llama2/latest" ]; then
            echo "✅ llama2:7b model found in cache"
          else
            echo "Pulling llama2:7b model..."
            curl -X POST http://localhost:11434/api/pull -d '{"name":"llama2:7b"}' --max-time 600
            echo "✅ Model pull completed"
          fi
      
      - name: Install dependencies
        run: uv sync --dev
      
      - name: Run all tests with coverage
        run: |
          uv run pytest --cov=src --cov-report=xml --cov-report=term-missing -v
        env:
          OLLAMA_ENDPOINT: http://localhost:11434
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
          flags: alltests
          name: codecov-umbrella
          fail_ci_if_error: false
        env:
          CODECOV_TOKEN: ${{ secrets.CODECOV_TOKEN }}
      
      - name: Upload test results to Codecov
        uses: codecov/test-results-action@v1
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
      
      - name: Cleanup containers
        if: always()
        run: |
          docker stop ollama || true
          docker rm ollama || true

  # Server startup test
  test-server-startup:
    name: Server Startup Test
    runs-on: ubuntu-latest
    needs: test-unit

    steps:
      - uses: actions/checkout@v4
      
      - name: Install uv
        uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true
          cache-dependency-glob: "uv.lock"
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      
      - name: Install dependencies
        run: uv sync --dev
      
      - name: Test server startup
        run: |
          timeout 5s uv run python -m md_server --port 9999 || exit_code=$?
          if [ "${exit_code:-0}" -eq 124 ]; then
            echo "✓ Server started successfully (timeout expected)"
            exit 0
          elif [ "${exit_code:-0}" -eq 0 ]; then
            echo "✓ Server started and exited cleanly"
            exit 0
          else
            echo "✗ Server failed to start (exit code: ${exit_code:-0})"
            exit 1
          fi
```

### Phase 6: Final Testing and Validation

- [ ] Run full test suite: `uv run pytest -v`
- [ ] Run tests with coverage: `uv run pytest --cov=src --cov-report=term-missing`
- [ ] Test server startup: `uv run python -m md_server --port 9999`
- [ ] Verify all API endpoints work with real requests
- [ ] Run linting: `uv run ruff check .`
- [ ] Run type checking: `uv run mypy src`
- [ ] Commit test implementation
- [ ] Create and test CI/CD pipeline

## Key Principles

- **Content validation:** Use test vectors with must_include/must_not_include patterns
- **Integration focus:** Primary coverage through API endpoint testing  
- **Real test data:** Use markitdown test files for realistic scenarios
- **85% coverage target:** Balance between thoroughness and maintainability
- **Fast feedback:** Unit tests run quickly, integration tests on PR/main only
- **CI/CD:** Automated testing with Ollama for LLM functionality