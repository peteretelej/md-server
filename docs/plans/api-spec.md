# API Specification

HTTP API for converting documents, files, and web content to markdown.

Optional API key authentication may be required (configured per deployment).

## Endpoints

### Health Check
```http
GET /healthz
```

Response:
```json
{
  "status": "ok"
}
```

### Convert File
```http
POST /convert
Content-Type: multipart/form-data

file: (binary file)
```

Response:
```json
{
  "markdown": "# Document Title\n\nContent here..."
}
```

### Convert URL
```http
POST /convert/url
Content-Type: application/json

{
  "url": "https://example.com/document.pdf"
}
```

Response:
```json
{
  "markdown": "# Document Title\n\nContent here..."
}
```

## Error Response
```json
{
  "error": "Error description"
}
```

## HTTP Status Codes
- 200 OK - Success
- 400 Bad Request - Invalid input
- 415 Unsupported Media Type - File format not supported
- 500 Internal Server Error - Processing failed

## Examples

### Convert Local File
```bash
curl -X POST http://localhost:8080/convert -F "file=@document.pdf"
```

### Convert URL
```bash
curl -X POST http://localhost:8080/convert/url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article"}'
```

### Health Check
```bash
curl http://localhost:8080/healthz
```