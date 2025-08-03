import pytest
import asyncio
import time
from unittest.mock import Mock, patch
from io import BytesIO

from md_server.adapters.markitdown_adapter import MarkItDownAdapter
from md_server.core.exceptions import MarkdownConversionError, ConversionTimeoutError
from md_server.core.markitdown_config import MarkItDownConfig


class TestMarkItDownAdapter:
    def test_init_with_defaults(self):
        adapter = MarkItDownAdapter()
        assert adapter.timeout_seconds == 30
        assert adapter._markitdown_instance is None
        assert adapter._custom_converters_registered is False

    def test_init_with_custom_config(self):
        config = MarkItDownConfig(timeout_seconds=60)
        adapter = MarkItDownAdapter(config=config)
        assert adapter.timeout_seconds == 60
        assert adapter.config == config

    def test_init_with_parameter_overrides(self):
        config = MarkItDownConfig(timeout_seconds=30)
        adapter = MarkItDownAdapter(
            config=config,
            timeout_seconds=45,
            enable_plugins=True,
            enable_builtins=False,
        )
        assert adapter.timeout_seconds == 45
        assert adapter.config.enable_plugins is True
        assert adapter.config.enable_builtins is False

    def test_conversion_context_success(self):
        adapter = MarkItDownAdapter()

        with adapter._conversion_context("test"):
            pass

        assert adapter._metrics["conversions_total"] == 1
        assert adapter._metrics["conversions_successful"] == 1
        assert adapter._metrics["conversions_failed"] == 0

    def test_conversion_context_failure(self):
        adapter = MarkItDownAdapter()

        with pytest.raises(ValueError):
            with adapter._conversion_context("test"):
                raise ValueError("test error")

        assert adapter._metrics["conversions_total"] == 1
        assert adapter._metrics["conversions_successful"] == 0
        assert adapter._metrics["conversions_failed"] == 1

    def test_should_retry_with_retryable_error(self):
        adapter = MarkItDownAdapter()

        connection_error = Exception("Connection error occurred")
        assert adapter._should_retry(connection_error, 0, 3) is True

        timeout_error = Exception("Request timeout")
        assert adapter._should_retry(timeout_error, 1, 3) is True

    def test_should_retry_max_attempts_reached(self):
        adapter = MarkItDownAdapter()

        error = Exception("Connection error")
        assert adapter._should_retry(error, 3, 3) is False

    def test_is_retryable_error_by_type(self):
        adapter = MarkItDownAdapter()

        class ConnectionError(Exception):
            pass

        error = ConnectionError("test")
        assert adapter._is_retryable_error(error) is True

    def test_is_retryable_error_by_message(self):
        adapter = MarkItDownAdapter()

        error = Exception("network timeout occurred")
        assert adapter._is_retryable_error(error) is True

        error = Exception("invalid format")
        assert adapter._is_retryable_error(error) is False

    @pytest.mark.asyncio
    async def test_wait_before_retry(self):
        adapter = MarkItDownAdapter()

        start_time = time.time()
        await adapter._wait_before_retry(0, Exception("test"))
        elapsed = time.time() - start_time

        assert elapsed >= 1.0
        assert elapsed < 3.0

    @pytest.mark.asyncio
    async def test_convert_file_timeout(self):
        adapter = MarkItDownAdapter(timeout_seconds=1)

        async def slow_convert(*args):
            await asyncio.sleep(2)
            return "result"

        with patch.object(adapter, "_convert_file_sync", side_effect=slow_convert):
            with pytest.raises(ConversionTimeoutError):
                await adapter.convert_file("/fake/path")

    @pytest.mark.asyncio
    async def test_convert_content_success(self):
        adapter = MarkItDownAdapter()

        with patch.object(adapter, "_convert_stream_sync") as mock_convert:
            mock_convert.return_value = "# Test Content"

            result = await adapter.convert_content(b"test content", "test.txt")
            assert result == "# Test Content"
            mock_convert.assert_called_once_with(b"test content", "test.txt")

    @pytest.mark.asyncio
    async def test_convert_stream_success(self):
        adapter = MarkItDownAdapter()

        stream = BytesIO(b"test content")

        with patch.object(adapter, "_convert_stream_sync") as mock_convert:
            mock_convert.return_value = "# Stream Content"

            result = await adapter.convert_stream(stream, "test.txt")
            assert result == "# Stream Content"

    @pytest.mark.asyncio
    async def test_convert_url_with_retry(self):
        adapter = MarkItDownAdapter()

        with patch.object(adapter, "_retry_with_backoff") as mock_retry:
            mock_retry.return_value = "# URL Content"

            result = await adapter.convert_url("https://example.com")
            assert result == "# URL Content"
            mock_retry.assert_called_once()

    def test_get_markitdown_instance_import_error(self):
        adapter = MarkItDownAdapter()

        with patch("markitdown.MarkItDown", side_effect=ImportError):
            with pytest.raises(
                MarkdownConversionError, match="markitdown library not installed"
            ):
                adapter._get_markitdown_instance()

    def test_get_markitdown_instance_success(self):
        adapter = MarkItDownAdapter()

        with patch("markitdown.MarkItDown") as mock_markitdown:
            mock_instance = Mock()
            mock_markitdown.return_value = mock_instance

            result = adapter._get_markitdown_instance()
            assert result == mock_instance
            assert adapter._markitdown_instance == mock_instance

    def test_sync_convert_file_success(self):
        adapter = MarkItDownAdapter()

        with patch.object(adapter, "_get_markitdown_instance") as mock_get_md:
            mock_md = Mock()
            mock_result = Mock()
            mock_result.markdown = "# File Content"
            mock_md.convert.return_value = mock_result
            mock_get_md.return_value = mock_md

            with patch("markitdown.StreamInfo"):
                result = adapter._sync_convert_file("/test/file.txt")
                assert result == "# File Content"

    def test_sync_convert_stream_success(self):
        adapter = MarkItDownAdapter()

        with patch.object(adapter, "_get_markitdown_instance") as mock_get_md:
            mock_md = Mock()
            mock_result = Mock()
            mock_result.markdown = "# Stream Content"
            mock_md.convert_stream.return_value = mock_result
            mock_get_md.return_value = mock_md

            result = adapter._sync_convert_stream(b"test content", "test.txt")
            assert result == "# Stream Content"

    def test_sync_convert_url_success(self):
        adapter = MarkItDownAdapter()

        with patch.object(adapter, "_get_markitdown_instance") as mock_get_md:
            mock_md = Mock()
            mock_result = Mock()
            mock_result.markdown = "# URL Content"
            mock_md.convert.return_value = mock_result
            mock_get_md.return_value = mock_md

            result = adapter._sync_convert_url("https://example.com")
            assert result == "# URL Content"

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        adapter = MarkItDownAdapter()

        with patch.object(adapter, "_get_markitdown_instance"):
            result = await adapter.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        adapter = MarkItDownAdapter()

        with patch.object(
            adapter, "_get_markitdown_instance", side_effect=Exception("test error")
        ):
            with pytest.raises(MarkdownConversionError):
                await adapter.health_check()

    def test_get_supported_formats(self):
        adapter = MarkItDownAdapter()

        with patch.object(adapter, "_get_markitdown_instance"):
            formats = adapter.get_supported_formats()
            assert isinstance(formats, list)
            assert ".txt" in formats
            assert ".md" in formats
            assert ".html" in formats

    def test_get_supported_formats_fallback(self):
        adapter = MarkItDownAdapter()

        with patch.object(adapter, "_get_markitdown_instance", side_effect=Exception):
            formats = adapter.get_supported_formats()
            expected = [".txt", ".md", ".html", ".csv", ".json"]
            assert formats == expected

    def test_get_configuration_info(self):
        adapter = MarkItDownAdapter()

        with patch.object(
            adapter, "get_supported_formats", return_value=[".txt", ".pdf"]
        ):
            info = adapter.get_configuration_info()

            assert "enable_builtins" in info
            assert "enable_plugins" in info
            assert "timeout_seconds" in info
            assert "supported_formats" in info
            assert info["supported_formats"] == [".txt", ".pdf"]

    def test_get_metrics(self):
        adapter = MarkItDownAdapter()

        metrics = adapter.get_metrics()
        assert "conversions_total" in metrics
        assert "conversions_successful" in metrics
        assert "conversions_failed" in metrics
        assert metrics["conversions_total"] == 0

    def test_reset_metrics(self):
        adapter = MarkItDownAdapter()

        adapter._metrics["conversions_total"] = 5
        adapter.reset_metrics()

        assert adapter._metrics["conversions_total"] == 0
        assert adapter._metrics["conversions_successful"] == 0

    @pytest.mark.asyncio
    async def test_close_cleanup(self):
        adapter = MarkItDownAdapter()
        mock_session = Mock()
        adapter._requests_session = mock_session
        adapter._markitdown_instance = Mock()

        await adapter.close()

        mock_session.close.assert_called_once()
        assert adapter._requests_session is None
        assert adapter._markitdown_instance is None
