# MD Server Python SDK

Python SDK for document to markdown conversion using md-server.

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage Patterns](#usage-patterns)
- [Synchronous API](#synchronous-api)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)
- [Integration Examples](#integration-examples)

## Installation

```bash
pip install md-server[sdk]
```

## Quick Start

### Local Conversion

```python
from md_server.sdk import MDConverter

# Create converter with default settings
converter = MDConverter()

# Convert various input types
result = await converter.convert_file("document.pdf")
result = await converter.convert_url("https://example.com")
result = await converter.convert_text("<h1>HTML</h1>", mime_type="text/html")

print(result.markdown)
print(f"Processed {result.metadata.source_size} bytes in {result.metadata.conversion_time_ms}ms")
```

### Remote Conversion

```python
from md_server.sdk import RemoteMDConverter

# Connect to remote md-server instance
async with RemoteMDConverter(
    endpoint="https://api.example.com",
    api_key="your-api-key"
) as client:
    result = await client.convert_file("document.pdf")
    print(result.markdown)
```

## Configuration

### Local Converter Options

```python
converter = MDConverter(
    # OCR for scanned PDFs and images
    ocr_enabled=True,
    
    # JavaScript rendering for dynamic web pages
    js_rendering=True,
    
    # Timeout for conversion operations
    timeout=60,
    
    # Maximum file size in MB
    max_file_size_mb=100,
    
    # Extract and reference embedded images
    extract_images=True,
    
    # Preserve complex formatting
    preserve_formatting=True,
    
    # Clean and normalize markdown output
    clean_markdown=False
)
```

### Remote Converter Options

```python
from md_server.sdk import RemoteMDConverter

client = RemoteMDConverter(
    endpoint="https://your-md-server.com",
    api_key="your-api-key",
    timeout=30  # HTTP request timeout
)
```

## Usage Patterns

### File Processing

```python
from pathlib import Path

async def process_documents(folder_path: str):
    converter = MDConverter(ocr_enabled=True)
    folder = Path(folder_path)
    
    for file_path in folder.glob("*.pdf"):
        try:
            result = await converter.convert_file(file_path)
            
            # Save markdown output
            output_path = file_path.with_suffix(".md")
            output_path.write_text(result.markdown)
            
            print(f"Converted {file_path.name} -> {output_path.name}")
            
        except Exception as e:
            print(f"Failed to convert {file_path.name}: {e}")
```

### URL Processing with Options

```python
async def convert_web_pages():
    converter = MDConverter()
    
    urls = [
        "https://example.com/static-page",
        "https://spa.example.com",  # JavaScript-heavy
    ]
    
    for url in urls:
        # Detect if JS rendering needed
        js_needed = "spa." in url or "app." in url
        
        result = await converter.convert_url(
            url,
            js_rendering=js_needed,
            extract_images=True
        )
        
        print(f"URL: {url}")
        print(f"Size: {result.metadata.markdown_size} chars")
        print(f"Format: {result.metadata.detected_format}")
```

### Batch Processing

```python
import asyncio
from typing import List

async def batch_convert_files(file_paths: List[str]) -> List[str]:
    converter = MDConverter()
    
    # Process files concurrently
    tasks = [
        converter.convert_file(path) 
        for path in file_paths
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    markdown_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"Failed {file_paths[i]}: {result}")
            markdown_results.append("")
        else:
            markdown_results.append(result.markdown)
    
    return markdown_results
```

### Content Type Detection

```python
async def smart_convert(input_data: bytes, filename: str = None):
    converter = MDConverter()
    
    # SDK automatically detects content type
    result = await converter.convert_content(
        input_data, 
        filename=filename
    )
    
    print(f"Detected format: {result.metadata.detected_format}")
    print(f"Source type: {result.metadata.source_type}")
    
    return result.markdown
```

## Synchronous API

For non-async environments:

```python
from md_server.sdk import MDConverter

converter = MDConverter()

# Sync methods (automatically handle event loop)
result = converter.convert_file_sync("document.pdf")
result = converter.convert_url_sync("https://example.com")
result = converter.convert_text_sync("<h1>HTML</h1>", mime_type="text/html")
```

## Error Handling

### Exception Handling

The simplified SDK uses standard Python exceptions:

```python
from md_server.sdk import MDConverter

converter = MDConverter()

try:
    result = await converter.convert_file("document.pdf")
except FileNotFoundError:
    print("File not found")
except ValueError as e:
    print(f"Invalid input: {e}")
except OSError as e:
    print(f"System error: {e}")
```

### Comprehensive Error Handling

```python
async def robust_convert(file_path: str):
    converter = MDConverter()
    
    try:
        result = await converter.convert_file(file_path)
        return result.markdown
        
    except FileNotFoundError:
        print(f"File {file_path} not found")
        return None
        
    except ValueError as e:
        print(f"Invalid input for {file_path}: {e}")
        return None
        
    except OSError as e:
        print(f"File system error for {file_path}: {e}")
        return None
        
    except Exception as e:
        print(f"Conversion failed for {file_path}: {e}")
        return None
```

## Best Practices

### 1. Resource Management

```python
# For local converters, no special cleanup needed
converter = MDConverter()

# For remote converters, use context manager
async with RemoteMDConverter("https://api.example.com") as client:
    result = await client.convert_file("document.pdf")
```

### 2. Configuration Management

```python
import os
from dataclasses import dataclass

@dataclass
class ConversionSettings:
    ocr_enabled: bool = True
    js_rendering: bool = False
    timeout: int = 60
    max_file_size_mb: int = 50

def create_converter(settings: ConversionSettings = None) -> MDConverter:
    settings = settings or ConversionSettings()
    
    return MDConverter(
        ocr_enabled=settings.ocr_enabled,
        js_rendering=settings.js_rendering,
        timeout=settings.timeout,
        max_file_size_mb=settings.max_file_size_mb
    )

# Usage
converter = create_converter(ConversionSettings(ocr_enabled=True))
```

### 3. Performance Optimization

```python
# Reuse converter instances
converter = MDConverter()

# Process multiple files with same converter
for file_path in file_paths:
    result = await converter.convert_file(file_path)

# Use appropriate timeouts
fast_converter = MDConverter(timeout=10)  # For simple documents
slow_converter = MDConverter(timeout=120)  # For complex documents

# Batch similar operations
pdf_files = [f for f in files if f.endswith('.pdf')]
url_list = [url for url in inputs if url.startswith('http')]

# Process each type optimally
for pdf_file in pdf_files:
    result = await converter.convert_file(pdf_file)
```

### 4. Logging and Monitoring

```python
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def monitored_convert(file_path: str):
    converter = MDConverter()
    
    logger.info(f"Starting conversion: {file_path}")
    start_time = time.time()
    
    try:
        result = await converter.convert_file(file_path)
        
        duration = time.time() - start_time
        logger.info(
            f"Conversion completed: {file_path} "
            f"({result.metadata.source_size} bytes -> "
            f"{result.metadata.markdown_size} chars in {duration:.2f}s)"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Conversion failed: {file_path} - {e}")
        raise
```

## Integration Examples

### Django Integration

```python
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from md_server.sdk import MDConverter
import json

@csrf_exempt
async def convert_document(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    converter = MDConverter()
    
    try:
        if 'file' in request.FILES:
            file_obj = request.FILES['file']
            content = file_obj.read()
            result = await converter.convert_content(content, filename=file_obj.name)
        else:
            data = json.loads(request.body)
            if 'url' in data:
                result = await converter.convert_url(data['url'])
            else:
                return JsonResponse({'error': 'No file or URL provided'}, status=400)
        
        return JsonResponse({
            'markdown': result.markdown,
            'metadata': {
                'source_type': result.metadata.source_type,
                'conversion_time_ms': result.metadata.conversion_time_ms
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
```

### FastAPI Integration

```python
from fastapi import FastAPI, UploadFile, HTTPException
from md_server.sdk import MDConverter

app = FastAPI()
converter = MDConverter()

@app.post("/convert")
async def convert_endpoint(file: UploadFile):
    try:
        content = await file.read()
        result = await converter.convert_content(content, filename=file.filename)
        
        return {
            "markdown": result.markdown,
            "metadata": {
                "source_type": result.metadata.source_type,
                "source_size": result.metadata.source_size,
                "conversion_time_ms": result.metadata.conversion_time_ms
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

## See Also

- [API Reference](../API.md) - HTTP API documentation
- [MCP Guide](../mcp-guide.md) - AI tool integration
- [Configuration](../configuration.md) - Environment variables
- [Troubleshooting](../troubleshooting.md) - Common issues
- [Main README](../../README.md) - Project overview and quick start