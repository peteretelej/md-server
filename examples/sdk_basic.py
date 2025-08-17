#!/usr/bin/env python3
"""
Basic SDK usage examples for md-server.

Demonstrates common conversion scenarios using the Python SDK.
"""

import asyncio
from pathlib import Path
from md_server import MDConverter, ConversionError


async def basic_file_conversion():
    """Convert a local file to markdown."""
    print("=== Basic File Conversion ===")

    converter = MDConverter()

    try:
        # Convert a PDF file
        result = await converter.convert_file("sample.pdf")

        print(f"✓ Converted {result.metadata.source_size} bytes")
        print(f"✓ Generated {result.metadata.markdown_size} chars of markdown")
        print(f"✓ Processing took {result.metadata.processing_time:.2f}s")
        print(f"✓ Detected format: {result.metadata.detected_format}")

        # Save the result
        output_path = Path("output.md")
        output_path.write_text(result.markdown)
        print(f"✓ Saved to {output_path}")

    except FileNotFoundError:
        print("❌ File not found: sample.pdf")
    except ConversionError as e:
        print(f"❌ Conversion failed: {e}")


async def basic_url_conversion():
    """Convert a web page to markdown."""
    print("\n=== Basic URL Conversion ===")

    converter = MDConverter()

    try:
        # Convert a static web page
        result = await converter.convert_url("https://httpbin.org/html")

        print("✓ Converted URL content")
        print(f"✓ Generated {result.metadata.markdown_size} chars of markdown")
        print(f"✓ Processing took {result.metadata.processing_time:.2f}s")

        # Print first 200 characters of markdown
        preview = (
            result.markdown[:200] + "..."
            if len(result.markdown) > 200
            else result.markdown
        )
        print(f"✓ Preview: {preview}")

    except ConversionError as e:
        print(f"❌ Conversion failed: {e}")


async def basic_text_conversion():
    """Convert text with MIME type to markdown."""
    print("\n=== Basic Text Conversion ===")

    converter = MDConverter()

    # HTML content
    html_content = """
    <html>
        <head><title>Sample Document</title></head>
        <body>
            <h1>Main Title</h1>
            <p>This is a <strong>sample</strong> HTML document.</p>
            <ul>
                <li>Item 1</li>
                <li>Item 2</li>
            </ul>
        </body>
    </html>
    """

    try:
        result = await converter.convert_text(html_content, mime_type="text/html")

        print("✓ Converted HTML text")
        print(f"✓ Generated {result.metadata.markdown_size} chars of markdown")
        print(f"✓ Result:\n{result.markdown}")

    except ConversionError as e:
        print(f"❌ Conversion failed: {e}")


async def basic_content_conversion():
    """Convert binary content to markdown."""
    print("\n=== Basic Content Conversion ===")

    converter = MDConverter()

    # Create some sample content (simulating a downloaded file)
    sample_html = b"""<!DOCTYPE html>
<html>
<head><title>Downloaded Content</title></head>
<body>
    <h1>Downloaded Document</h1>
    <p>This content was downloaded from an API.</p>
</body>
</html>"""

    try:
        result = await converter.convert_content(
            sample_html, filename="downloaded.html"
        )

        print("✓ Converted binary content")
        print(f"✓ Generated {result.metadata.markdown_size} chars of markdown")
        print(f"✓ Detected format: {result.metadata.detected_format}")
        print(f"✓ Result:\n{result.markdown}")

    except ConversionError as e:
        print(f"❌ Conversion failed: {e}")


async def configured_converter():
    """Use converter with custom configuration."""
    print("\n=== Configured Converter ===")

    # Create converter with custom settings
    converter = MDConverter(
        ocr_enabled=True,  # Enable OCR for images/scanned PDFs
        js_rendering=True,  # Enable JavaScript for SPAs
        timeout=60,  # Longer timeout
        max_file_size_mb=100,  # Larger file size limit
        extract_images=True,  # Extract embedded images
        preserve_formatting=True,  # Keep complex formatting
        debug=True,  # Enable debug logging
    )

    print("✓ Created converter with custom configuration:")
    print(f"  - OCR enabled: {converter.options.ocr_enabled}")
    print(f"  - JS rendering: {converter.options.js_rendering}")
    print(f"  - Timeout: {converter.options.timeout}s")
    print(f"  - Max file size: {converter.options.max_file_size_mb}MB")


async def sync_api_example():
    """Demonstrate synchronous API usage."""
    print("\n=== Synchronous API ===")

    converter = MDConverter()

    # HTML content for sync conversion
    html = "<h1>Sync Example</h1><p>Using synchronous API</p>"

    try:
        # Use sync version - no await needed
        result = converter.convert_text_sync(html, mime_type="text/html")

        print("✓ Sync conversion completed")
        print(f"✓ Result: {result.markdown}")

    except ConversionError as e:
        print(f"❌ Sync conversion failed: {e}")


async def error_handling_example():
    """Demonstrate proper error handling."""
    print("\n=== Error Handling ===")

    from md_server import InvalidInputError

    converter = MDConverter(max_file_size_mb=1)  # Very small limit for demo

    # Try to convert non-existent file
    try:
        await converter.convert_file("nonexistent.pdf")
    except InvalidInputError as e:
        print(f"✓ Caught expected error: {e}")

    # Try to convert invalid URL
    try:
        await converter.convert_url("not-a-valid-url")
    except InvalidInputError as e:
        print(f"✓ Caught expected error: {e}")

    # Try to convert empty text
    try:
        await converter.convert_text("", mime_type="text/html")
    except InvalidInputError as e:
        print(f"✓ Caught expected error: {e}")


async def main():
    """Run all basic examples."""
    print("MD Server SDK - Basic Examples")
    print("=" * 40)

    await basic_file_conversion()
    await basic_url_conversion()
    await basic_text_conversion()
    await basic_content_conversion()
    await configured_converter()
    await sync_api_example()
    await error_handling_example()

    print("\n✓ All examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
