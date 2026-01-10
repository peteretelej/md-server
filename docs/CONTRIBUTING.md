# Contributing to md-server

## Table of Contents

- [Development Setup](#development-setup)
- [Running Locally](#running-locally)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Development Workflow](#development-workflow)
- [Enhanced URL Conversion](#enhanced-url-conversion-optional)
- [Docker](#docker)
- [Publishing New Version](#publishing-new-version)
- [Project Structure](#project-structure)
- [Debugging](#debugging)

## Development Setup

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager

### Setup

```bash
git clone https://github.com/peteretelej/md-server.git
cd md-server
uv sync

# Optional: Install Playwright browsers for enhanced URL conversion
uv run playwright install chromium
```

## Running Locally

```bash
# Development server
uv run python -m md_server

# Custom host/port
uv run python -m md_server --host 0.0.0.0 --port 9000

# With environment variables
cp .env.example .env  # Edit as needed
uv run python -m md_server
```

API docs: http://localhost:8080/docs

## Testing

```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov=md_server --cov-report=html

# Specific markers
uv run pytest -m unit
uv run pytest -m integration
uv run pytest -m slow
```

## Code Quality

```bash
# Lint and format
uv run ruff check
uv run ruff check --fix
uv run ruff format

# Pre-commit checks
uv run ruff check && uv run ruff format --check && uv run pytest

# Use pre-push script
./scripts/pre-push
```

## Development Workflow

1. Create feature branch: `git checkout -b feature/name`
2. Make changes, add tests
3. Run quality checks: `./scripts/pre-push`
4. Commit and push
5. Create pull request

### Git Hooks

Install the pre-push hook to run checks automatically:

```bash
ln -sf ./scripts/pre-push .git/hooks/pre-push
```

### Coding Standards

- Use type hints
- Follow Litestar patterns
- Use Pydantic models for validation
- Prefer async/await for I/O
- Self-documenting code

## Enhanced URL Conversion (Optional)

By default, md-server uses MarkItDown for URL conversion, which works well for most websites. For JavaScript-heavy sites, you can enable enhanced conversion:

### Install Playwright Browsers

```bash
uvx playwright install-deps
uvx playwright install chromium
```

### Benefits of Browser-Based Conversion

- **JavaScript rendering**: Properly handles dynamic content
- **Better extraction**: More accurate content from modern web apps
- **Enhanced crawling**: Advanced page interaction capabilities

### Verification

Restart the server to see the conversion mode:

```bash
uv run python -m md_server
# With browsers: "URL Conversion: Using Crawl4AI with Playwright browsers"
# Without browsers: "URL Conversion: Playwright browsers not available, falling back to MarkItDown"
```

## Dependencies

```bash
# Runtime
uv add package-name

# Development
uv add --dev package-name
```

## Docker

The Docker image includes browser support for JavaScript rendering:

```bash
docker build -t md-server .
docker run -p 8080:8080 --env-file .env ghcr.io/peteretelej/md-server
```

**Resource Requirements:**
- Memory: 1GB recommended for browser operations
- Build time: 5-10 minutes (includes Playwright browsers)
- Image size: ~1.2GB

## Publishing New Version

1. Update version in `pyproject.toml`
2. Commit: `git commit -m "Bump version to x.y.z"`
3. Tag and push:
   ```bash
   git tag vx.y.z
   git push origin main
   git push origin vx.y.z
   ```

CI/CD handles PyPI publishing, GitHub releases, and Docker images automatically.

### Versioning

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features
- **PATCH**: Bug fixes

## Project Structure

```
src/md_server/
├── __main__.py         # CLI entry
├── app.py              # Litestar app
├── controllers.py      # API handlers
├── converter.py        # Conversion logic
├── models.py           # Pydantic models
└── core/
    ├── __init__.py
    └── config.py       # Settings
```

## Debugging

```bash
# Debug mode
MD_SERVER_DEBUG=true uv run python -m md_server

# Different port
uv run python -m md_server --port 9000

# Increase timeout
MD_SERVER_TIMEOUT_SECONDS=60 uv run python -m md_server
```

## Help

- [GitHub Issues](https://github.com/peteretelej/md-server/issues)
- [API Documentation](API.md)
- [Configuration Reference](configuration.md)
- [Design Document](design.md)
