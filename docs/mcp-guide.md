# MCP Integration Guide

md-server works directly with AI tools via [Model Context Protocol (MCP)](https://modelcontextprotocol.io). This lets Claude Desktop, Cursor, and other AI tools read documents and web pages without any HTTP setup.

## Table of Contents

- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Transport Modes](#transport-modes)
- [Available Tools](#available-tools)
- [Response Format](#response-format)
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
| `MD_SERVER_BROWSER_TIMEOUT` | 90 | Browser operations timeout (JS rendering) |
| `MD_SERVER_OCR_TIMEOUT` | 120 | OCR operations timeout |
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

## Available Tools

When integrated, your AI gets access to two tools: `read_url` and `read_file`.

### read_url

Fetch and read content from a URL, returning clean markdown.

**Use this to read:**
- Articles, blog posts, news, documentation
- Online PDFs and Google Docs (public)
- Dynamic web apps (set `render_js: true`)

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `url` | string | Yes | - | URL to fetch (webpage, PDF link, document URL) |
| `render_js` | boolean | No | false | Execute JavaScript before reading. Enable for SPAs and pages that load content dynamically. |
| `max_length` | integer | No | - | Maximum characters to return. Content is truncated if exceeded. |
| `max_tokens` | integer | No | - | Maximum tokens to return (uses tiktoken cl100k_base encoding). |
| `truncate_mode` | string | No | - | Truncation mode: `chars`, `tokens`, `sections`, or `paragraphs`. |
| `truncate_limit` | integer | No | - | Limit for truncation mode (count of chars/tokens/sections/paragraphs). |
| `timeout` | integer | No | - | Timeout in seconds for the conversion operation. |
| `include_frontmatter` | boolean | No | true | Include YAML frontmatter with metadata in the output. |
| `output_format` | string | No | markdown | Output format: `markdown` (raw text) or `json` (structured response). |

**Truncation Modes:**
- `chars` - Truncate to a character limit
- `tokens` - Truncate to a token limit (useful for LLM context limits)
- `sections` - Keep only the first N `##` headings
- `paragraphs` - Keep only the first N paragraphs

#### Schema

```json
{
  "name": "read_url",
  "inputSchema": {
    "type": "object",
    "required": ["url"],
    "properties": {
      "url": {
        "type": "string",
        "format": "uri",
        "description": "URL to fetch (webpage, PDF link, document URL)"
      },
      "render_js": {
        "type": "boolean",
        "default": false,
        "description": "Execute JavaScript before reading. Enable for SPAs and pages that load content dynamically."
      },
      "max_tokens": {
        "type": "integer",
        "description": "Maximum tokens to return (uses tiktoken cl100k_base encoding)."
      },
      "truncate_mode": {
        "type": "string",
        "enum": ["chars", "tokens", "sections", "paragraphs"],
        "description": "Truncation mode for controlling output size."
      },
      "truncate_limit": {
        "type": "integer",
        "description": "Limit for truncation mode."
      },
      "output_format": {
        "type": "string",
        "enum": ["markdown", "json"],
        "default": "markdown",
        "description": "Output format: markdown (default) or json."
      }
    }
  }
}
```

### read_file

Read and extract content from a document file, returning clean markdown.

**Supported formats:**
- Documents: PDF, DOCX, DOC, RTF, ODT
- Spreadsheets: XLSX, XLS, CSV
- Presentations: PPTX, PPT, ODP
- Images: PNG, JPG, GIF, WebP, TIFF (auto-OCR)
- Web: HTML, XML
- Text: TXT, MD, JSON

Images automatically use OCR to extract visible text - no extra parameters needed.

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `content` | string | Yes | - | Base64-encoded file data |
| `filename` | string | Yes | - | Filename with extension (e.g., 'report.pdf', 'chart.png') |
| `max_length` | integer | No | - | Maximum characters to return. Content is truncated if exceeded. |
| `max_tokens` | integer | No | - | Maximum tokens to return (uses tiktoken cl100k_base encoding). |
| `truncate_mode` | string | No | - | Truncation mode: `chars`, `tokens`, `sections`, or `paragraphs`. |
| `truncate_limit` | integer | No | - | Limit for truncation mode (count of chars/tokens/sections/paragraphs). |
| `timeout` | integer | No | - | Timeout in seconds for the conversion operation. |
| `include_frontmatter` | boolean | No | true | Include YAML frontmatter with metadata in the output. |
| `output_format` | string | No | markdown | Output format: `markdown` (raw text) or `json` (structured response). |

#### Schema

```json
{
  "name": "read_file",
  "inputSchema": {
    "type": "object",
    "required": ["content", "filename"],
    "properties": {
      "content": {
        "type": "string",
        "description": "Base64-encoded file data"
      },
      "filename": {
        "type": "string",
        "description": "Filename with extension (e.g., 'report.pdf', 'chart.png')"
      },
      "max_tokens": {
        "type": "integer",
        "description": "Maximum tokens to return (uses tiktoken cl100k_base encoding)."
      },
      "truncate_mode": {
        "type": "string",
        "enum": ["chars", "tokens", "sections", "paragraphs"],
        "description": "Truncation mode for controlling output size."
      },
      "truncate_limit": {
        "type": "integer",
        "description": "Limit for truncation mode."
      },
      "output_format": {
        "type": "string",
        "enum": ["markdown", "json"],
        "default": "markdown",
        "description": "Output format: markdown (default) or json."
      }
    }
  }
}
```

## Response Format

By default, both tools return **raw markdown** with YAML frontmatter. Set `output_format: "json"` for structured JSON responses.

### Markdown Response (Default)

When `output_format` is `"markdown"` (or not specified), the tool returns raw markdown text:

```markdown
---
title: "Article Title"
source: "https://example.com/article"
word_count: 1523
---

# Article Title

Markdown content here...
```

This format is ideal for direct use by LLMs—the frontmatter provides context while the content is immediately usable.

### JSON Response

When `output_format: "json"`, the tool returns a structured response:

```json
{
  "success": true,
  "title": "Article Title",
  "markdown": "# Article Title\n\nMarkdown content here...",
  "source": "https://example.com/article",
  "word_count": 1523,
  "metadata": {
    "description": "A brief summary of the article",
    "language": "en",
    "format": "text/html",
    "ocr_applied": false,
    "was_truncated": true,
    "original_length": 45000,
    "original_tokens": 12000,
    "truncation_mode": "tokens"
  }
}
```

### Truncation Metadata

When content is truncated, the metadata includes:

| Field | Description |
|-------|-------------|
| `was_truncated` | `true` if content was truncated |
| `original_length` | Original character count before truncation |
| `original_tokens` | Original token count before truncation |
| `truncation_mode` | Mode used: `chars`, `tokens`, `sections`, or `paragraphs` |

### Error Response

Errors always return JSON:

```json
{
  "success": false,
  "error": {
    "code": "TIMEOUT",
    "message": "URL fetch timed out after 60 seconds",
    "suggestions": [
      "The server may be slow or unresponsive. Try again later.",
      "For JavaScript-heavy pages, try with render_js: true"
    ]
  }
}
```

### Error Codes

| Code | When | Suggestions |
|------|------|-------------|
| `TIMEOUT` | Request exceeded timeout | Retry, check if server is slow |
| `CONNECTION_FAILED` | Cannot reach URL | Check URL, server may be down |
| `NOT_FOUND` | 404 response | Verify URL is correct |
| `ACCESS_DENIED` | 401/403 response | Page may require authentication |
| `INVALID_URL` | Malformed URL | Check URL format |
| `UNSUPPORTED_FORMAT` | Unknown file type | See supported formats list |
| `FILE_TOO_LARGE` | Exceeds size limit | Compress or split the file |
| `CONVERSION_FAILED` | Processing error | Try different file/format |
| `CONTENT_EMPTY` | No extractable content | Try `render_js: true` for dynamic pages |

## Examples

Once configured, your AI can read documents directly:

### Reading Web Pages

> "Read this article and summarize it: https://example.com/article"

> "What does the Python asyncio documentation say about tasks?"

### JavaScript-Heavy Sites

> "Read this dashboard with JavaScript rendering enabled: https://app.example.com/stats"

The AI will use `render_js: true` for dynamic content.

### Reading Documents

> "What's in this PDF?" *(with file attached)*

> "Summarize the key points from this Word document"

### OCR for Images

> "Extract the text from this screenshot"

Images are automatically processed with OCR - no special options needed.

### Controlling Output Size

For large documents, use truncation to limit the response:

> "Read this documentation, limiting to 4000 tokens"

The AI will use `max_tokens: 4000` to fit within context limits.

For markdown-aware truncation:

> "Get the first 5 sections from this article"

Uses `truncate_mode: "sections"` and `truncate_limit: 5` to return complete sections.

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
2. Use `render_js: true` in the tool call
3. Error response will suggest this if content is minimal

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

For browser operations:

```bash
export MD_SERVER_BROWSER_TIMEOUT=120
```

## See Also

- [API Reference](API.md) - HTTP API documentation
- [Configuration](configuration.md) - All environment variables
- [Python SDK](sdk/README.md) - Library usage
