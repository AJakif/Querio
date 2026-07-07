import http.client
import ipaddress
import socket
import ssl
from urllib.parse import urlparse

from app.core.logging import get_logger

logger = get_logger("services.ssrf_guard")

ALLOWED_SCHEMES = {"http", "https"}
DEFAULT_TIMEOUT = 30
CHUNK_SIZE = 64 * 1024

ALLOWED_CONTENT_TYPES = {
    "text/csv",
    "text/plain",
    "application/json",
    "application/octet-stream",
}

class SSRFError(ValueError):
    pass


def _check_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
    if ip.is_loopback:
        raise SSRFError(
            f"URL resolves to a loopback address ({ip}). "
            "Only public internet URLs are allowed."
        )
    if ip.is_link_local:
        raise SSRFError(
            f"URL resolves to a link-local address ({ip}). "
            "Only public internet URLs are allowed."
        )
    if str(ip) == "169.254.169.254":
        raise SSRFError(
            "URL resolves to a cloud metadata IP address (169.254.169.254). "
            "Only public internet URLs are allowed."
        )
    if ip.is_private:
        raise SSRFError(
            f"URL resolves to a private IP address ({ip}). "
            "Only public internet URLs are allowed."
        )
    if ip.is_multicast:
        raise SSRFError(
            f"URL resolves to a multicast address ({ip}). "
            "Only public internet URLs are allowed."
        )


def _validate_and_resolve(url: str) -> tuple[str, int, str, str]:
    parsed = urlparse(url)

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise SSRFError(
            f"Only HTTP and HTTPS URLs are supported. Got scheme '{parsed.scheme}'."
        )

    if not parsed.hostname:
        raise SSRFError("URL has no hostname.")

    host: str = parsed.hostname or ""
    if not host:
        raise SSRFError("URL has no hostname.")

    port: int = parsed.port or (443 if parsed.scheme == "https" else 80)
    path: str = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    try:
        ip = ipaddress.ip_address(host)
        _check_ip(ip)
        return host, port, path, str(ip)
    except ValueError:
        pass

    try:
        addrs = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise SSRFError(f"Could not resolve hostname '{host}': {exc}")

    if not addrs:
        raise SSRFError(f"Could not resolve hostname '{host}' to any IP address.")

    resolved_ip: str = ""
    for _family, _type, _proto, _canonname, sockaddr in addrs:
        ip_str = str(sockaddr[0])
        ip = ipaddress.ip_address(ip_str)
        _check_ip(ip)
        resolved_ip = ip_str
        break

    return host, port, path, resolved_ip


def fetch_url(url: str, max_size: int = 50 * 1024 * 1024, timeout: int = DEFAULT_TIMEOUT) -> tuple[bytes, str]:
    parsed = urlparse(url)
    scheme = parsed.scheme
    host = parsed.hostname or ""
    port = parsed.port or (443 if scheme == "https" else 80)
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    _, _, _, resolved_ip = _validate_and_resolve(url)

    logger.info(
        "Fetching URL content",
        extra={
            "url": url,
            "resolved_ip": resolved_ip,
            "host": host,
            "max_size": max_size,
        },
    )

    if scheme == "https":
        ctx = ssl.create_default_context()
        raw_sock = socket.create_connection((resolved_ip, port), timeout=timeout)
        conn = http.client.HTTPSConnection(host, port, timeout=timeout, context=ctx)
        conn.sock = ctx.wrap_socket(raw_sock, server_hostname=host)
    else:
        conn = http.client.HTTPConnection(resolved_ip, port, timeout=timeout)

    host_header = host if port in (80, 443) else f"{host}:{port}"

    try:
        conn.putrequest("GET", path)
        conn.putheader("Host", host_header)
        conn.putheader("User-Agent", "Querio/1.0")
        conn.putheader("Accept", "text/csv,application/json,text/plain,*/*")
        conn.endheaders()

        response = conn.getresponse()

        content_type = response.getheader("Content-Type", "").split(";")[0].strip().lower()

        if content_type and content_type not in ALLOWED_CONTENT_TYPES:
            conn.close()
            raise SSRFError(
                f"Unsupported content type '{content_type}'. "
                "Only CSV and JSON files are supported."
            )

        content = bytearray()
        while True:
            chunk = response.read(CHUNK_SIZE)
            if not chunk:
                break
            content.extend(chunk)
            if len(content) > max_size:
                conn.close()
                raise SSRFError(
                    f"File too large. Maximum size is {max_size // (1024 * 1024)}MB."
                )

        conn.close()

        if len(content) == 0:
            raise SSRFError("Fetched file is empty.")

        logger.info(
            "URL fetch complete",
            extra={
                "url": url,
                "content_type": content_type,
                "size": len(content),
                "status": response.status,
            },
        )

        return bytes(content), content_type

    except http.client.HTTPException as exc:
        conn.close()
        raise SSRFError(f"HTTP error while fetching URL: {exc}")
    except socket.timeout:
        conn.close()
        raise SSRFError("Connection timed out while fetching URL.")
    except OSError as exc:
        conn.close()
        raise SSRFError(f"Connection error while fetching URL: {exc}")
