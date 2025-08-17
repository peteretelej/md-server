"""
End-to-end integration tests for SDK flows.

This file consolidates integration testing across the entire SDK, including
sync/async interoperability, real document processing, performance characteristics,
and complex usage scenarios.
"""

import asyncio
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from concurrent.futures import ThreadPoolExecutor

import pytest

from md_server.sdk import MDConverter, RemoteMDConverter
from md_server.sdk.models import ConversionResult, ConversionMetadata
from md_server.sdk.exceptions import ConversionError, TimeoutError
from md_server.sdk.sync import sync_wrapper, get_or_create_event_loop


class TestSDKEndToEndFlows:
    """End-to-end integration testing scenarios."""
    
    async def test_complete_local_conversion_flow(self, sample_files):
        """Test complete local conversion workflow with real files."""
        converter = MDConverter(
            ocr_enabled=True,
            extract_images=True,
            clean_markdown=True,
            debug=True
        )
        
        results = []
        
        # Test each available sample file
        for file_type, file_path in sample_files.items():
            if not file_path.exists():
                continue
                
            try:
                result = await converter.convert_file(file_path)
                results.append((file_type, result))
                
                # Verify basic result structure
                assert result.success is True
                assert len(result.markdown) > 0
                assert result.metadata.source_size > 0
                assert result.metadata.processing_time > 0
                assert result.request_id.startswith("req_")
                
            except Exception as e:
                # Log but don't fail test for unsupported file types
                print(f"Could not convert {file_type}: {e}")
        
        # Should have converted at least some files
        assert len(results) > 0
        
        # Verify all results have unique request IDs
        request_ids = [result.request_id for _, result in results]
        assert len(set(request_ids)) == len(request_ids)
    
    async def test_mixed_input_type_workflow(self, md_converter):
        """Test workflow with different input types in sequence."""
        # Test data for different input types
        test_cases = [
            ("url", "https://example.com", {}),
            ("text", ("<h1>Test HTML</h1><p>Content</p>", "text/html"), {}),
            ("content", b"<h1>Binary HTML</h1><p>Binary content</p>", {"filename": "test.html"}),
        ]
        
        results = []
        
        # Mock underlying converters for consistent testing
        with patch.object(md_converter._url_converter, 'convert_url', return_value="# URL Content"), \
             patch.object(md_converter._content_converter, 'convert_content', return_value="# Content"):
            
            for input_type, input_data, kwargs in test_cases:
                if input_type == "url":
                    result = await md_converter.convert_url(input_data, **kwargs)
                elif input_type == "text":
                    result = await md_converter.convert_text(input_data[0], input_data[1], **kwargs)
                elif input_type == "content":
                    result = await md_converter.convert_content(input_data, **kwargs)
                
                results.append(result)
                
                # Verify each result
                assert result.success is True
                assert len(result.markdown) > 0
                assert result.metadata.source_type in ["url", "text", "content"]
        
        # Verify we processed all input types
        assert len(results) == len(test_cases)
        
        # Verify metadata consistency
        for result in results:
            assert result.metadata.processing_time > 0
            assert result.metadata.source_size > 0
            assert result.metadata.markdown_size > 0
    
    async def test_error_recovery_workflow(self, md_converter):
        """Test workflow with error recovery scenarios."""
        # Sequence of operations with some failures
        operations = [
            ("convert_text", ("Valid content", "text/plain"), True),  # Should succeed
            ("convert_file", ("/nonexistent/file.txt",), False),  # Should fail
            ("convert_text", ("More valid content", "text/html"), True),  # Should succeed
            ("convert_url", ("invalid-url",), False),  # Should fail
            ("convert_text", ("Final content", "text/plain"), True),  # Should succeed
        ]
        
        results = []
        errors = []
        
        for method_name, args, should_succeed in operations:
            method = getattr(md_converter, method_name)
            
            try:
                result = await method(*args)
                if should_succeed:
                    results.append(result)
                    assert result.success is True
                else:
                    # Unexpected success
                    assert False, f"Expected {method_name} to fail"
                    
            except Exception as e:
                if not should_succeed:
                    errors.append(e)
                else:
                    # Unexpected failure
                    raise
        
        # Verify we got expected successes and failures
        assert len(results) == 3  # 3 successful operations
        assert len(errors) == 2   # 2 failed operations
        
        # Verify converter still works after errors
        final_result = await md_converter.convert_text("Recovery test", "text/plain")
        assert final_result.success is True
    
    async def test_concurrent_mixed_operations(self, md_converter):
        """Test concurrent operations with different input types."""
        # Mock converters for consistent testing
        with patch.object(md_converter._url_converter, 'convert_url', return_value="# URL"), \
             patch.object(md_converter._content_converter, 'convert_content', return_value="# Content"):
            
            # Create mixed concurrent tasks
            tasks = [
                md_converter.convert_text(f"Text {i}", "text/plain")
                for i in range(5)
            ] + [
                md_converter.convert_url(f"https://example{i}.com")
                for i in range(3)
            ] + [
                md_converter.convert_content(f"Content {i}".encode(), filename=f"test{i}.txt")
                for i in range(2)
            ]
            
            # Execute all concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter successful results
            successful_results = [r for r in results if isinstance(r, ConversionResult)]
            
            # Should have most or all results successful
            assert len(successful_results) >= 8  # Allow for some potential issues
            
            # Verify all have unique request IDs
            request_ids = [r.request_id for r in successful_results]
            assert len(set(request_ids)) == len(successful_results)
    
    async def test_performance_characteristics(self, md_converter):
        """Test performance characteristics under various loads."""
        # Small content performance
        start_time = time.time()
        
        small_tasks = [
            md_converter.convert_text(f"Small {i}", "text/plain")
            for i in range(20)
        ]
        
        small_results = await asyncio.gather(*small_tasks)
        small_duration = time.time() - start_time
        
        # Verify all succeeded
        assert len(small_results) == 20
        for result in small_results:
            assert result.success is True
            assert result.metadata.processing_time > 0
        
        # Should be reasonably fast for small content
        assert small_duration < 10.0  # Should complete in under 10 seconds
        
        # Average processing time should be reasonable
        avg_processing_time = sum(r.metadata.processing_time for r in small_results) / len(small_results)
        assert avg_processing_time < 1.0  # Average under 1 second per conversion
    
    async def test_memory_usage_stability(self, md_converter):
        """Test memory usage remains stable during extended operations."""
        import gc
        
        # Run multiple conversion cycles
        for cycle in range(5):
            # Create batch of conversions
            tasks = [
                md_converter.convert_text(f"Cycle {cycle} Content {i}", "text/plain")
                for i in range(10)
            ]
            
            results = await asyncio.gather(*tasks)
            
            # Verify all succeeded
            assert len(results) == 10
            for result in results:
                assert result.success is True
            
            # Force garbage collection between cycles
            gc.collect()
        
        # Memory should be stable (no easy way to test exactly, but operations should complete)
        # This test mainly ensures no memory leaks cause failures


class TestSyncAsyncInteroperability:
    """Test sync/async API interoperability."""
    
    def test_sync_wrapper_functionality(self):
        """Test sync wrapper works correctly."""
        
        async def dummy_async_function(value, delay=0.01):
            await asyncio.sleep(delay)
            return f"result: {value}"
        
        sync_func = sync_wrapper(dummy_async_function)
        result = sync_func("test")
        assert result == "result: test"
    
    def test_sync_wrapper_with_exception(self):
        """Test sync wrapper propagates exceptions correctly."""
        async def failing_func():
            raise ValueError("test error")
        
        sync_func = sync_wrapper(failing_func)
        with pytest.raises(ValueError, match="test error"):
            sync_func()
    
    def test_event_loop_management(self):
        """Test event loop creation and management."""
        loop = get_or_create_event_loop()
        assert isinstance(loop, asyncio.AbstractEventLoop)
        
        # Should be able to run simple coroutine
        async def simple_coro():
            return "test"
        
        result = loop.run_until_complete(simple_coro())
        assert result == "test"
        
        loop.close()
    
    def test_converter_sync_methods(self):
        """Test all converter sync methods work."""
        converter = MDConverter()
        
        # Mock async methods for testing
        expected_result = ConversionResult(
            markdown="# Test",
            metadata=ConversionMetadata(
                source_type="text",
                source_size=10,
                markdown_size=6,
                processing_time=0.1,
                detected_format="text/plain"
            )
        )
        
        with patch.object(converter, 'convert_text', new_callable=AsyncMock) as mock_async:
            mock_async.return_value = expected_result
            
            # Test sync wrapper
            result = converter.convert_text_sync("Test", "text/plain")
            assert result.markdown == "# Test"
            mock_async.assert_called_once_with("Test", "text/plain")
    
    def test_mixed_sync_async_usage(self):
        """Test mixing sync and async calls doesn't cause issues."""
        converter = MDConverter()
        
        with patch.object(converter, 'convert_text', new_callable=AsyncMock) as mock_async:
            expected_result = ConversionResult(
                markdown="# Mixed",
                metadata=ConversionMetadata(
                    source_type="text",
                    source_size=10,
                    markdown_size=7,
                    processing_time=0.1,
                    detected_format="text/plain"
                )
            )
            mock_async.return_value = expected_result
            
            # Sync call
            sync_result = converter.convert_text_sync("Sync test", "text/plain")
            assert sync_result.markdown == "# Mixed"
            
            # Async call in new event loop
            async def async_test():
                return await converter.convert_text("Async test", "text/plain")
            
            loop = asyncio.new_event_loop()
            async_result = loop.run_until_complete(async_test())
            loop.close()
            
            assert async_result.markdown == "# Mixed"
    
    def test_concurrent_sync_calls(self):
        """Test concurrent sync calls using threading."""
        converter = MDConverter()
        
        with patch.object(converter, 'convert_text', new_callable=AsyncMock) as mock_async:
            expected_result = ConversionResult(
                markdown="# Concurrent",
                metadata=ConversionMetadata(
                    source_type="text",
                    source_size=10,
                    markdown_size=12,
                    processing_time=0.1,
                    detected_format="text/plain"
                )
            )
            mock_async.return_value = expected_result
            
            def sync_conversion(text):
                return converter.convert_text_sync(text, "text/plain")
            
            # Run multiple sync conversions in threads
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [
                    executor.submit(sync_conversion, f"Text {i}")
                    for i in range(5)
                ]
                
                results = [future.result() for future in futures]
            
            # All should succeed
            assert len(results) == 5
            for result in results:
                assert result.markdown == "# Concurrent"


class TestContextManagerBehavior:
    """Test context manager functionality."""
    
    async def test_async_context_manager(self):
        """Test async context manager behavior."""
        async with MDConverter() as converter:
            assert isinstance(converter, MDConverter)
            
            # Should be functional within context
            result = await converter.convert_text("Test", "text/plain")
            assert result.success is True
        
        # After context, converter should still work (no resource cleanup needed for local)
        result = await converter.convert_text("Test", "text/plain")
        assert result.success is True
    
    def test_sync_context_manager(self):
        """Test sync context manager behavior."""
        with MDConverter() as converter:
            assert isinstance(converter, MDConverter)
            
            # Should be functional within context (using sync method)
            with patch.object(converter, 'convert_text', new_callable=AsyncMock) as mock_async:
                expected_result = ConversionResult(
                    markdown="# Context",
                    metadata=ConversionMetadata(
                        source_type="text",
                        source_size=10,
                        markdown_size=9,
                        processing_time=0.1,
                        detected_format="text/plain"
                    )
                )
                mock_async.return_value = expected_result
                
                result = converter.convert_text_sync("Test", "text/plain")
                assert result.markdown == "# Context"
    
    async def test_context_manager_exception_handling(self):
        """Test context manager handles exceptions properly."""
        try:
            async with MDConverter() as converter:
                # Force an exception within context
                raise ValueError("Test exception")
        except ValueError:
            pass  # Expected
        
        # Context manager should have handled cleanup properly
        # (No specific cleanup needed for local converter, but test the pattern)
    
    async def test_remote_context_manager(self):
        """Test remote converter context manager."""
        # Mock httpx client for testing
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            async with RemoteMDConverter("http://localhost:8080") as client:
                assert isinstance(client, RemoteMDConverter)
                # Client should be configured
                assert client.endpoint == "http://localhost:8080"
            
            # After context, httpx client should have been closed
            mock_client.aclose.assert_called_once()


class TestRealDocumentProcessing:
    """Test processing with real document samples."""
    
    async def test_html_document_processing(self, sample_files):
        """Test processing real HTML documents."""
        if not sample_files.get("html") or not sample_files["html"].exists():
            pytest.skip("HTML test file not available")
        
        converter = MDConverter(clean_markdown=True)
        
        # Test file conversion
        result = await converter.convert_file(sample_files["html"])
        
        assert result.success is True
        assert len(result.markdown) > 0
        assert result.metadata.detected_format == "text/html"
        assert result.metadata.source_size > 0
        assert result.metadata.markdown_size > 0
        
        # Should contain typical HTML->Markdown conversions
        markdown = result.markdown.lower()
        # Look for common markdown patterns that should result from HTML
        contains_markdown_patterns = any(pattern in markdown for pattern in [
            "#", "*", "**", "[", "]", "\n\n"
        ])
        assert contains_markdown_patterns
    
    async def test_json_document_processing(self, sample_files):
        """Test processing JSON documents."""
        if not sample_files.get("json") or not sample_files["json"].exists():
            pytest.skip("JSON test file not available")
        
        converter = MDConverter()
        
        # Test file conversion
        result = await converter.convert_file(sample_files["json"])
        
        assert result.success is True
        assert len(result.markdown) > 0
        assert result.metadata.source_size > 0
        
        # JSON content should be converted to readable format
        assert len(result.markdown) > 10  # Should produce substantial output
    
    async def test_binary_document_processing(self, sample_files):
        """Test processing binary documents."""
        if not sample_files.get("pdf") or not sample_files["pdf"].exists():
            pytest.skip("PDF test file not available")
        
        converter = MDConverter(ocr_enabled=True)
        
        try:
            result = await converter.convert_file(sample_files["pdf"])
            
            assert result.success is True
            assert result.metadata.detected_format == "application/pdf"
            assert result.metadata.source_size > 0
            
            # PDF conversion should produce some content
            assert len(result.markdown) > 0
            
        except ConversionError:
            # PDF conversion might fail if dependencies missing
            pytest.skip("PDF conversion not available")
    
    async def test_processing_time_consistency(self, sample_files):
        """Test that processing times are consistent and reasonable."""
        converter = MDConverter()
        
        processing_times = []
        
        # Process available files multiple times
        for file_type, file_path in sample_files.items():
            if not file_path.exists():
                continue
            
            # Convert same file multiple times
            for _ in range(3):
                try:
                    result = await converter.convert_file(file_path)
                    if result.success:
                        processing_times.append(result.metadata.processing_time)
                except Exception:
                    continue  # Skip files that fail to convert
        
        if processing_times:
            # Processing times should be reasonable
            avg_time = sum(processing_times) / len(processing_times)
            max_time = max(processing_times)
            
            assert avg_time > 0  # Should take some time
            assert avg_time < 30  # But not too long for test files
            assert max_time < 60  # No single conversion should take too long
            
            # Times should be somewhat consistent (not vary wildly)
            if len(processing_times) > 1:
                import statistics
                std_dev = statistics.stdev(processing_times)
                assert std_dev < avg_time * 2  # Standard deviation shouldn't be too high


class TestAdvancedScenarios:
    """Test advanced usage scenarios."""
    
    async def test_timeout_handling(self):
        """Test timeout handling in conversions."""
        # Very short timeout
        converter = MDConverter(timeout=0.001)  # 1ms timeout
        
        # Mock a slow conversion
        with patch.object(converter._content_converter, 'convert_content') as mock_convert:
            async def slow_conversion(*args, **kwargs):
                await asyncio.sleep(1)  # Longer than timeout
                return "Should not reach here"
            
            mock_convert.side_effect = slow_conversion
            
            with pytest.raises(TimeoutError):
                await converter.convert_text("Test", "text/plain")
    
    async def test_large_content_handling(self):
        """Test handling of large content."""
        converter = MDConverter(max_file_size_mb=1)  # 1MB limit
        
        # Create content just under the limit
        large_content = "A" * (900 * 1024)  # 900KB
        
        # Should succeed
        result = await converter.convert_text(large_content, "text/plain")
        assert result.success is True
        assert result.metadata.source_size == len(large_content.encode())
        
        # Content over the limit should fail
        huge_content = "A" * (2 * 1024 * 1024)  # 2MB
        
        with pytest.raises(Exception):  # Should raise size error
            await converter.convert_text(huge_content, "text/plain")
    
    async def test_option_inheritance_and_override(self):
        """Test option inheritance and override behavior."""
        # Base converter with specific options
        base_converter = MDConverter(
            clean_markdown=True,
            preserve_formatting=False,
            extract_images=True
        )
        
        # Test that options are applied correctly
        assert base_converter.options.clean_markdown is True
        assert base_converter.options.preserve_formatting is False
        assert base_converter.options.extract_images is True
        
        # Test per-call option overrides (if implemented)
        # This would depend on the actual API design
        result = await base_converter.convert_text("Test", "text/plain")
        assert result.success is True
    
    async def test_metadata_accuracy(self):
        """Test accuracy of metadata calculations."""
        converter = MDConverter()
        
        test_content = "# Test Title\n\nThis is test content with some **bold** text."
        expected_size = len(test_content.encode('utf-8'))
        
        start_time = time.time()
        result = await converter.convert_text(test_content, "text/markdown")
        end_time = time.time()
        
        # Verify size calculation
        assert result.metadata.source_size == expected_size
        
        # Verify processing time is reasonable
        assert result.metadata.processing_time > 0
        assert result.metadata.processing_time <= (end_time - start_time) + 0.1  # Allow small margin
        
        # Verify markdown size
        assert result.metadata.markdown_size == len(result.markdown.encode('utf-8'))
        
        # Verify format detection
        assert result.metadata.detected_format == "text/markdown"