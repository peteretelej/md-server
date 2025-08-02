# MarkItDown API Reference

## Installation

```bash
pip install markitdown[all]
```

### Optional Dependencies

Install specific format support:

```bash
pip install markitdown[pdf,docx,pptx]
```

Available groups: `all`, `pptx`, `docx`, `xlsx`, `xls`, `pdf`, `outlook`, `az-doc-intel`, `audio-transcription`, `youtube-transcription`

## Core API

### MarkItDown Class

Main conversion interface:

```python
from markitdown import MarkItDown

md = MarkItDown()
result = md.convert(source)
```

#### Constructor

```python
MarkItDown(
    enable_builtins=True,       # Enable built-in converters
    enable_plugins=False,       # Enable 3rd-party plugins
    requests_session=None,      # Custom requests.Session
    llm_client=None,           # LLM client for image descriptions
    llm_model=None,            # LLM model name
    docintel_endpoint=None,    # Azure Document Intelligence endpoint
    docintel_credential=None,  # Azure credentials
    exiftool_path=None,        # Path to exiftool binary
    style_map=None             # Custom style mapping
)
```

#### Methods

**convert(source, \*, stream_info=None, **kwargs) → DocumentConverterResult\*\*

Converts input to Markdown. Source can be:

- File path (str or Path)
- URL (str)
- Binary stream (BinaryIO)
- HTTP Response object

**convert_local(path, \*, stream_info=None, **kwargs) → DocumentConverterResult\*\*

Convert local file by path.

**convert_stream(stream, \*, stream_info=None, **kwargs) → DocumentConverterResult\*\*

Convert from binary stream.

**convert_uri(uri, \*, stream_info=None, **kwargs) → DocumentConverterResult\*\*

Convert from URI (file://, data://, http://, https://).

**convert_response(response, \*, stream_info=None, **kwargs) → DocumentConverterResult\*\*

Convert from requests.Response object.

**register_converter(converter, \*, priority=0.0)**

Adds custom converter with priority (lower = higher priority).

**enable_builtins(**kwargs)\*\*

Enable built-in converters (called by default).

**enable_plugins(**kwargs)\*\*

Enable 3rd-party plugins.

### DocumentConverter Interface

Base class for format converters:

```python
class DocumentConverter:
    def accepts(self, file_stream: BinaryIO, stream_info: StreamInfo, **kwargs) -> bool:
        """Check if converter can handle the file"""
        pass

    def convert(self, file_stream: BinaryIO, stream_info: StreamInfo, **kwargs) -> DocumentConverterResult:
        """Convert file to markdown"""
        pass
```

### DocumentConverterResult

```python
class DocumentConverterResult:
    def __init__(self, markdown: str, *, title: str = None):
        self.markdown = markdown       # Converted Markdown text
        self.title = title            # Optional document title

    @property
    def text_content(self) -> str:    # Deprecated alias for markdown
        return self.markdown
```

### StreamInfo

Metadata about the input stream:

```python
from markitdown import StreamInfo

stream_info = StreamInfo(
    mimetype="application/pdf",
    extension=".pdf",
    charset="utf-8",
    filename="document.pdf",
    local_path="/path/to/file",
    url="https://example.com/doc.pdf"
)
```

## Supported Formats

| Format       | Extension                    | Feature Group           | Converter           |
| ------------ | ---------------------------- | ----------------------- | ------------------- |
| PDF          | `.pdf`                       | `pdf`                   | PdfConverter        |
| Word         | `.docx`                      | `docx`                  | DocxConverter       |
| Excel        | `.xlsx`                      | `xlsx`                  | XlsxConverter       |
| Excel Legacy | `.xls`                       | `xls`                   | XlsConverter        |
| PowerPoint   | `.pptx`                      | `pptx`                  | PptxConverter       |
| Outlook      | `.msg`                       | `outlook`               | OutlookMsgConverter |
| HTML         | `.html`, `.htm`              | Built-in                | HtmlConverter       |
| Images       | `.jpg`, `.png`, `.bmp`, etc. | Built-in                | ImageConverter      |
| Audio        | `.wav`, `.mp3`               | `audio-transcription`   | AudioConverter      |
| Text         | `.txt`, `.md`, `.py`, etc.   | Built-in                | PlainTextConverter  |
| CSV          | `.csv`                       | Built-in                | CsvConverter        |
| JSON         | `.json`                      | Built-in                | PlainTextConverter  |
| XML          | `.xml`                       | Built-in                | PlainTextConverter  |
| ZIP          | `.zip`                       | Built-in                | ZipConverter        |
| EPUB         | `.epub`                      | Built-in                | EpubConverter       |
| Jupyter      | `.ipynb`                     | Built-in                | IpynbConverter      |
| RSS          | RSS feeds                    | Built-in                | RssConverter        |
| YouTube      | YouTube URLs                 | `youtube-transcription` | YouTubeConverter    |
| Wikipedia    | Wikipedia URLs               | Built-in                | WikipediaConverter  |

## Usage Examples

### Basic File Conversion

```python
from markitdown import MarkItDown

md = MarkItDown()

# Convert local file
result = md.convert("document.pdf")
print(result.markdown)

# Convert from URL
result = md.convert("https://example.com/doc.pdf")
print(result.markdown)

# Convert with hints
from markitdown import StreamInfo
stream_info = StreamInfo(extension=".pdf")
result = md.convert("document", stream_info=stream_info)
```

### Stream Conversion

```python
# From binary stream
with open("document.pdf", "rb") as f:
    result = md.convert_stream(f)
    print(result.markdown)

# From BytesIO
import io
with open("document.pdf", "rb") as f:
    buffer = io.BytesIO(f.read())
    result = md.convert_stream(buffer)
```

### Custom Converter

```python
from markitdown import DocumentConverter, DocumentConverterResult

class CustomConverter(DocumentConverter):
    def accepts(self, file_stream, stream_info, **kwargs):
        return stream_info.extension == '.custom'

    def convert(self, file_stream, stream_info, **kwargs):
        content = file_stream.read().decode('utf-8')
        return DocumentConverterResult(f"# Custom\n{content}")

md = MarkItDown()
md.register_converter(CustomConverter(), priority=0.0)
```

### Error Handling

```python
from markitdown import MarkItDown
from markitdown._exceptions import (
    UnsupportedFormatException,
    FileConversionException,
    MissingDependencyException
)

md = MarkItDown()

try:
    result = md.convert("document.xyz")
    print(result.markdown)
except UnsupportedFormatException:
    print("Format not supported")
except FileConversionException as e:
    print(f"Conversion failed: {e}")
except MissingDependencyException as e:
    print(f"Missing dependency: {e}")
```

### LLM Integration

```python
from openai import OpenAI

client = OpenAI()
md = MarkItDown(llm_client=client, llm_model="gpt-4o")

# Images will be described using LLM
result = md.convert("image.jpg")
print(result.markdown)  # Contains AI-generated description
```

### Azure Document Intelligence

```python
md = MarkItDown(
    docintel_endpoint="https://myservice.cognitiveservices.azure.com/",
    docintel_credential=credential
)

result = md.convert("complex_document.pdf")
print(result.markdown)
```

## Plugin System

### Creating Plugins

Entry point in `pyproject.toml`:

```toml
[project.entry-points."markitdown.plugin"]
my_plugin = "my_package.plugin"
```

Plugin implementation:

```python
# my_package/plugin.py
def register_converters(markitdown_instance, **kwargs):
    """Called when plugins are enabled"""
    markitdown_instance.register_converter(MyCustomConverter())
```

### Using Plugins

```python
# Enable during construction
md = MarkItDown(enable_plugins=True)

# Or enable later
md = MarkItDown(enable_plugins=False)
md.enable_plugins()
```

## CLI Usage

```bash
# Basic conversion
markitdown document.pdf > output.md

# With output file
markitdown document.pdf -o output.md

# From stdin with hints
cat document.pdf | markitdown -x .pdf

# With plugins
markitdown document.pdf --use-plugins

# List plugins
markitdown --list-plugins

# Azure Document Intelligence
markitdown document.pdf -d -e "https://endpoint.cognitiveservices.azure.com/"
```
