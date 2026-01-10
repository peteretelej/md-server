FROM python:3.11-slim

# Install essential tools (ffmpeg, curl)
RUN apt-get update && apt-get install -y \
    curl ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY src/ ./src/

RUN uv sync --frozen --no-dev

# Install Chromium browser and its system dependencies
# install-deps needs apt-get, so we update, install deps, then clean up
RUN uv run playwright install chromium \
    && apt-get update \
    && uv run playwright install-deps chromium \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 8080

ENV PYTHONPATH=/app/src
ENV UV_PROJECT_ENVIRONMENT=/app/.venv

CMD ["uv", "run", "--no-sync", "python", "-m", "md_server", "--host", "0.0.0.0", "--port", "8080"]