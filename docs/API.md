# API Documentation

## Base URL

```
http://localhost:8080
```

This can be modified with the `--host` and `--port` options when running the server or by setting the environment variables `MD_SERVER_HOST` and `MD_SERVER_PORT`. Please use HTTPS in production (Consider [Caddy](https://caddyserver.com/) for easy HTTPS setup) and use `MD_SERVER_API_KEY` to support API key auth.

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
  "content": "string", // base64
  "text": "string",
  "mime_type": "string", // optional, for text field
  "filename": "string",
  "source_format": "string",
  "options": {
    "js_rendering": false,
    "timeout": 30,
    "extract_images": false,
    "preserve_formatting": false,
    "ocr_enabled": false,
    "max_length": null,
    "clean_markdown": false
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
    "warnings": []
  },
  "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
}
```

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

Returns supported formats.

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
  "version": "1.0.0"
}
```

## Error Codes

| Code                 | Status | Description           |
| -------------------- | ------ | --------------------- |
| `UNSUPPORTED_FORMAT` | 400    | Format not supported  |
| `FILE_TOO_LARGE`     | 413    | Exceeds size limit    |
| `INVALID_URL`        | 400    | URL malformed/blocked |
| `INVALID_INPUT`      | 400    | Invalid MIME type/input |
| `FETCH_FAILED`       | 502    | URL fetch failed      |
| `CONVERSION_FAILED`  | 500    | Conversion error      |
| `RATE_LIMITED`       | 429    | Too many requests     |
| `INVALID_CONTENT`    | 400    | Validation failed     |
| `TIMEOUT`            | 504    | Operation timeout     |

## Options

| Option                | Type | Default | Description                |
| --------------------- | ---- | ------- | -------------------------- |
| `js_rendering`        | bool | false   | Use headless browser       |
| `timeout`             | int  | 30      | Timeout seconds (max: 120) |
| `extract_images`      | bool | false   | Extract embedded images    |
| `preserve_formatting` | bool | false   | Keep complex formatting    |
| `ocr_enabled`         | bool | false   | OCR for images/PDFs        |
| `max_length`          | int  | null    | Truncate output            |
| `clean_markdown`      | bool | false   | Normalize markdown         |

## Security

### API Key Authentication

To secure your API, set the `MD_SERVER_API_KEY` environment variable:

```bash
# Set API key
export MD_SERVER_API_KEY="your-secret-api-key-here"

# Start server
uvx md-server
```

When configured, all requests (except `/healthz`) require the `Authorization` header:

```bash
# Authenticated request
curl -X POST localhost:8080/convert \
  -H "Authorization: Bearer your-secret-api-key-here" \
  --data-binary @document.pdf

# Unauthenticated requests will return 401
curl -X POST localhost:8080/convert --data-binary @document.pdf
# {"success": false, "error": {"code": "UNAUTHORIZED", "message": "Missing Authorization header"}}
```

Use HTTPS in production to protect the key in transit.

### SSRF Protection

- Blocked: Private IPs (10.x, 192.168.x, 127.x), AWS metadata (169.254.169.254)
- Allowed schemes: https, http
- Max redirects: 5
- Max size: 50MB

### File Validation

- Magic bytes verification
- Size limits per format
- Path traversal prevention

## Rate Limiting

- 100 requests/hour per IP
- Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

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

# With options
curl -X POST localhost:8080/convert \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","options":{"js_rendering":true}}'

# Pipe input
cat document.html | curl -X POST localhost:8080/convert \
  --data-binary @- -H "Content-Type: text/html"

# Save output
curl -X POST localhost:8080/convert --data-binary @doc.pdf \
  | jq -r '.markdown' > output.md
```

</details>

# Python SDK

## Installation

The SDK is included with md-server:

```bash
pip install md-server
```

## Local Usage

```python
from md_server import MDConverter

# Create converter
converter = MDConverter()

# Convert file
result = await converter.convert_file("document.pdf")
print(result.markdown)

# Convert URL
result = await converter.convert_url("https://example.com")
print(result.markdown)

# Convert binary content
with open("file.pdf", "rb") as f:
    result = await converter.convert_content(f.read(), filename="file.pdf")

# Convert text with MIME type
result = await converter.convert_text("<h1>HTML</h1>", mime_type="text/html")
```

## Remote Usage

```python
from md_server import MDConverter

# Connect to remote md-server
converter = MDConverter.remote(
    endpoint="https://api.example.com",
    api_key="your-api-key"
)

result = await converter.convert_file("document.pdf")
```

## Sync API

```python
from md_server import MDConverter

converter = MDConverter()

# Sync versions
result = converter.convert_file_sync("document.pdf")
result = converter.convert_url_sync("https://example.com")
```

## Configuration

```python
converter = MDConverter(
    ocr_enabled=True,
    js_rendering=True,
    timeout=60,
    max_file_size_mb=100,
    extract_images=True,
    preserve_formatting=True
)
```

## Models

### ConversionResult

```python
@dataclass
class ConversionResult:
    markdown: str
    metadata: ConversionMetadata
    success: bool = True
    request_id: str = None
```

### ConversionMetadata

```python
@dataclass
class ConversionMetadata:
    source_type: str
    source_size: int
    markdown_size: int
    processing_time: float
    detected_format: str
    warnings: List[str] = None
```

## Exceptions

```python
from md_server import (
    ConversionError,
    InvalidInputError,
    NetworkError,
    TimeoutError,
    FileSizeError,
    UnsupportedFormatError
)

try:
    result = await converter.convert_file("document.pdf")
except FileSizeError:
    print("File too large")
except UnsupportedFormatError:
    print("Format not supported")
except ConversionError as e:
    print(f"Conversion failed: {e}")
```

<details>
<summary>Legacy HTTP Client Example</summary>

```python
import requests

class MDServerClient:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url

    def convert_file(self, file_path, options=None):
        with open(file_path, 'rb') as f:
            response = requests.post(
                f"{self.base_url}/convert",
                data=f.read()
            )
        return response.json()

    def convert_url(self, url, options=None):
        payload = {"url": url}
        if options:
            payload["options"] = options
        response = requests.post(
            f"{self.base_url}/convert",
            json=payload
        )
        return response.json()

# Usage
client = MDServerClient()
result = client.convert_file("document.pdf")
print(result["markdown"])
```

</details>

<details>
<summary>JavaScript SDK</summary>

```javascript
class MDServerClient {
  constructor(baseUrl = "http://localhost:8080") {
    this.baseUrl = baseUrl;
  }

  async convertFile(file, options) {
    const formData = new FormData();
    formData.append("file", file);
    if (options) {
      formData.append("options", JSON.stringify(options));
    }
    const response = await fetch(`${this.baseUrl}/convert`, {
      method: "POST",
      body: formData,
    });
    return response.json();
  }

  async convertUrl(url, options) {
    const response = await fetch(`${this.baseUrl}/convert`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, options }),
    });
    return response.json();
  }
}
```

</details>

<details>
<summary>Go SDK</summary>

```go
package main

import (
    "bytes"
    "encoding/json"
    "net/http"
)

type MDServerClient struct {
    BaseURL string
}

type ConvertOptions struct {
    JSRendering    bool `json:"js_rendering,omitempty"`
    ExtractImages  bool `json:"extract_images,omitempty"`
}

func (c *MDServerClient) ConvertURL(url string, opts *ConvertOptions) (map[string]interface{}, error) {
    payload := map[string]interface{}{
        "url": url,
        "options": opts,
    }

    body, _ := json.Marshal(payload)
    resp, err := http.Post(
        c.BaseURL+"/convert",
        "application/json",
        bytes.NewReader(body),
    )
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()

    var result map[string]interface{}
    json.NewDecoder(resp.Body).Decode(&result)
    return result, nil
}
```

</details>

<details>
<summary>Ruby SDK</summary>

```ruby
require 'net/http'
require 'json'

class MDServerClient
  def initialize(base_url = 'http://localhost:8080')
    @base_url = base_url
  end

  def convert_file(file_path, options = nil)
    uri = URI("#{@base_url}/convert")
    request = Net::HTTP::Post.new(uri)
    request.body = File.read(file_path, mode: 'rb')

    response = Net::HTTP.start(uri.hostname, uri.port) do |http|
      http.request(request)
    end

    JSON.parse(response.body)
  end

  def convert_url(url, options = nil)
    uri = URI("#{@base_url}/convert")
    request = Net::HTTP::Post.new(uri)
    request['Content-Type'] = 'application/json'
    request.body = { url: url, options: options }.to_json

    response = Net::HTTP.start(uri.hostname, uri.port) do |http|
      http.request(request)
    end

    JSON.parse(response.body)
  end
end
```

</details>
