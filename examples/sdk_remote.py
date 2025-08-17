#!/usr/bin/env python3
"""
Remote SDK usage examples for md-server.

Demonstrates connecting to remote md-server instances, handling authentication,
and managing distributed conversion workflows.
"""

import asyncio
import os
from pathlib import Path
from typing import List, Optional

from md_server import MDConverter, ConversionError, RemoteMDConverter


async def basic_remote_usage():
    """Basic remote converter usage."""
    print("=== Basic Remote Usage ===")

    # Connect to remote md-server
    # Note: Replace with your actual endpoint
    remote_converter = MDConverter.remote(
        endpoint="http://localhost:8080",  # Local server for demo
        api_key=os.getenv("MD_SERVER_API_KEY"),  # Optional API key
        timeout=30,
    )

    try:
        # Test connection with a simple conversion
        result = await remote_converter.convert_text(
            "<h1>Remote Test</h1><p>Testing remote conversion</p>",
            mime_type="text/html",
        )

        print("✓ Remote conversion successful")
        print(f"✓ Generated {result.metadata.markdown_size} chars of markdown")
        print(f"✓ Processing time: {result.metadata.processing_time:.2f}s")
        print(f"✓ Result: {result.markdown}")

    except ConversionError as e:
        print(f"❌ Remote conversion failed: {e}")
    except Exception as e:
        print(f"❌ Connection error: {e}")


async def authenticated_remote_usage():
    """Demonstrate authenticated remote access."""
    print("\n=== Authenticated Remote Usage ===")

    # Get API key from environment
    api_key = os.getenv("MD_SERVER_API_KEY")

    if not api_key:
        print("⚠️  No API key found in MD_SERVER_API_KEY environment variable")
        print("   Using unauthenticated access...")

    # Create authenticated client
    auth_converter = MDConverter.remote(
        endpoint="http://localhost:8080", api_key=api_key, timeout=60
    )

    try:
        # Convert a file using authenticated endpoint
        sample_content = b"""
        <!DOCTYPE html>
        <html>
        <head><title>Authenticated Test</title></head>
        <body>
            <h1>Secure Document</h1>
            <p>This conversion was performed with authentication.</p>
            <ul>
                <li>Feature 1</li>
                <li>Feature 2</li>
            </ul>
        </body>
        </html>
        """

        result = await auth_converter.convert_content(
            sample_content, filename="secure_doc.html"
        )

        print("✓ Authenticated conversion successful")
        print(f"✓ Request ID: {result.request_id}")
        print(f"✓ Detected format: {result.metadata.detected_format}")

    except ConversionError as e:
        print(f"❌ Authenticated conversion failed: {e}")


async def remote_file_processing():
    """Process local files using remote converter."""
    print("\n=== Remote File Processing ===")

    remote = MDConverter.remote("http://localhost:8080")

    # Simulate processing local files through remote server
    local_files = ["document1.html", "presentation.md", "data.csv"]

    for filename in local_files:
        try:
            # Create sample content for demo
            if filename.endswith(".html"):
                content = (
                    f"<h1>{filename}</h1><p>HTML content for {filename}</p>".encode()
                )
            elif filename.endswith(".md"):
                content = f"# {filename}\n\nMarkdown content for {filename}".encode()
            elif filename.endswith(".csv"):
                content = f"name,value\n{filename},123\ndata,456".encode()
            else:
                content = f"Plain text content for {filename}".encode()

            # Send to remote server
            result = await remote.convert_content(content, filename=filename)

            print(f"✓ Processed {filename} remotely")
            print(f"  - Original size: {result.metadata.source_size} bytes")
            print(f"  - Markdown size: {result.metadata.markdown_size} chars")
            print(f"  - Remote processing time: {result.metadata.processing_time:.2f}s")

        except ConversionError as e:
            print(f"❌ Failed to process {filename}: {e}")


async def remote_url_processing():
    """Process URLs using remote converter."""
    print("\n=== Remote URL Processing ===")

    remote = MDConverter.remote("http://localhost:8080")

    urls = [
        "https://httpbin.org/html",
        "https://httpbin.org/json",
        "https://docs.python.org/3/library/asyncio.html",
    ]

    for url in urls:
        try:
            print(f"🌐 Processing URL: {url}")
            result = await remote.convert_url(url, js_rendering=False)

            print("✓ Remote URL conversion successful")
            print(f"  - Content size: {result.metadata.markdown_size} chars")
            print(f"  - Processing time: {result.metadata.processing_time:.2f}s")

            # Save result to file
            filename = url.replace("https://", "").replace("/", "_") + ".md"
            Path(filename).write_text(result.markdown)
            print(f"  - Saved to: {filename}")

        except ConversionError as e:
            print(f"❌ Failed to process {url}: {e}")


async def distributed_processing():
    """Demonstrate distributed processing across multiple remote servers."""
    print("\n=== Distributed Processing ===")

    class DistributedConverter:
        """Manages conversion across multiple remote servers."""

        def __init__(self, endpoints: List[str], api_key: Optional[str] = None):
            self.converters = [
                MDConverter.remote(endpoint, api_key=api_key, timeout=30)
                for endpoint in endpoints
            ]
            self.current_server = 0

        def get_next_converter(self) -> RemoteMDConverter:
            """Round-robin server selection."""
            converter = self.converters[self.current_server]
            self.current_server = (self.current_server + 1) % len(self.converters)
            return converter

        async def convert_with_failover(self, content: bytes, filename: str):
            """Convert with automatic failover between servers."""
            last_error = None

            for i, converter in enumerate(self.converters):
                try:
                    print(f"  Trying server {i + 1}...")
                    result = await converter.convert_content(content, filename=filename)
                    print(f"  ✓ Success on server {i + 1}")
                    return result

                except Exception as e:
                    print(f"  ❌ Server {i + 1} failed: {e}")
                    last_error = e
                    continue

            raise ConversionError(f"All servers failed. Last error: {last_error}")

        async def distributed_batch_convert(self, files: List[tuple]):
            """Process files across multiple servers concurrently."""

            async def process_file(file_data):
                content, filename = file_data
                converter = self.get_next_converter()
                return await converter.convert_content(content, filename=filename)

            # Process all files concurrently across servers
            tasks = [process_file(file_data) for file_data in files]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            return results

    # Demo with multiple endpoints (using same local server for demo)
    # In practice, these would be different server instances
    distributed = DistributedConverter(
        [
            "http://localhost:8080",
            "http://localhost:8080",  # In practice: different servers
            "http://localhost:8080",  # In practice: different servers
        ]
    )

    # Sample files for distributed processing
    sample_files = [
        (b"<h1>Doc 1</h1><p>Content 1</p>", "doc1.html"),
        (b"<h1>Doc 2</h1><p>Content 2</p>", "doc2.html"),
        (b"<h1>Doc 3</h1><p>Content 3</p>", "doc3.html"),
        (b"<h1>Doc 4</h1><p>Content 4</p>", "doc4.html"),
    ]

    print(f"📤 Processing {len(sample_files)} files across distributed servers...")

    results = await distributed.distributed_batch_convert(sample_files)

    successful = sum(1 for r in results if not isinstance(r, Exception))
    failed = len(results) - successful

    print("✅ Distributed processing complete:")
    print(f"  - Successful: {successful}")
    print(f"  - Failed: {failed}")

    # Test failover
    print("\n🔄 Testing failover capability...")
    try:
        result = await distributed.convert_with_failover(
            b"<h1>Failover Test</h1><p>Testing server failover</p>",
            "failover_test.html",
        )
        print(f"✓ Failover successful: {len(result.markdown)} chars")
    except ConversionError as e:
        print(f"❌ All servers failed: {e}")


async def remote_context_manager():
    """Demonstrate proper resource management with remote converters."""
    print("\n=== Remote Context Manager ===")

    # Using async context manager for proper cleanup
    async with MDConverter.remote("http://localhost:8080") as converter:
        try:
            # Multiple operations in the same session
            html_result = await converter.convert_text(
                "<h1>Context Manager Test</h1>", mime_type="text/html"
            )

            url_result = await converter.convert_url("https://httpbin.org/html")

            print(f"✓ HTML conversion: {len(html_result.markdown)} chars")
            print(f"✓ URL conversion: {len(url_result.markdown)} chars")
            print("✓ Context manager cleanup handled automatically")

        except ConversionError as e:
            print(f"❌ Conversion failed: {e}")

    print("✓ Context manager exited, resources cleaned up")


async def sync_remote_api():
    """Demonstrate synchronous remote API usage."""
    print("\n=== Synchronous Remote API ===")

    remote = MDConverter.remote("http://localhost:8080")

    # Use sync methods for non-async environments
    try:
        html = "<h1>Sync Remote</h1><p>Using sync API with remote server</p>"
        result = remote.convert_text_sync(html, mime_type="text/html")

        print("✓ Sync remote conversion successful")
        print(f"✓ Result: {result.markdown}")

    except ConversionError as e:
        print(f"❌ Sync remote conversion failed: {e}")


async def main():
    """Run all remote examples."""
    print("MD Server SDK - Remote Examples")
    print("=" * 45)
    print("Note: These examples assume a local md-server running on localhost:8080")
    print("Start with: uvx md-server --host localhost --port 8080")
    print("=" * 45)

    await basic_remote_usage()
    await authenticated_remote_usage()
    await remote_file_processing()
    await remote_url_processing()
    await distributed_processing()
    await remote_context_manager()
    await sync_remote_api()

    print("\n🚀 All remote examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
