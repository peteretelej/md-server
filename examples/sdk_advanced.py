#!/usr/bin/env python3
"""
Advanced SDK usage examples for md-server.

Demonstrates batch processing, concurrent operations, integration patterns,
and production-ready usage scenarios.
"""

import asyncio
import time
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass

from md_server import MDConverter, ConversionError, ConversionResult


@dataclass
class ProcessingStats:
    """Statistics for batch processing operations."""
    total_files: int = 0
    successful: int = 0
    failed: int = 0
    total_size: int = 0
    total_time: float = 0.0
    
    @property
    def success_rate(self) -> float:
        return (self.successful / self.total_files * 100) if self.total_files > 0 else 0.0


async def batch_file_processing():
    """Process multiple files concurrently."""
    print("=== Batch File Processing ===")
    
    converter = MDConverter(
        ocr_enabled=True,
        timeout=60,
        max_file_size_mb=100
    )
    
    # Simulate list of files to process
    file_paths = [
        "document1.pdf",
        "presentation.pptx", 
        "spreadsheet.xlsx",
        "image.png",
        "webpage.html"
    ]
    
    stats = ProcessingStats(total_files=len(file_paths))
    start_time = time.time()
    
    # Process files concurrently with semaphore for rate limiting
    semaphore = asyncio.Semaphore(3)  # Max 3 concurrent conversions
    
    async def process_single_file(file_path: str) -> tuple[str, ConversionResult | Exception]:
        async with semaphore:
            try:
                if Path(file_path).exists():
                    result = await converter.convert_file(file_path)
                    return file_path, result
                else:
                    # Simulate with text conversion for demo
                    result = await converter.convert_text(
                        f"<h1>Sample {file_path}</h1><p>Simulated content</p>",
                        mime_type="text/html"
                    )
                    return file_path, result
            except Exception as e:
                return file_path, e
    
    # Execute all conversions concurrently
    tasks = [process_single_file(path) for path in file_paths]
    results = await asyncio.gather(*tasks)
    
    # Process results
    for file_path, result in results:
        if isinstance(result, Exception):
            print(f"❌ Failed: {file_path} - {result}")
            stats.failed += 1
        else:
            print(f"✓ Success: {file_path} ({result.metadata.source_size} bytes)")
            stats.successful += 1
            stats.total_size += result.metadata.source_size
    
    stats.total_time = time.time() - start_time
    
    print(f"\n📊 Batch Processing Results:")
    print(f"  - Total files: {stats.total_files}")
    print(f"  - Successful: {stats.successful}")
    print(f"  - Failed: {stats.failed}")
    print(f"  - Success rate: {stats.success_rate:.1f}%")
    print(f"  - Total size: {stats.total_size:,} bytes")
    print(f"  - Processing time: {stats.total_time:.2f}s")


async def smart_url_processing():
    """Intelligently process URLs with different strategies."""
    print("\n=== Smart URL Processing ===")
    
    converter = MDConverter()
    
    urls = [
        "https://httpbin.org/html",           # Static HTML
        "https://httpbin.org/json",           # JSON API
        "https://github.com",                 # Complex page (might need JS)
        "https://docs.python.org/3/",         # Documentation
    ]
    
    async def smart_convert_url(url: str) -> ConversionResult:
        """Convert URL with smart strategy selection."""
        
        # Determine if JS rendering is likely needed
        js_indicators = ["github.com", "app.", "spa.", "dashboard"]
        needs_js = any(indicator in url for indicator in js_indicators)
        
        # Try conversion with appropriate strategy
        try:
            result = await converter.convert_url(
                url, 
                js_rendering=needs_js,
                extract_images=True
            )
            
            print(f"✓ {url}")
            print(f"  - Strategy: {'JS rendering' if needs_js else 'Static HTML'}")
            print(f"  - Size: {result.metadata.markdown_size} chars")
            print(f"  - Time: {result.metadata.processing_time:.2f}s")
            
            return result
            
        except ConversionError as e:
            print(f"❌ {url} - {e}")
            raise
    
    # Process URLs with different strategies
    for url in urls:
        try:
            await smart_convert_url(url)
        except ConversionError:
            continue  # Already logged


async def content_pipeline():
    """Demonstrate a content processing pipeline."""
    print("\n=== Content Processing Pipeline ===")
    
    class ContentPipeline:
        """A processing pipeline for content conversion."""
        
        def __init__(self):
            self.converter = MDConverter(
                clean_markdown=True,
                preserve_formatting=True
            )
            self.processed_count = 0
        
        async def process_content(self, content: bytes, filename: str) -> Dict[str, Any]:
            """Process content through the pipeline."""
            self.processed_count += 1
            
            # Step 1: Convert to markdown
            result = await self.converter.convert_content(content, filename=filename)
            
            # Step 2: Post-process markdown (custom logic)
            processed_markdown = self._post_process_markdown(result.markdown)
            
            # Step 3: Generate metadata
            pipeline_metadata = {
                "original_size": result.metadata.source_size,
                "markdown_size": len(processed_markdown),
                "processing_time": result.metadata.processing_time,
                "detected_format": result.metadata.detected_format,
                "pipeline_step": self.processed_count,
                "post_processed": True
            }
            
            return {
                "markdown": processed_markdown,
                "metadata": pipeline_metadata,
                "original_result": result
            }
        
        def _post_process_markdown(self, markdown: str) -> str:
            """Apply custom post-processing to markdown."""
            # Example post-processing steps
            lines = markdown.split('\n')
            
            # Add processing timestamp
            timestamp = f"*Processed at: {time.strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
            
            # Clean up extra whitespace
            cleaned_lines = []
            for line in lines:
                cleaned_line = line.strip()
                if cleaned_line or (cleaned_lines and cleaned_lines[-1]):
                    cleaned_lines.append(cleaned_line)
            
            return timestamp + '\n'.join(cleaned_lines)
    
    # Use the pipeline
    pipeline = ContentPipeline()
    
    # Sample content
    sample_contents = [
        (b"<h1>Document 1</h1><p>Content here</p>", "doc1.html"),
        (b"# Markdown\n\nSome **bold** text", "doc2.md"),
        (b"Plain text content", "doc3.txt")
    ]
    
    for content, filename in sample_contents:
        result = await pipeline.process_content(content, filename)
        
        print(f"✓ Processed: {filename}")
        print(f"  - Format: {result['metadata']['detected_format']}")
        print(f"  - Original size: {result['metadata']['original_size']} bytes")
        print(f"  - Markdown size: {result['metadata']['markdown_size']} chars")
        print(f"  - Pipeline step: {result['metadata']['pipeline_step']}")


async def error_recovery_patterns():
    """Demonstrate error recovery and retry patterns."""
    print("\n=== Error Recovery Patterns ===")
    
    from md_server import NetworkError, TimeoutError, FileSizeError
    
    class RobustConverter:
        """Converter with built-in retry and fallback logic."""
        
        def __init__(self):
            self.primary_converter = MDConverter(timeout=10)
            self.fallback_converter = MDConverter(
                timeout=30,
                max_file_size_mb=25,  # Smaller files for fallback
                clean_markdown=True
            )
            self.max_retries = 3
        
        async def convert_with_retry(self, url: str) -> ConversionResult:
            """Convert URL with retry logic and fallbacks."""
            
            # Primary attempt
            for attempt in range(self.max_retries):
                try:
                    result = await self.primary_converter.convert_url(url)
                    print(f"✓ Primary conversion succeeded (attempt {attempt + 1})")
                    return result
                    
                except TimeoutError:
                    print(f"⏰ Timeout on attempt {attempt + 1}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(1.0 * (attempt + 1))  # Exponential backoff
                        continue
                        
                except NetworkError as e:
                    print(f"🌐 Network error on attempt {attempt + 1}: {e}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2.0)
                        continue
                        
                except Exception as e:
                    print(f"❌ Unexpected error: {e}")
                    break
            
            # Fallback attempt with relaxed settings
            try:
                print("🔄 Trying fallback converter...")
                result = await self.fallback_converter.convert_url(url)
                print("✓ Fallback conversion succeeded")
                return result
                
            except Exception as e:
                print(f"❌ Fallback also failed: {e}")
                raise ConversionError(f"All conversion attempts failed for {url}")
    
    # Test robust converter
    robust = RobustConverter()
    
    test_urls = [
        "https://httpbin.org/html",      # Should work
        "https://httpbin.org/delay/5",   # Might timeout
        "https://invalid-url-12345.com", # Should fail
    ]
    
    for url in test_urls:
        try:
            print(f"\n🔗 Testing: {url}")
            result = await robust.convert_with_retry(url)
            print(f"✅ Final result: {len(result.markdown)} chars")
        except ConversionError as e:
            print(f"💥 Final failure: {e}")


async def monitoring_and_metrics():
    """Demonstrate monitoring and metrics collection."""
    print("\n=== Monitoring and Metrics ===")
    
    import logging
    from collections import defaultdict
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("conversion_monitor")
    
    class MonitoredConverter:
        """Converter with built-in monitoring and metrics."""
        
        def __init__(self):
            self.converter = MDConverter()
            self.metrics = defaultdict(int)
            self.timing_data = []
            
        async def convert_with_monitoring(self, file_path: str) -> ConversionResult:
            """Convert file with monitoring."""
            start_time = time.time()
            
            try:
                # Log start
                logger.info(f"Starting conversion: {file_path}")
                
                # Simulate file conversion
                result = await self.converter.convert_text(
                    f"<h1>Sample {file_path}</h1><p>Monitoring example</p>",
                    mime_type="text/html"
                )
                
                # Record metrics
                duration = time.time() - start_time
                self.metrics["successful_conversions"] += 1
                self.metrics["total_bytes_processed"] += result.metadata.source_size
                self.timing_data.append(duration)
                
                # Log success
                logger.info(
                    f"Conversion completed: {file_path} "
                    f"({result.metadata.source_size} bytes in {duration:.2f}s)"
                )
                
                return result
                
            except Exception as e:
                # Record error metrics
                self.metrics["failed_conversions"] += 1
                duration = time.time() - start_time
                
                # Log error
                logger.error(f"Conversion failed: {file_path} - {e} (after {duration:.2f}s)")
                raise
        
        def get_metrics_report(self) -> Dict[str, Any]:
            """Generate metrics report."""
            if not self.timing_data:
                return {"status": "no_data"}
            
            avg_time = sum(self.timing_data) / len(self.timing_data)
            max_time = max(self.timing_data)
            min_time = min(self.timing_data)
            
            return {
                "total_conversions": self.metrics["successful_conversions"] + self.metrics["failed_conversions"],
                "successful_conversions": self.metrics["successful_conversions"],
                "failed_conversions": self.metrics["failed_conversions"],
                "success_rate": (
                    self.metrics["successful_conversions"] / 
                    (self.metrics["successful_conversions"] + self.metrics["failed_conversions"]) * 100
                ) if (self.metrics["successful_conversions"] + self.metrics["failed_conversions"]) > 0 else 0,
                "total_bytes_processed": self.metrics["total_bytes_processed"],
                "timing": {
                    "average_seconds": avg_time,
                    "max_seconds": max_time,
                    "min_seconds": min_time,
                    "total_samples": len(self.timing_data)
                }
            }
    
    # Test monitored converter
    monitor = MonitoredConverter()
    
    test_files = ["doc1.pdf", "doc2.docx", "doc3.txt", "doc4.html"]
    
    for file_path in test_files:
        try:
            await monitor.convert_with_monitoring(file_path)
        except ConversionError:
            continue  # Error already logged
    
    # Generate report
    report = monitor.get_metrics_report()
    print("\n📈 Metrics Report:")
    print(f"  - Total conversions: {report['total_conversions']}")
    print(f"  - Success rate: {report['success_rate']:.1f}%")
    print(f"  - Total bytes processed: {report['total_bytes_processed']:,}")
    print(f"  - Average time: {report['timing']['average_seconds']:.2f}s")
    print(f"  - Max time: {report['timing']['max_seconds']:.2f}s")


async def main():
    """Run all advanced examples."""
    print("MD Server SDK - Advanced Examples")
    print("=" * 50)
    
    await batch_file_processing()
    await smart_url_processing()
    await content_pipeline()
    await error_recovery_patterns()
    await monitoring_and_metrics()
    
    print("\n🎉 All advanced examples completed!")


if __name__ == "__main__":
    asyncio.run(main())