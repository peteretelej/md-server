# md-server Documentation

**Convert any document, webpage, or media file to markdown.**

md-server is an HTTP API and MCP server that converts files, URLs, and raw content into markdown. It handles PDFs, Office documents, web pages with JavaScript rendering, images with OCR, and more.

## Quick Links

| Guide | Description |
|-------|-------------|
| [Getting Started](../README.md#quick-start) | Installation and first conversion |
| [API Reference](API.md) | HTTP endpoints, options, and responses |
| [MCP Integration](mcp-guide.md) | Claude Desktop, Cursor, and AI tool setup |
| [Python SDK](sdk/README.md) | Library usage for Python applications |
| [Configuration](configuration.md) | Environment variables reference |
| [Troubleshooting](troubleshooting.md) | Common issues and solutions |

## Features

- **Universal Conversion** - PDF, DOCX, XLSX, PPTX, HTML, images, audio, video
- **Web Scraping** - JavaScript rendering with Crawl4AI
- **MCP Server** - Direct integration with AI tools
- **Python SDK** - Local and remote conversion APIs
- **Security** - SSRF protection, API key authentication
- **Zero Config** - Works out of the box

## Two Ways to Use

### HTTP API

Run as a server for any application:

```bash
uvx md-server
curl -X POST localhost:8080/convert --data-binary @document.pdf
```

### MCP Server

Direct integration with AI tools like Claude Desktop and Cursor:

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

## Architecture

md-server uses [Microsoft MarkItDown](https://github.com/microsoft/markitdown) for document conversion and [Crawl4AI](https://github.com/unclecode/crawl4ai) for intelligent web scraping with JavaScript rendering.

```
Request → Input Detection → Converter → MarkItDown/Crawl4AI → Markdown Response
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## Links

- [GitHub Repository](https://github.com/peteretelej/md-server)
- [PyPI Package](https://pypi.org/project/md-server/)
- [Docker Image](https://github.com/peteretelej/md-server/pkgs/container/md-server)
