FROM python:3.11-slim

# System dependencies for browsers and existing tools
RUN apt-get update && apt-get install -y \
    # Browser system dependencies
    libnss3 libnspr4 libatk-bridge2.0-0 libdrm2 \
    libxkbcommon0 libxss1 libasound2 libatspi2.0-0 \
    libgtk-3-0 libgbm1 \
    # Existing dependencies
    curl ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY src/ ./src/

RUN uv sync --frozen --no-dev

# Install browsers after dependencies but before final layer
RUN uv run playwright install chromium
RUN uv run playwright install-deps

EXPOSE 8080

ENV PYTHONPATH=/app/src
ENV UV_PROJECT_ENVIRONMENT=/app/.venv

CMD ["uv", "run", "--no-sync", "python", "-m", "md_server", "--host", "0.0.0.0", "--port", "8080"]