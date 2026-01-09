"""URL validation for SSRF protection."""

import ipaddress
import socket
from typing import Set
from urllib.parse import urlparse


# Loopback addresses - localhost (usually safe, user's own services)
LOOPBACK_NETWORKS: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = [
    ipaddress.ip_network("127.0.0.0/8"),  # IPv4 Loopback
    ipaddress.ip_network("::1/128"),  # IPv6 Loopback
]

# Private networks - internal infrastructure (more dangerous)
PRIVATE_NETWORKS: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = [
    ipaddress.ip_network("10.0.0.0/8"),  # IPv4 Private
    ipaddress.ip_network("172.16.0.0/12"),  # IPv4 Private
    ipaddress.ip_network("192.168.0.0/16"),  # IPv4 Private
    ipaddress.ip_network("fc00::/7"),  # IPv6 ULA
    ipaddress.ip_network("fe80::/10"),  # IPv6 Link-local
]

# Cloud metadata and special networks - critical security risk
DANGEROUS_NETWORKS: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = [
    ipaddress.ip_network(
        "169.254.0.0/16"
    ),  # Link-local / Cloud metadata (AWS, GCP, Azure)
    ipaddress.ip_network("0.0.0.0/8"),  # Current network
]

ALLOWED_SCHEMES: Set[str] = {"http", "https"}


class SSRFError(ValueError):
    """Raised when URL targets a blocked resource."""

    def __init__(self, message: str, blocked_reason: str = "unknown"):
        super().__init__(message)
        self.blocked_reason = blocked_reason


def _is_in_networks(
    ip: ipaddress.IPv4Address | ipaddress.IPv6Address,
    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network],
) -> bool:
    """Check if an IP address is in any of the given networks."""
    for network in networks:
        if ip in network:
            return True
    return False


def validate_url(
    url: str,
    allow_localhost: bool = True,
    allow_private_networks: bool = False,
) -> str:
    """
    Validate URL before fetching to prevent SSRF attacks.

    Args:
        url: Target URL to validate
        allow_localhost: Allow localhost/loopback addresses (default: True)
        allow_private_networks: Allow private network ranges like 10.x, 172.16.x, 192.168.x
                               Also enables cloud metadata access (default: False)

    Returns:
        Validated URL string

    Raises:
        SSRFError: URL targets blocked resource
    """
    parsed = urlparse(url)

    # Validate scheme
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise SSRFError(
            f"URL scheme not allowed: {parsed.scheme}", blocked_reason="invalid_scheme"
        )

    # Validate hostname exists
    hostname = parsed.hostname
    if not hostname:
        raise SSRFError("No hostname in URL", blocked_reason="missing_hostname")

    # Resolve DNS and validate IP
    try:
        addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC)
        resolved_ips = {ipaddress.ip_address(info[4][0]) for info in addr_info}
    except socket.gaierror as e:
        raise SSRFError(
            f"DNS resolution failed for: {hostname}", blocked_reason="dns_failure"
        ) from e

    # Check resolved IPs against blocked ranges
    for ip in resolved_ips:
        # Always block dangerous networks (cloud metadata) unless private networks allowed
        if not allow_private_networks and _is_in_networks(ip, DANGEROUS_NETWORKS):
            raise SSRFError(
                "URL targets a blocked IP range",
                blocked_reason="dangerous_ip_range",
            )

        # Block private networks unless explicitly allowed
        if not allow_private_networks and _is_in_networks(ip, PRIVATE_NETWORKS):
            raise SSRFError(
                "URL targets a private IP range",
                blocked_reason="private_ip_range",
            )

        # Block loopback unless allowed (allowed by default)
        if not allow_localhost and _is_in_networks(ip, LOOPBACK_NETWORKS):
            raise SSRFError(
                "URL targets localhost",
                blocked_reason="localhost_blocked",
            )

    return url
