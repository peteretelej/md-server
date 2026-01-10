FROM python:3.11-slim-bookworm

# Install essential tools (ffmpeg, curl)
RUN apt-get update && apt-get install -y \
    curl ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY src/ ./src/

RUN uv sync --frozen --no-dev

# Install Chromium browser and system dependencies in one command
# --with-deps installs both browser binaries AND required system libraries
RUN uv run playwright install --with-deps chromium

EXPOSE 8080

ENV PYTHONPATH=/app/src
ENV UV_PROJECT_ENVIRONMENT=/app/.venv

CMD ["uv", "run", "--no-sync", "python", "-m", "md_server", "--host", "0.0.0.0", "--port", "8080"]