# MCP Integration Guide

md-server works directly with AI tools via [Model Context Protocol (MCP)](https://modelcontextprotocol.io). This lets Claude Desktop, Cursor, and other AI tools convert documents and read web pages without any HTTP setup.

## Table of Contents

- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Transport Modes](#transport-modes)
- [The Convert Tool](#the-convert-tool)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Claude Desktop

Add to your Claude Desktop configuration:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

**Linux:** `~/.config/Claude/claude_desktop_config.json`

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "md-server": {
      "command": "uvx",
      "args": ["md-server[mcp]", "--mcp-stdio"]
    }
  }
}
```

Restart Claude Desktop after saving.

### Cursor

Cursor uses the same configuration format. Add the same JSON to your Cursor MCP settings.

### Using Docker

If you prefer Docker:

```json
{
  "mcpServers": {
    "md-server": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "ghcr.io/peteretelej/md-server", "--mcp-stdio"]
    }
  }
}
```

## Configuration

### Installation Options

```bash
# UVX (recommended - no installation needed)
uvx md-server[mcp] --mcp-stdio

# pip installation
pip install md-server[mcp]
python -m md_server --mcp-stdio

# Docker
docker run -i --rm ghcr.io/peteretelej/md-server --mcp-stdio
```

### Environment Variables

MCP mode respects the same environment variables as the HTTP server:

| Variable | Default | Description |
|----------|---------|-------------|
| `MD_SERVER_CONVERSION_TIMEOUT` | 120 | Conversion timeout in seconds |
| `MD_SERVER_MAX_FILE_SIZE` | 52428800 | Maximum file size in bytes |
| `MD_SERVER_ALLOW_LOCALHOST` | true | Allow localhost URLs |
| `MD_SERVER_ALLOW_PRIVATE_NETWORKS` | false | Allow private IP ranges |

See [Configuration](configuration.md) for the complete list.

## Transport Modes

### stdio (Local AI Tools)

For local AI tools like Claude Desktop and Cursor that communicate via stdin/stdout:

```bash
uvx md-server[mcp] --mcp-stdio
```

This is the default mode for MCP integration.

### SSE (Network Agents)

For network-based AI agents that connect over HTTP:

```bash
uvx md-server[mcp] --mcp-sse --port 9000
```

Endpoints:
- `GET /health` - Health check
- `GET /sse` - SSE connection endpoint
- `POST /messages` - Message endpoint

## The Convert Tool

When integrated, your AI gets access to the `convert` tool.

### Tool Schema

```json
{
  "name": "convert",
  "description": "Convert a document, URL, or text to Markdown. Supports PDF, DOCX, XLSX, PPTX, HTML, images, and more.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "url": {
        "type": "string",
        "description": "URL to fetch and convert"
      },
      "content": {
        "type": "string",
        "description": "Base64-encoded file content"
      },
      "text": {
        "type": "string",
        "description": "Raw text or HTML to convert"
      },
      "filename": {
        "type": "string",
        "description": "Filename hint for format detection"
      },
      "js_rendering": {
        "type": "boolean",
        "default": false,
        "description": "Enable JavaScript rendering for dynamic web pages"
      },
      "ocr_enabled": {
        "type": "boolean",
        "default": false,
        "description": "Enable OCR for images and scanned PDFs"
      },
      "include_frontmatter": {
        "type": "boolean",
        "default": false,
        "description": "Include YAML frontmatter with metadata"
      }
    },
    "oneOf": [
      {"required": ["url"]},
      {"required": ["content"]},
      {"required": ["text"]}
    ]
  }
}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | string | One of three | URL to fetch and convert |
| `content` | string | One of three | Base64-encoded file content |
| `text` | string | One of three | Raw text or HTML to convert |
| `filename` | string | No | Filename hint (e.g., "report.pdf") |
| `js_rendering` | boolean | No | Enable JavaScript rendering |
| `ocr_enabled` | boolean | No | Enable OCR for images/scanned docs |
| `include_frontmatter` | boolean | No | Add YAML metadata header |

You must provide exactly one of: `url`, `content`, or `text`.

## Examples

Once configured, your AI can convert documents directly:

### Reading Web Pages

> "Read the Python asyncio documentation and summarize it"

> "Convert this webpage to markdown: https://example.com/article"

### Converting Documents

> "What's in this PDF?" *(with file attached)*

> "Summarize the key points from this Word document"

### JavaScript-Heavy Sites

> "Read this React documentation page with JavaScript rendering enabled"

The AI will use `js_rendering: true` for dynamic content.

### OCR for Images

> "Extract the text from this screenshot"

The AI will use `ocr_enabled: true` for images and scanned documents.

### With Metadata

> "Convert this page and include metadata in the output"

The AI will use `include_frontmatter: true` to add YAML headers.

## Troubleshooting

### "MCP dependencies not installed"

Install the MCP extras:

```bash
pip install md-server[mcp]
# or
uvx md-server[mcp] --mcp-stdio
```

### Tool not appearing in Claude Desktop

1. Verify the configuration file path is correct for your OS
2. Check the JSON syntax is valid
3. Restart Claude Desktop completely (quit and reopen)
4. Check Claude Desktop logs for errors

### JavaScript sites return empty content

1. Ensure Playwright browsers are installed:
   ```bash
   uvx playwright install chromium
   ```
2. Use `js_rendering: true` in the tool call

### URL blocked by SSRF protection

Private IPs and localhost are blocked by default. For development:

```bash
export MD_SERVER_ALLOW_LOCALHOST=true
export MD_SERVER_ALLOW_PRIVATE_NETWORKS=true
```

### SSE connection failing

1. Check the host and port are accessible
2. Verify no firewall is blocking the connection
3. Ensure the server started successfully

### Large files timing out

Increase the conversion timeout:

```bash
export MD_SERVER_CONVERSION_TIMEOUT=300
```

## See Also

- [API Reference](API.md) - HTTP API documentation
- [Configuration](configuration.md) - All environment variables
- [Python SDK](sdk/README.md) - Library usage
