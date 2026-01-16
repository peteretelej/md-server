# MCP Guide

md-server works directly with AI tools via [Model Context Protocol (MCP)](https://modelcontextprotocol.io). This lets Claude Desktop, Cursor, and other AI tools read documents and web pages without any HTTP setup.

## Quick Start

**Prerequisites:** [uv](https://docs.astral.sh/uv/getting-started/installation/)

> **Tip:** Many AI tools can install MCP servers directly. Try asking your AI assistant to "install the md-server MCP" or use your tool's MCP installation feature.

### Manual Configuration

Add md-server to your MCP settings:

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

Restart your AI tool after saving.

For JavaScript-rendered pages, install browsers: `uvx playwright install --with-deps chromium`

### Docker

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

## The `read_resource` Tool

Once configured, your AI gets access to the **`read_resource`** tool which reads URLs or files and converts them to markdown.

### Input Options

Provide **one** of:
- `url` — Webpage, online PDF, or document URL
- `file_content` + `filename` — Base64-encoded file with its filename

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | string | - | URL to fetch |
| `file_content` | string | - | Base64-encoded file data |
| `filename` | string | - | Filename with extension (required with file_content) |
| `render_js` | boolean | false | Execute JavaScript before reading (URLs only) |
| `max_length` | integer | - | Maximum characters to return |
| `max_tokens` | integer | - | Maximum tokens to return |
| `truncate_mode` | string | - | `chars`, `tokens`, `sections`, or `paragraphs` |
| `truncate_limit` | integer | - | Limit for truncation mode |
| `timeout` | integer | - | Timeout in seconds |
| `include_frontmatter` | boolean | true | Include YAML frontmatter with metadata |
| `output_format` | string | markdown | `markdown` or `json` |

### Supported File Formats

- **Documents:** PDF, DOCX, DOC, RTF, ODT
- **Spreadsheets:** XLSX, XLS, CSV
- **Presentations:** PPTX, PPT, ODP
- **Images:** PNG, JPG, GIF, WebP, TIFF (auto-OCR)
- **Web:** HTML, XML
- **Text:** TXT, MD, JSON

## Response Format

By default, returns raw markdown with YAML frontmatter. Set `output_format: "json"` for structured responses.

### Markdown (Default)

```markdown
---
title: "Article Title"
source: "https://example.com/article"
word_count: 1523
---

# Article Title

Content here...
```

### JSON

```json
{
  "success": true,
  "title": "Article Title",
  "markdown": "# Article Title\n\nContent...",
  "source": "https://example.com/article",
  "word_count": 1523,
  "metadata": {
    "language": "en",
    "was_truncated": false
  }
}
```

### Error Response

```json
{
  "success": false,
  "error": {
    "code": "TIMEOUT",
    "message": "URL fetch timed out after 60 seconds",
    "suggestions": ["Try again later", "Try with render_js: true"]
  }
}
```

### Error Codes

| Code | When |
|------|------|
| `TIMEOUT` | Request exceeded timeout |
| `CONNECTION_FAILED` | Cannot reach URL |
| `NOT_FOUND` | 404 response |
| `ACCESS_DENIED` | 401/403 response |
| `INVALID_INPUT` | Missing or conflicting parameters |
| `INVALID_URL` | Malformed URL |
| `UNSUPPORTED_FORMAT` | Unknown file type |
| `FILE_TOO_LARGE` | Exceeds size limit |
| `CONVERSION_FAILED` | Processing error |
| `CONTENT_EMPTY` | No extractable content |

## Transport Modes

### stdio (Default)

For local AI tools (Claude Desktop, Cursor):

```bash
uvx md-server[mcp] --mcp-stdio
```

### SSE

For network-based AI agents:

```bash
uvx md-server[mcp] --mcp-sse --port 9000
```

Endpoints: `GET /health`, `GET /sse`, `POST /messages`

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MD_SERVER_CONVERSION_TIMEOUT` | 120 | Conversion timeout (seconds) |
| `MD_SERVER_BROWSER_TIMEOUT` | 90 | Browser timeout (seconds) |
| `MD_SERVER_MAX_FILE_SIZE` | 52428800 | Max file size (bytes) |
| `MD_SERVER_ALLOW_LOCALHOST` | true | Allow localhost URLs |
| `MD_SERVER_ALLOW_PRIVATE_NETWORKS` | false | Allow private IP ranges |

See [Configuration](configuration.md) for the complete list.

## Troubleshooting

### Tool not appearing in Claude Desktop

1. Verify configuration file path is correct
2. Check JSON syntax
3. Restart Claude Desktop completely
4. Check Claude Desktop logs

### JavaScript-rendered pages return empty content

1. Install browsers: `uvx playwright install --with-deps chromium`
2. Use `render_js: true` in the request

### URL blocked by SSRF protection

```bash
export MD_SERVER_ALLOW_LOCALHOST=true
export MD_SERVER_ALLOW_PRIVATE_NETWORKS=true
```

### Large files timing out

```bash
export MD_SERVER_CONVERSION_TIMEOUT=300
```

## See Also

- [API Reference](API.md) - HTTP API documentation
- [Configuration](configuration.md) - All environment variables
- [Python SDK](sdk/README.md) - Library usage
