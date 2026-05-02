"""Test URL validation hardening in source_targets.py."""

import pytest
from app.ingestion.web_monitor.source_targets import (
    _parsed_allowed_host,
    WebMonitorTarget,
)


class TestParsedAllowedHost:
    """Test _parsed_allowed_host validation logic."""

    def test_valid_https_url(self):
        """Test valid HTTPS URL."""
        assert _parsed_allowed_host("https://example.com/path") == "example.com"

    def test_valid_http_url(self):
        """Test valid HTTP URL."""
        assert _parsed_allowed_host("http://example.com/path") == "example.com"

    def test_trailing_dot_stripped(self):
        """Test that trailing dot is stripped."""
        assert _parsed_allowed_host("https://example.com./path") == "example.com"

    def test_url_lowercased(self):
        """Test that hostname is lowercased."""
        assert _parsed_allowed_host("https://EXAMPLE.COM/path") == "example.com"

    def test_rejects_file_scheme(self):
        """Test that file:// scheme is rejected."""
        with pytest.raises(ValueError, match="Unsupported URL scheme"):
            _parsed_allowed_host("file:///etc/passwd")

    def test_rejects_ftp_scheme(self):
        """Test that ftp:// scheme is rejected."""
        with pytest.raises(ValueError, match="Unsupported URL scheme"):
            _parsed_allowed_host("ftp://example.com/file")

    def test_rejects_url_with_username(self):
        """Test that URLs with username are rejected."""
        with pytest.raises(ValueError, match="must not include credentials"):
            _parsed_allowed_host("https://user@example.com/path")

    def test_rejects_url_with_password(self):
        """Test that URLs with password are rejected."""
        with pytest.raises(ValueError, match="must not include credentials"):
            _parsed_allowed_host("https://user:pass@example.com/path")

    def test_rejects_url_without_hostname(self):
        """Test that malformed URL without hostname is rejected."""
        with pytest.raises(ValueError, match="must include a hostname"):
            _parsed_allowed_host("https:///path")


class TestWebMonitorTargetIsUrlAllowed:
    """Test WebMonitorTarget.is_url_allowed with hardened validation."""

    def test_allows_valid_exact_domain(self):
        """Test that exact domain matches are allowed."""
        target = WebMonitorTarget(
            name="Test",
            source_type="test",
            base_url="https://example.com",
            allowed_domains=["example.com"],
            start_urls=["https://example.com"],
            extractor_type="test",
        )
        assert target.is_url_allowed("https://example.com/path") is True

    def test_allows_valid_subdomain(self):
        """Test that subdomains are allowed."""
        target = WebMonitorTarget(
            name="Test",
            source_type="test",
            base_url="https://example.com",
            allowed_domains=["example.com"],
            start_urls=["https://example.com"],
            extractor_type="test",
        )
        assert target.is_url_allowed("https://news.example.com/path") is True

    def test_rejects_invalid_sibling_domain(self):
        """Test that sibling domains are rejected."""
        target = WebMonitorTarget(
            name="Test",
            source_type="test",
            base_url="https://example.com",
            allowed_domains=["example.com"],
            start_urls=["https://example.com"],
            extractor_type="test",
        )
        assert target.is_url_allowed("https://evil.net/path") is False

    def test_rejects_url_with_credentials(self):
        """Test that URLs with credentials are rejected."""
        target = WebMonitorTarget(
            name="Test",
            source_type="test",
            base_url="https://example.com",
            allowed_domains=["example.com"],
            start_urls=["https://example.com"],
            extractor_type="test",
        )
        assert target.is_url_allowed("https://user:pass@example.com/path") is False

    def test_rejects_file_scheme(self):
        """Test that file:// URLs are rejected."""
        target = WebMonitorTarget(
            name="Test",
            source_type="test",
            base_url="https://example.com",
            allowed_domains=["example.com"],
            start_urls=["https://example.com"],
            extractor_type="test",
        )
        assert target.is_url_allowed("file:///etc/passwd") is False

    def test_rejects_ftp_scheme(self):
        """Test that ftp:// URLs are rejected."""
        target = WebMonitorTarget(
            name="Test",
            source_type="test",
            base_url="https://example.com",
            allowed_domains=["example.com"],
            start_urls=["https://example.com"],
            extractor_type="test",
        )
        assert target.is_url_allowed("ftp://example.com/file") is False
