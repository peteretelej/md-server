# Contributing to md-server

## Development Setup

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager

### Setup

```bash
git clone https://github.com/peteretelej/md-server.git
cd md-server
uv sync
uv run playwright install
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
- Follow FastAPI patterns
- Use Pydantic models for validation
- Prefer async/await for I/O
- Self-documenting code

## Dependencies

```bash
# Runtime
uv add package-name

# Development
uv add --dev package-name
```

## Docker

```bash
docker build -t md-server .
docker run -p 8080:8080 --env-file .env md-server
```

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
├── app.py              # FastAPI app
├── controllers.py      # API handlers
├── converter.py        # Conversion logic
├── models.py           # Pydantic models
├── core/config.py      # Settings
└── middleware/auth.py  # Auth middleware
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
- [Design Document](design.md)
