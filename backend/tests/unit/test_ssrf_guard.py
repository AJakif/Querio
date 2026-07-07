import ipaddress
import re

import pytest

from app.services.ssrf_guard import (
    _check_ip,
    _validate_and_resolve,
    SSRFError,
    ALLOWED_SCHEMES,
    ALLOWED_CONTENT_TYPES,
)


class TestCheckIp:
    def test_public_ip_passes(self):
        _check_ip(ipaddress.ip_address("8.8.8.8"))
        _check_ip(ipaddress.ip_address("1.1.1.1"))
        _check_ip(ipaddress.ip_address("93.184.216.34"))

    def test_loopback_v4_blocked(self):
        with pytest.raises(SSRFError, match="loopback"):
            _check_ip(ipaddress.ip_address("127.0.0.1"))
        with pytest.raises(SSRFError, match="loopback"):
            _check_ip(ipaddress.ip_address("127.255.255.255"))

    def test_loopback_v6_blocked(self):
        with pytest.raises(SSRFError, match="loopback"):
            _check_ip(ipaddress.ip_address("::1"))

    def test_private_10_blocked(self):
        with pytest.raises(SSRFError, match="private"):
            _check_ip(ipaddress.ip_address("10.0.0.1"))
        with pytest.raises(SSRFError, match="private"):
            _check_ip(ipaddress.ip_address("10.255.255.255"))

    def test_private_172_16_blocked(self):
        with pytest.raises(SSRFError, match="private"):
            _check_ip(ipaddress.ip_address("172.16.0.1"))
        with pytest.raises(SSRFError, match="private"):
            _check_ip(ipaddress.ip_address("172.31.255.255"))

    def test_private_192_168_blocked(self):
        with pytest.raises(SSRFError, match="private"):
            _check_ip(ipaddress.ip_address("192.168.0.1"))
        with pytest.raises(SSRFError, match="private"):
            _check_ip(ipaddress.ip_address("192.168.255.255"))

    def test_link_local_blocked(self):
        with pytest.raises(SSRFError, match="link-local"):
            _check_ip(ipaddress.ip_address("169.254.1.1"))
        with pytest.raises(SSRFError, match="link-local"):
            _check_ip(ipaddress.ip_address("169.254.254.254"))

    def test_cloud_metadata_explicitly_blocked(self):
        with pytest.raises(SSRFError, match="link-local|cloud metadata"):
            _check_ip(ipaddress.ip_address("169.254.169.254"))


class TestValidateAndResolve:
    def test_rejects_invalid_scheme(self):
        with pytest.raises(SSRFError, match="Only HTTP and HTTPS"):
            _validate_and_resolve("ftp://example.com/data.csv")
        with pytest.raises(SSRFError, match="Only HTTP and HTTPS"):
            _validate_and_resolve("file:///etc/passwd")

    def test_rejects_missing_hostname(self):
        with pytest.raises(SSRFError, match="no hostname"):
            _validate_and_resolve("http:///path")

    def test_rejects_loopback_ip_literal(self):
        with pytest.raises(SSRFError, match="loopback"):
            _validate_and_resolve("http://127.0.0.1/data.csv")

    def test_rejects_private_ip_literal(self):
        with pytest.raises(SSRFError, match="private"):
            _validate_and_resolve("http://192.168.1.1/data.csv")
        with pytest.raises(SSRFError, match="private"):
            _validate_and_resolve("http://10.0.0.1/data.csv")

    def test_rejects_link_local_ip_literal(self):
        with pytest.raises(SSRFError, match="link-local"):
            _validate_and_resolve("http://169.254.169.254/data.csv")

    def test_public_ip_literal_passes_validation(self):
        host, port, path, ip = _validate_and_resolve("http://8.8.8.8/data.csv")
        assert host == "8.8.8.8"
        assert port == 80
        assert path == "/data.csv"
        assert ip == "8.8.8.8"

    def test_https_public_url_sets_correct_default_port(self):
        host, port, path, ip = _validate_and_resolve("https://example.com/data.csv")
        assert port == 443

    def test_url_with_query_string_preserves_query(self):
        host, port, path, ip = _validate_and_resolve("http://example.com/data.csv?param=1")
        assert "param=1" in path

    def test_explicit_port_preserved(self):
        host, port, path, ip = _validate_and_resolve("http://example.com:8080/data.csv")
        assert port == 8080


class TestAllowedConstants:
    def test_allowed_schemes(self):
        assert ALLOWED_SCHEMES == {"http", "https"}

    def test_allowed_content_types(self):
        assert "text/csv" in ALLOWED_CONTENT_TYPES
        assert "application/json" in ALLOWED_CONTENT_TYPES
        assert "text/plain" in ALLOWED_CONTENT_TYPES
