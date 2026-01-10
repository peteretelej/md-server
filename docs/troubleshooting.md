# Troubleshooting

Common issues and solutions for md-server.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Conversion Issues](#conversion-issues)
- [URL and Web Scraping Issues](#url-and-web-scraping-issues)
- [MCP Issues](#mcp-issues)
- [Performance Issues](#performance-issues)
- [Getting Help](#getting-help)

## Installation Issues

### "MCP dependencies not installed"

The MCP extras are required for AI tool integration:

```bash
pip install md-server[mcp]
# or use uvx directly
uvx md-server[mcp] --mcp-stdio
```

### Playwright browsers not found

JavaScript rendering requires Playwright browsers:

```bash
# Install Chromium
uvx playwright install chromium

# Or install all browsers
uvx playwright install
```

Docker images include browsers automatically.

### Port already in use

If port 8080 is taken:

```bash
# Use a different port
uvx md-server --port 9000

# Or set environment variable
export MD_SERVER_PORT=9000
uvx md-server
```

### Permission denied on Linux

If you see permission errors:

```bash
# May need to run playwright install with proper permissions
python -m playwright install chromium
```

## Conversion Issues

### Unsupported format error

Check supported formats:

```bash
curl localhost:8080/formats
```

For files without extensions, provide the MIME type:

```bash
curl -X POST localhost:8080/convert \
  -H "Content-Type: application/pdf" \
  --data-binary @file_without_extension
```

### PDF or image OCR not working

Enable OCR explicitly:

```bash
curl -X POST localhost:8080/convert \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/scan.pdf", "options": {"ocr_enabled": true}}'
```

### Large files failing

Check and increase the file size limit:

```bash
# Default is 50MB (52428800 bytes)
export MD_SERVER_MAX_FILE_SIZE=104857600  # 100MB
uvx md-server
```

### Timeout errors

Increase the timeout for large or complex documents:

```bash
export MD_SERVER_CONVERSION_TIMEOUT=300  # 5 minutes
export MD_SERVER_TIMEOUT_SECONDS=60
uvx md-server
```

### Empty output from conversion

1. Check if the file is valid and not corrupted
2. For PDFs, the content might be image-based (enable OCR)
3. For web pages, JavaScript might be required

## URL and Web Scraping Issues

### JavaScript sites return empty content

Enable JavaScript rendering:

```bash
curl -X POST localhost:8080/convert \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "options": {"js_rendering": true}}'
```

Requires Playwright browsers (see [Installation Issues](#playwright-browsers-not-found)).

### URL blocked (SSRF error)

By default, private IPs and localhost are blocked. For development:

```bash
export MD_SERVER_ALLOW_LOCALHOST=true
export MD_SERVER_ALLOW_PRIVATE_NETWORKS=true
uvx md-server
```

Blocked by default:
- `127.0.0.0/8` (localhost)
- `10.0.0.0/8` (private)
- `172.16.0.0/12` (private)
- `192.168.0.0/16` (private)
- `169.254.169.254` (cloud metadata)

### URL fetch timeout

Increase the URL fetch timeout:

```bash
export MD_SERVER_URL_FETCH_TIMEOUT=60
uvx md-server
```

### SSL certificate errors

If fetching HTTPS URLs fails due to certificate issues, ensure your system's CA certificates are up to date.

## MCP Issues

### Tool not appearing in Claude Desktop

1. **Check config path** - Verify the configuration file location:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`

2. **Validate JSON syntax** - Ensure the configuration is valid JSON:
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

3. **Restart Claude Desktop** - Fully quit and reopen the application

4. **Check for errors** - Look at Claude Desktop logs for error messages

### SSE connection failing

1. Verify the server is running:
   ```bash
   curl http://localhost:9000/health
   ```

2. Check firewall settings

3. Ensure no other service is using the port

### MCP conversion errors

Check that the server can access the target URL or file. Environment variables still apply in MCP mode.

## Performance Issues

### Slow URL conversions

1. **Disable JS rendering** if not needed - JavaScript rendering is slower
2. **Check network** - Slow target sites affect conversion time
3. **Reduce timeout** - Set appropriate timeout for your use case

### High memory usage

1. **Reduce max file size** - Limit large uploads:
   ```bash
   export MD_SERVER_MAX_FILE_SIZE=26214400  # 25MB
   ```

2. **Docker resource limits** - Set container memory limits:
   ```bash
   docker run -m 1g -p 8080:8080 ghcr.io/peteretelej/md-server
   ```

### Slow startup with Docker

Initial startup takes 10-15 seconds for browser initialization. This is normal for the Docker image which includes full browser support.

## Getting Help

If you're still having issues:

1. **Check existing issues** - [GitHub Issues](https://github.com/peteretelej/md-server/issues)
2. **Open a new issue** - Include:
   - md-server version (`uvx md-server --version`)
   - Operating system
   - Error messages
   - Steps to reproduce
3. **Discussions** - [GitHub Discussions](https://github.com/peteretelej/md-server/discussions)

## See Also

- [Configuration](configuration.md) - All environment variables
- [API Reference](API.md) - HTTP endpoints and options
- [MCP Guide](mcp-guide.md) - AI tool integration
