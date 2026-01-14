# API Reference

HTTP API documentation for md-server.

## Table of Contents

- [Base URL](#base-url)
- [Endpoints](#endpoints)
  - [POST /convert](#post-convert)
  - [GET /formats](#get-formats)
  - [GET /health](#get-health)
- [Content Negotiation](#content-negotiation)
- [Options](#options)
- [Error Codes](#error-codes)
- [Security](#security)
- [Examples](#examples)

## Base URL

```
http://localhost:8080
```

Configure with `--host` and `--port` options or environment variables `MD_SERVER_HOST` and `MD_SERVER_PORT`. Use HTTPS in production (consider [Caddy](https://caddyserver.com/) for easy HTTPS setup) and set `MD_SERVER_API_KEY` for authentication.

See [Configuration](configuration.md) for all environment variables.

## Endpoints

### POST /convert

Single endpoint that handles all conversion types. Input type is detected automatically.

#### Input Detection

Detection order:
1. Content-Type header
2. Request body structure (JSON fields)
3. Magic bytes (binary data)

#### Input Methods

##### Binary Upload

```bash
curl -X POST http://localhost:8080/convert --data-binary @document.pdf
```

##### Multipart Form

```bash
curl -X POST http://localhost:8080/convert -F "file=@document.docx"
```

##### JSON with URL

```bash
curl -X POST http://localhost:8080/convert \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/document.pdf"}'
```

##### JSON with Base64

```bash
curl -X POST http://localhost:8080/convert \
  -H "Content-Type: application/json" \
  -d '{"content": "base64_string", "filename": "doc.xlsx"}'
```

##### JSON with Text

```bash
curl -X POST http://localhost:8080/convert \
  -H "Content-Type: application/json" \
  -d '{"text": "# Markdown content"}'
```

##### JSON with Typed Text

```bash
# HTML text conversion
curl -X POST http://localhost:8080/convert \
  -H "Content-Type: application/json" \
  -d '{"text": "<h1>Title</h1><p>Content</p>", "mime_type": "text/html"}'

# XML text conversion
curl -X POST http://localhost:8080/convert \
  -H "Content-Type: application/json" \
  -d '{"text": "<?xml version=\"1.0\"?><root><item>Data</item></root>", "mime_type": "text/xml"}'
```

#### Request Schema

```json
{
  "url": "string",
  "content": "string",
  "text": "string",
  "mime_type": "string",
  "filename": "string",
  "source_format": "string",
  "options": {
    "js_rendering": false,
    "timeout": 30,
    "extract_images": false,
    "preserve_formatting": true,
    "ocr_enabled": false,
    "max_length": null,
    "max_tokens": null,
    "truncate_mode": null,
    "truncate_limit": null,
    "clean_markdown": false,
    "include_frontmatter": false,
    "output_format": null
  }
}
```

#### Response

##### Success (200)

```json
{
  "success": true,
  "markdown": "# Content",
  "metadata": {
    "source_type": "pdf",
    "source_size": 102400,
    "markdown_size": 8192,
    "conversion_time_ms": 456,
    "detected_format": "application/pdf",
    "warnings": [],
    "title": "Document Title",
    "estimated_tokens": 2048,
    "detected_language": "en"
  },
  "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
}
```

##### Metadata Fields

| Field | Type | Description |
|-------|------|-------------|
| `source_type` | string | Type of source content (pdf, html, etc.) |
| `source_size` | int | Size of source content in bytes |
| `markdown_size` | int | Size of converted markdown in bytes |
| `conversion_time_ms` | int | Time taken for conversion in milliseconds |
| `detected_format` | string | Detected format/MIME type |
| `warnings` | array | Conversion warnings |
| `title` | string | Extracted document title (if available) |
| `estimated_tokens` | int | Estimated token count for LLM usage |
| `detected_language` | string | ISO 639-1 language code (e.g., "en", "es") |
| `was_truncated` | bool | True if content was truncated |
| `original_length` | int | Original character count before truncation |
| `original_tokens` | int | Original token count before truncation |
| `truncation_mode` | string | How content was truncated (chars, tokens, sections, paragraphs) |

##### Error (4xx/5xx)

```json
{
  "success": false,
  "error": {
    "code": "UNSUPPORTED_FORMAT",
    "message": "File format not supported",
    "details": {},
    "suggestions": []
  },
  "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
}
```

### GET /formats

Returns supported formats and capabilities.

```bash
curl http://localhost:8080/formats
```

<details>
<summary>Response Example</summary>

```json
{
  "formats": {
    "pdf": {
      "mime_types": ["application/pdf"],
      "extensions": [".pdf"],
      "features": ["ocr", "extract_images", "preserve_formatting"],
      "max_size_mb": 50
    },
    "docx": {
      "mime_types": [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
      ],
      "extensions": [".docx"],
      "features": ["extract_images", "preserve_formatting"],
      "max_size_mb": 25
    }
  },
  "supported_formats": ["pdf", "docx", "..."],
  "capabilities": {
    "browser_available": true
  }
}
```

</details>

### GET /health

```bash
curl http://localhost:8080/health
```

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "conversions_last_hour": 42
}
```

## Content Negotiation

md-server supports two response formats: JSON (default) and raw markdown.

### JSON Response (Default)

Standard JSON response with metadata:

```bash
curl -X POST localhost:8080/convert --data-binary @document.pdf
```

### Raw Markdown Response

Get raw markdown with metadata in HTTP headers. Use either:

**Accept header:**

```bash
curl -X POST localhost:8080/convert \
  -H "Accept: text/markdown" \
  --data-binary @document.pdf
```

**output_format option:**

```bash
curl -X POST localhost:8080/convert \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "options": {"output_format": "markdown"}}'
```

#### Response Headers

When using raw markdown output, metadata is returned in HTTP headers:

| Header | Description |
|--------|-------------|
| `X-Request-Id` | Unique request identifier |
| `X-Source-Type` | Source content type |
| `X-Source-Size` | Source size in bytes |
| `X-Markdown-Size` | Output size in bytes |
| `X-Conversion-Time-Ms` | Conversion time in milliseconds |
| `X-Detected-Format` | Detected MIME type |
| `X-Estimated-Tokens` | Token count estimate (if available) |

#### Piping Raw Markdown

Raw markdown mode is useful for CLI pipelines:

```bash
# Save directly to file
curl -s -X POST localhost:8080/convert \
  -H "Accept: text/markdown" \
  --data-binary @document.pdf > output.md

# Pipe to other tools
curl -s -X POST localhost:8080/convert \
  -H "Accept: text/markdown" \
  -d '{"url": "https://example.com"}' | grep "keyword"
```

## Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `js_rendering` | bool | false | Use headless browser for JavaScript sites |
| `timeout` | int | 30 | Timeout seconds (max: 120) |
| `extract_images` | bool | false | Extract embedded images |
| `preserve_formatting` | bool | true | Keep complex formatting |
| `ocr_enabled` | bool | false | OCR for images/scanned PDFs |
| `max_length` | int | null | Truncate output to character limit |
| `max_tokens` | int | null | Truncate output to token limit (uses tiktoken cl100k_base) |
| `truncate_mode` | string | null | Truncation mode: `chars`, `tokens`, `sections`, `paragraphs` |
| `truncate_limit` | int | null | Limit for truncation mode |
| `clean_markdown` | bool | false | Normalize markdown |
| `include_frontmatter` | bool | false | Prepend YAML frontmatter with metadata |
| `output_format` | string | null | Response format: "json" or "markdown" |

### Truncation Options

For controlling output size, md-server offers flexible truncation:

**Character/Token limits:**
- `max_length` - Simple character truncation
- `max_tokens` - Token-based truncation using tiktoken cl100k_base (useful for LLM context limits)

**Markdown-aware truncation:**
- `truncate_mode: "sections"` with `truncate_limit: 5` - Returns first 5 `##` sections
- `truncate_mode: "paragraphs"` with `truncate_limit: 10` - Returns first 10 paragraphs

When content is truncated, the response metadata includes `was_truncated`, `original_length`, `original_tokens`, and `truncation_mode`.

### include_frontmatter

When enabled, prepends YAML frontmatter to the markdown output:

```bash
curl -X POST localhost:8080/convert \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "options": {"include_frontmatter": true}}'
```

Output:

```markdown
---
title: "Example Page"
source_type: html
estimated_tokens: 1024
detected_language: en
---

# Example Page

Content here...
```

## Error Codes

| Code | Status | Description |
|------|--------|-------------|
| `UNSUPPORTED_FORMAT` | 400 | Format not supported |
| `FILE_TOO_LARGE` | 413 | Exceeds size limit |
| `INVALID_URL` | 400 | URL malformed/blocked |
| `INVALID_INPUT` | 400 | Invalid MIME type/input |
| `FETCH_FAILED` | 502 | URL fetch failed |
| `CONVERSION_FAILED` | 500 | Conversion error |
| `RATE_LIMITED` | 429 | Too many requests |
| `INVALID_CONTENT` | 400 | Validation failed |
| `TIMEOUT` | 504 | Operation timeout |
| `SSRF_BLOCKED` | 400 | URL targets blocked resource |
| `UNAUTHORIZED` | 401 | Missing or invalid API key |

## Security

### API Key Authentication

Set `MD_SERVER_API_KEY` to require authentication:

```bash
export MD_SERVER_API_KEY="your-secret-api-key"
uvx md-server
```

Requests must include the `Authorization` header:

```bash
curl -X POST localhost:8080/convert \
  -H "Authorization: Bearer your-secret-api-key" \
  --data-binary @document.pdf
```

### SSRF Protection

By default, md-server blocks:
- Private IPs (10.x, 192.168.x, 172.16.x)
- Localhost (127.x, ::1)
- Cloud metadata (169.254.169.254)

See [Configuration](configuration.md) for SSRF settings.

### File Validation

- Magic bytes verification
- Size limits per format
- Path traversal prevention

## Examples

<details>
<summary>cURL Examples</summary>

```bash
# PDF conversion
curl -X POST localhost:8080/convert --data-binary @document.pdf

# URL conversion
curl -X POST localhost:8080/convert \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com"}'

# With JavaScript rendering
curl -X POST localhost:8080/convert \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","options":{"js_rendering":true}}'

# With OCR
curl -X POST localhost:8080/convert \
  -H "Content-Type: application/json" \
  -d '{"content":"base64...","filename":"scan.pdf","options":{"ocr_enabled":true}}'

# Raw markdown output
curl -X POST localhost:8080/convert \
  -H "Accept: text/markdown" \
  --data-binary @document.pdf

# With frontmatter
curl -X POST localhost:8080/convert \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","options":{"include_frontmatter":true}}'

# With token limit (useful for LLM context)
curl -X POST localhost:8080/convert \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","options":{"max_tokens":4000}}'

# Get first 5 sections only
curl -X POST localhost:8080/convert \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","options":{"truncate_mode":"sections","truncate_limit":5}}'

# Pipe from stdin
echo "<h1>Hello</h1>" | curl -X POST localhost:8080/convert \
  --data-binary @- -H "Content-Type: text/html"

# Save output
curl -X POST localhost:8080/convert --data-binary @doc.pdf \
  | jq -r '.markdown' > output.md
```

</details>

## See Also

- [Python SDK](sdk/README.md) - Library usage for Python applications
- [MCP Guide](mcp-guide.md) - AI tool integration
- [Configuration](configuration.md) - Environment variables
- [Troubleshooting](troubleshooting.md) - Common issues
