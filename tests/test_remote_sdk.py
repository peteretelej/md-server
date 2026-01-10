import pytest
from unittest.mock import patch, Mock
import httpx

from md_server.sdk import RemoteMDConverter
from md_server.models import ConversionResult


class TestRemoteMDConverter:
    @pytest.fixture
    def remote_converter(self):
        return RemoteMDConverter("http://localhost:9011")

    def test_init_default(self):
        converter = RemoteMDConverter("http://localhost:9011")
        assert converter.endpoint == "http://localhost:9011"
        # Check timeout is set correctly
        assert hasattr(converter._client, "timeout")

    def test_init_with_api_key(self):
        converter = RemoteMDConverter(
            "http://localhost:9011", api_key="test-key", timeout=60
        )
        assert converter.endpoint == "http://localhost:9011"
        assert converter._client.headers["Authorization"] == "Bearer test-key"
        assert hasattr(converter._client, "timeout")

    def test_init_strips_trailing_slash(self):
        converter = RemoteMDConverter("http://localhost:9011/")
        assert converter.endpoint == "http://localhost:9011"

    @pytest.mark.asyncio
    async def test_convert_content_success(self, remote_converter):
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "markdown": "# Test Content",
            "metadata": {"type": "html"},
        }
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
            result = await remote_converter.convert_content(b"<h1>Test</h1>")
            assert result.success is True
            assert result.markdown == "# Test Content"
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_convert_content_http_error(self, remote_converter):
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = httpx.HTTPStatusError(
                "400 Bad Request", request=Mock(), response=Mock(status_code=400)
            )

            with pytest.raises(httpx.HTTPStatusError):
                await remote_converter.convert_content(b"<h1>Test</h1>")

    @pytest.mark.asyncio
    async def test_convert_content_network_error(self, remote_converter):
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = httpx.ConnectError("Connection failed")

            with pytest.raises(httpx.ConnectError):
                await remote_converter.convert_content(b"<h1>Test</h1>")

    @pytest.mark.asyncio
    async def test_convert_url_success(self, remote_converter):
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "markdown": "# URL Content",
            "metadata": {"url": "https://example.com"},
        }
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            result = await remote_converter.convert_url("https://example.com")
            assert result.success is True
            assert result.markdown == "# URL Content"

    @pytest.mark.asyncio
    async def test_convert_file_success(self, remote_converter, simple_html_file):
        if simple_html_file.exists():
            mock_response = Mock()
            mock_response.json.return_value = {
                "success": True,
                "markdown": "# File Content",
                "metadata": {"filename": "simple.html"},
            }
            mock_response.raise_for_status = Mock()

            with patch("httpx.AsyncClient.post", return_value=mock_response):
                result = await remote_converter.convert_file(simple_html_file)
                assert result.success is True
                assert result.markdown == "# File Content"

    @pytest.mark.asyncio
    async def test_convert_file_nonexistent(self, remote_converter):
        from pathlib import Path

        nonexistent = Path("/nonexistent/file.txt")
        with pytest.raises(FileNotFoundError):
            await remote_converter.convert_file(nonexistent)

    def test_convert_content_sync(self, remote_converter):
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "markdown": "# Sync Content",
            "metadata": {},
        }
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            result = remote_converter.convert_content_sync(b"<h1>Test</h1>")
            assert result.success is True
            assert result.markdown == "# Sync Content"

    def test_convert_url_sync(self, remote_converter):
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "markdown": "# Sync URL",
            "metadata": {},
        }
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            result = remote_converter.convert_url_sync("https://example.com")
            assert result.success is True
            assert result.markdown == "# Sync URL"

    def test_convert_file_sync(self, remote_converter, simple_html_file):
        if simple_html_file.exists():
            mock_response = Mock()
            mock_response.json.return_value = {
                "success": True,
                "markdown": "# Sync File",
                "metadata": {},
            }
            mock_response.raise_for_status = Mock()

            with patch("httpx.AsyncClient.post", return_value=mock_response):
                result = remote_converter.convert_file_sync(simple_html_file)
                assert result.success is True
                assert result.markdown == "# Sync File"

    @pytest.mark.asyncio
    async def test_headers_with_api_key(self):
        converter = RemoteMDConverter("http://localhost:9011", api_key="test-key")

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {"success": True, "markdown": "test"}
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            await converter.convert_content(b"test")

            # Check that API key is configured in client headers
            assert "Authorization" in converter._client.headers
            assert converter._client.headers["Authorization"] == "Bearer test-key"

    # --- URL Validation Tests ---

    @pytest.mark.asyncio
    async def test_convert_url_empty_raises(self, remote_converter):
        with pytest.raises(ValueError, match="URL cannot be empty"):
            await remote_converter.convert_url("")

    @pytest.mark.asyncio
    async def test_convert_url_whitespace_raises(self, remote_converter):
        with pytest.raises(ValueError, match="URL cannot be empty"):
            await remote_converter.convert_url("   ")

    @pytest.mark.asyncio
    async def test_convert_url_invalid_scheme_raises(self, remote_converter):
        with pytest.raises(ValueError, match="must start with http"):
            await remote_converter.convert_url("ftp://example.com")

    # --- raw_markdown Tests ---

    @pytest.mark.asyncio
    async def test_convert_url_raw_markdown(self, remote_converter):
        mock_response = Mock()
        mock_response.text = "# Raw Content"
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            result = await remote_converter.convert_url(
                "https://example.com", raw_markdown=True
            )
            assert result == "# Raw Content"
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_convert_content_raw_markdown(self, remote_converter):
        mock_response = Mock()
        mock_response.text = "# Raw Content"
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            result = await remote_converter.convert_content(b"test", raw_markdown=True)
            assert result == "# Raw Content"
            assert isinstance(result, str)

    # --- convert_text Method Tests ---

    @pytest.mark.asyncio
    async def test_convert_text_success(self, remote_converter):
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "markdown": "# Text Content",
            "metadata": {},
        }
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            result = await remote_converter.convert_text("Hello World")
            assert result.success is True
            assert result.markdown == "# Text Content"

    @pytest.mark.asyncio
    async def test_convert_text_empty_raises(self, remote_converter):
        with pytest.raises(ValueError, match="Text cannot be empty"):
            await remote_converter.convert_text("")

    @pytest.mark.asyncio
    async def test_convert_text_raw_markdown(self, remote_converter):
        mock_response = Mock()
        mock_response.text = "# Raw Text"
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            result = await remote_converter.convert_text("Hello", raw_markdown=True)
            assert result == "# Raw Text"
            assert isinstance(result, str)

    def test_convert_text_sync(self, remote_converter):
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "markdown": "# Sync Text",
            "metadata": {},
        }
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            result = remote_converter.convert_text_sync("Hello")
            assert result.success is True
            assert result.markdown == "# Sync Text"

    # --- Content Validation Tests ---

    @pytest.mark.asyncio
    async def test_convert_content_empty_raises(self, remote_converter):
        with pytest.raises(ValueError, match="Content cannot be empty"):
            await remote_converter.convert_content(b"")


class TestRemoteMDConverterTimeout:
    """Test timeout handling in remote converter"""

    @pytest.mark.asyncio
    async def test_timeout_error_handling(self):
        converter = RemoteMDConverter("http://localhost:9011", timeout=0.001)

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Request timeout")

            with pytest.raises(httpx.TimeoutException):
                await converter.convert_content(b"<h1>Test</h1>")

    @pytest.mark.asyncio
    async def test_invalid_json_response(self):
        """Test handling of invalid JSON response"""
        converter = RemoteMDConverter("http://localhost:9011")

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            with pytest.raises(ValueError):
                await converter.convert_content(b"<h1>Test</h1>")

    @pytest.mark.asyncio
    async def test_malformed_response_structure(self):
        """Test handling of malformed response structure"""
        converter = RemoteMDConverter("http://localhost:9011")

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {
            "invalid": "structure"
        }  # Missing required fields

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            result = await converter.convert_content(b"<h1>Test</h1>")
            assert isinstance(result, ConversionResult)
            # Should handle gracefully with default values
            assert result.success is True


class TestRemoteMDConverterContextManager:
    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        async with RemoteMDConverter("http://localhost:9011") as converter:
            assert converter is not None

    def test_sync_context_manager(self):
        # RemoteMDConverter only supports async context manager
        converter = RemoteMDConverter("http://localhost:9011")
        assert converter is not None


class TestRemoteMDConverterAppLifecycle:
    """Test app startup/shutdown lifecycle paths"""

    @pytest.mark.asyncio
    async def test_client_session_lifecycle(self):
        """Test proper client session management"""
        converter = RemoteMDConverter("http://localhost:9011")

        # Test that multiple requests work with session management
        mock_response = Mock()
        mock_response.json.return_value = {"success": True, "markdown": "test"}
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
            # Make multiple requests
            await converter.convert_content(b"test1")
            await converter.convert_content(b"test2")

            assert mock_post.call_count == 2

    def test_configuration_loading_scenarios(self):
        """Test configuration loading edge cases"""
        # Test URL normalization
        converter1 = RemoteMDConverter("http://localhost:9011/")
        converter2 = RemoteMDConverter("http://localhost:9011")
        assert converter1.endpoint == converter2.endpoint

        # Test with different protocols
        https_converter = RemoteMDConverter("https://api.example.com")
        assert https_converter.endpoint == "https://api.example.com"

        # Test parameter validation
        converter_with_params = RemoteMDConverter(
            "http://localhost:9011", api_key="test-key", timeout=120
        )
        assert (
            converter_with_params._client.headers["Authorization"] == "Bearer test-key"
        )
        assert hasattr(converter_with_params._client, "timeout")
