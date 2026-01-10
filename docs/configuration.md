# Configuration Reference

All md-server settings can be configured via environment variables. Variables use the `MD_SERVER_` prefix.

## Table of Contents

- [Server Settings](#server-settings)
- [Limits and Timeouts](#limits-and-timeouts)
- [Security](#security)
- [Crawl4AI Settings](#crawl4ai-settings)
- [Proxy Settings](#proxy-settings)
- [LLM Integration](#llm-integration)
- [Azure Document Intelligence](#azure-document-intelligence)
- [Example Configuration](#example-configuration)

## Server Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `MD_SERVER_HOST` | string | `127.0.0.1` | Server bind address |
| `MD_SERVER_PORT` | int | `8080` | Server port |
| `MD_SERVER_API_KEY` | string | None | API key for authentication (see [Security](#security)) |
| `MD_SERVER_DEBUG` | bool | `false` | Enable debug mode |

## Limits and Timeouts

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `MD_SERVER_MAX_FILE_SIZE` | int | `52428800` | Maximum file size in bytes (50 MB) |
| `MD_SERVER_TIMEOUT_SECONDS` | int | `30` | General timeout in seconds |
| `MD_SERVER_URL_FETCH_TIMEOUT` | int | `30` | URL fetch timeout in seconds |
| `MD_SERVER_CONVERSION_TIMEOUT` | int | `120` | Conversion timeout in seconds |
| `MD_SERVER_BROWSER_TIMEOUT` | int | `90` | Browser operations timeout (JS rendering) |
| `MD_SERVER_OCR_TIMEOUT` | int | `120` | OCR operations timeout in seconds |

## Security

### API Key Authentication

When `MD_SERVER_API_KEY` is set, all requests (except `/health`) require the `Authorization` header:

```bash
export MD_SERVER_API_KEY="your-secret-key"
uvx md-server
```

Requests must include the header:

```bash
curl -X POST localhost:8080/convert \
  -H "Authorization: Bearer your-secret-key" \
  --data-binary @document.pdf
```

### SSRF Protection

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `MD_SERVER_ALLOW_LOCALHOST` | bool | `true` | Allow localhost URLs (127.x, ::1) |
| `MD_SERVER_ALLOW_PRIVATE_NETWORKS` | bool | `false` | Allow private IPs (10.x, 172.16.x, 192.168.x) and cloud metadata |

By default, md-server blocks:
- Private IP ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
- Cloud metadata endpoints (169.254.169.254)
- Link-local addresses

To allow private networks (for development):

```bash
export MD_SERVER_ALLOW_PRIVATE_NETWORKS=true
```

## Crawl4AI Settings

These settings control web page fetching and JavaScript rendering.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `MD_SERVER_CRAWL4AI_JS_RENDERING` | bool | `false` | Enable JavaScript rendering by default |
| `MD_SERVER_CRAWL4AI_TIMEOUT` | int | `30` | Page load timeout in seconds |
| `MD_SERVER_CRAWL4AI_USER_AGENT` | string | None | Custom user agent string |

JavaScript rendering requires Playwright browsers:

```bash
uvx playwright install chromium
```

Docker images include browsers automatically.

## Proxy Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `MD_SERVER_HTTP_PROXY` | string | None | HTTP proxy URL |
| `MD_SERVER_HTTPS_PROXY` | string | None | HTTPS proxy URL |

Example:

```bash
export MD_SERVER_HTTP_PROXY="http://proxy.example.com:8080"
export MD_SERVER_HTTPS_PROXY="http://proxy.example.com:8080"
```

## LLM Integration

Optional LLM integration for enhanced document processing.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `MD_SERVER_LLM_PROVIDER_URL` | string | None | LLM provider endpoint |
| `MD_SERVER_LLM_API_KEY` | string | None | LLM API key |
| `MD_SERVER_LLM_MODEL` | string | `google/gemini-2.5-flash` | LLM model identifier |
| `MD_SERVER_OPENAI_API_KEY` | string | None | OpenAI API key for image descriptions |

Example with OpenRouter:

```bash
export MD_SERVER_LLM_PROVIDER_URL="https://openrouter.ai/api/v1"
export MD_SERVER_LLM_API_KEY="your-openrouter-key"
export MD_SERVER_LLM_MODEL="anthropic/claude-3-haiku"
```

## Azure Document Intelligence

For enhanced PDF and document processing using Azure AI.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `MD_SERVER_AZURE_DOC_INTEL_ENDPOINT` | string | None | Azure Document Intelligence endpoint |
| `MD_SERVER_AZURE_DOC_INTEL_KEY` | string | None | Azure Document Intelligence API key |

## Example Configuration

### Basic `.env` file

```bash
# Server
MD_SERVER_HOST=0.0.0.0
MD_SERVER_PORT=8080
MD_SERVER_API_KEY=your-secret-api-key

# Limits
MD_SERVER_MAX_FILE_SIZE=104857600
MD_SERVER_TIMEOUT_SECONDS=60

# Web scraping
MD_SERVER_CRAWL4AI_JS_RENDERING=true
MD_SERVER_CRAWL4AI_TIMEOUT=60
```

### Production `.env` file

```bash
# Server
MD_SERVER_HOST=0.0.0.0
MD_SERVER_PORT=8080
MD_SERVER_API_KEY=your-production-api-key
MD_SERVER_DEBUG=false

# Limits
MD_SERVER_MAX_FILE_SIZE=52428800
MD_SERVER_TIMEOUT_SECONDS=30
MD_SERVER_CONVERSION_TIMEOUT=120

# Security
MD_SERVER_ALLOW_LOCALHOST=false
MD_SERVER_ALLOW_PRIVATE_NETWORKS=false

# Proxy (if needed)
MD_SERVER_HTTP_PROXY=http://proxy.internal:8080
MD_SERVER_HTTPS_PROXY=http://proxy.internal:8080
```

### Docker Compose

```yaml
version: '3.8'
services:
  md-server:
    image: ghcr.io/peteretelej/md-server
    ports:
      - "8080:8080"
    environment:
      - MD_SERVER_HOST=0.0.0.0
      - MD_SERVER_API_KEY=${MD_SERVER_API_KEY}
      - MD_SERVER_CRAWL4AI_JS_RENDERING=true
```

## See Also

- [API Reference](API.md) - HTTP endpoints and options
- [MCP Guide](mcp-guide.md) - AI tool integration
- [Troubleshooting](troubleshooting.md) - Common issues
