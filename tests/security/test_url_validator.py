"""Unit tests for SSRF protection."""

import pytest
from unittest.mock import patch
import socket

from src.md_server.security.url_validator import (
    validate_url,
    SSRFError,
    LOOPBACK_NETWORKS,
    PRIVATE_NETWORKS,
    DANGEROUS_NETWORKS,
    ALLOWED_SCHEMES,
)


class TestSSRFProtectionDefaults:
    """Test SSRF protection with default settings (localhost allowed, private blocked)."""

    def test_allows_localhost_by_default(self):
        """Localhost is allowed by default."""
        result = validate_url("http://127.0.0.1/")
        assert result == "http://127.0.0.1/"

    def test_allows_localhost_name_by_default(self):
        """localhost hostname is allowed by default."""
        result = validate_url("http://localhost/")
        assert result == "http://localhost/"

    def test_blocks_aws_metadata(self):
        """Block AWS metadata endpoint (169.254.169.254) by default."""
        with pytest.raises(SSRFError) as exc_info:
            validate_url("http://169.254.169.254/latest/meta-data/")
        assert exc_info.value.blocked_reason == "dangerous_ip_range"

    def test_blocks_private_10_range(self):
        """Block 10.x.x.x private range by default."""
        with pytest.raises(SSRFError) as exc_info:
            validate_url("http://10.0.0.1/")
        assert exc_info.value.blocked_reason == "private_ip_range"

    def test_blocks_private_172_range(self):
        """Block 172.16.x.x private range by default."""
        with pytest.raises(SSRFError) as exc_info:
            validate_url("http://172.16.0.1/")
        assert exc_info.value.blocked_reason == "private_ip_range"

    def test_blocks_private_192_range(self):
        """Block 192.168.x.x private range by default."""
        with pytest.raises(SSRFError) as exc_info:
            validate_url("http://192.168.1.1/")
        assert exc_info.value.blocked_reason == "private_ip_range"

    def test_blocks_file_scheme(self):
        """Block file:// scheme."""
        with pytest.raises(SSRFError) as exc_info:
            validate_url("file:///etc/passwd")
        assert exc_info.value.blocked_reason == "invalid_scheme"

    def test_blocks_ftp_scheme(self):
        """Block ftp:// scheme."""
        with pytest.raises(SSRFError) as exc_info:
            validate_url("ftp://ftp.example.com/")
        assert exc_info.value.blocked_reason == "invalid_scheme"

    def test_blocks_no_scheme(self):
        """Block URLs without scheme."""
        with pytest.raises(SSRFError) as exc_info:
            validate_url("example.com")
        assert exc_info.value.blocked_reason == "invalid_scheme"

    @patch("socket.getaddrinfo")
    def test_allows_public_http(self, mock_getaddrinfo):
        """Allow public HTTP URLs."""
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))
        ]
        result = validate_url("http://example.com/")
        assert result == "http://example.com/"

    @patch("socket.getaddrinfo")
    def test_allows_public_https(self, mock_getaddrinfo):
        """Allow public HTTPS URLs."""
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))
        ]
        result = validate_url("https://example.com/page.html")
        assert result == "https://example.com/page.html"

    def test_blocks_missing_hostname(self):
        """Block URLs without hostname."""
        with pytest.raises(SSRFError) as exc_info:
            validate_url("http:///path")
        assert exc_info.value.blocked_reason == "missing_hostname"

    def test_handles_dns_failure(self):
        """Handle DNS resolution failure gracefully."""
        with pytest.raises(SSRFError) as exc_info:
            validate_url("http://nonexistent.invalid.domain.test/")
        assert exc_info.value.blocked_reason == "dns_failure"

    def test_blocks_zero_network(self):
        """Block 0.0.0.0/8 network."""
        with pytest.raises(SSRFError) as exc_info:
            validate_url("http://0.0.0.1/")
        assert exc_info.value.blocked_reason == "dangerous_ip_range"


class TestSSRFProtectionLocalhostDisabled:
    """Test SSRF protection with localhost explicitly disabled."""

    def test_blocks_localhost_when_disabled(self):
        """Block localhost when allow_localhost=False."""
        with pytest.raises(SSRFError) as exc_info:
            validate_url("http://127.0.0.1/", allow_localhost=False)
        assert exc_info.value.blocked_reason == "localhost_blocked"

    def test_blocks_localhost_name_when_disabled(self):
        """Block localhost hostname when allow_localhost=False."""
        with pytest.raises(SSRFError) as exc_info:
            validate_url("http://localhost/", allow_localhost=False)
        assert exc_info.value.blocked_reason == "localhost_blocked"


class TestSSRFProtectionPrivateNetworksEnabled:
    """Test SSRF protection with private networks enabled."""

    def test_allows_private_192_when_enabled(self):
        """Allow 192.168.x.x when allow_private_networks=True."""
        result = validate_url("http://192.168.1.1/", allow_private_networks=True)
        assert result == "http://192.168.1.1/"

    def test_allows_private_10_when_enabled(self):
        """Allow 10.x.x.x when allow_private_networks=True."""
        result = validate_url("http://10.0.0.1/", allow_private_networks=True)
        assert result == "http://10.0.0.1/"

    def test_allows_private_172_when_enabled(self):
        """Allow 172.16.x.x when allow_private_networks=True."""
        result = validate_url("http://172.16.0.1/", allow_private_networks=True)
        assert result == "http://172.16.0.1/"

    def test_allows_cloud_metadata_when_enabled(self):
        """Allow cloud metadata when allow_private_networks=True."""
        result = validate_url(
            "http://169.254.169.254/latest/meta-data/", allow_private_networks=True
        )
        assert result == "http://169.254.169.254/latest/meta-data/"


class TestSSRFErrorException:
    """Test SSRFError exception class."""

    def test_ssrf_error_message(self):
        """SSRFError includes message."""
        error = SSRFError("Test message", blocked_reason="test_reason")
        assert str(error) == "Test message"

    def test_ssrf_error_blocked_reason(self):
        """SSRFError includes blocked_reason."""
        error = SSRFError("Test message", blocked_reason="test_reason")
        assert error.blocked_reason == "test_reason"

    def test_ssrf_error_default_reason(self):
        """SSRFError defaults blocked_reason to 'unknown'."""
        error = SSRFError("Test message")
        assert error.blocked_reason == "unknown"

    def test_ssrf_error_is_value_error(self):
        """SSRFError inherits from ValueError."""
        error = SSRFError("Test message")
        assert isinstance(error, ValueError)


class TestNetworkConfiguration:
    """Test network configuration constants."""

    def test_loopback_networks_contains_ipv4(self):
        """Loopback networks includes IPv4 loopback."""
        import ipaddress

        assert ipaddress.ip_network("127.0.0.0/8") in LOOPBACK_NETWORKS

    def test_loopback_networks_contains_ipv6(self):
        """Loopback networks includes IPv6 loopback."""
        import ipaddress

        assert ipaddress.ip_network("::1/128") in LOOPBACK_NETWORKS

    def test_private_networks_contains_rfc1918(self):
        """Private networks includes RFC 1918 ranges."""
        import ipaddress

        assert ipaddress.ip_network("10.0.0.0/8") in PRIVATE_NETWORKS
        assert ipaddress.ip_network("172.16.0.0/12") in PRIVATE_NETWORKS
        assert ipaddress.ip_network("192.168.0.0/16") in PRIVATE_NETWORKS

    def test_dangerous_networks_contains_link_local(self):
        """Dangerous networks includes link-local (cloud metadata)."""
        import ipaddress

        assert ipaddress.ip_network("169.254.0.0/16") in DANGEROUS_NETWORKS

    def test_dangerous_networks_contains_zero_network(self):
        """Dangerous networks includes 0.0.0.0/8."""
        import ipaddress

        assert ipaddress.ip_network("0.0.0.0/8") in DANGEROUS_NETWORKS


class TestAllowedSchemes:
    """Test allowed schemes configuration."""

    def test_http_allowed(self):
        """HTTP scheme is allowed."""
        assert "http" in ALLOWED_SCHEMES

    def test_https_allowed(self):
        """HTTPS scheme is allowed."""
        assert "https" in ALLOWED_SCHEMES

    def test_only_two_schemes(self):
        """Only http and https are allowed."""
        assert len(ALLOWED_SCHEMES) == 2
