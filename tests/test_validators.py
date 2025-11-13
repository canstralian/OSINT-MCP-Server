"""Tests for utility modules."""
import pytest
from osint_mcp.utils import (
    validate_domain,
    validate_ip_address,
    validate_url,
    validate_email,
    sanitize_input,
    InvalidInputError,
    EthicalViolationError,
)


def test_validate_domain():
    """Test domain validation."""
    # Valid domains
    assert validate_domain("example.com") == "example.com"
    assert validate_domain("sub.example.com") == "sub.example.com"
    assert validate_domain("EXAMPLE.COM") == "example.com"  # Should lowercase
    
    # Invalid domains
    with pytest.raises(InvalidInputError):
        validate_domain("not_a_domain")
    
    with pytest.raises(InvalidInputError):
        validate_domain("192.168.1.1")  # IP address, not domain
    
    with pytest.raises(InvalidInputError):
        validate_domain("")


def test_validate_ip_address():
    """Test IP address validation."""
    # Valid IPv4
    assert validate_ip_address("192.168.1.1") == "192.168.1.1"
    assert validate_ip_address("8.8.8.8") == "8.8.8.8"
    
    # Valid IPv6
    assert validate_ip_address("2001:4860:4860::8888") == "2001:4860:4860::8888"
    
    # Invalid IPs
    with pytest.raises(InvalidInputError):
        validate_ip_address("256.1.1.1")
    
    with pytest.raises(InvalidInputError):
        validate_ip_address("not.an.ip")
    
    with pytest.raises(InvalidInputError):
        validate_ip_address("")


def test_validate_url():
    """Test URL validation."""
    # Valid URLs
    assert validate_url("https://example.com") == "https://example.com"
    assert validate_url("http://example.com/path") == "http://example.com/path"
    
    # Invalid URLs
    with pytest.raises(InvalidInputError):
        validate_url("not a url")
    
    with pytest.raises(InvalidInputError):
        validate_url("")


def test_validate_email():
    """Test email validation."""
    # Valid emails
    assert validate_email("user@example.com") == "user@example.com"
    assert validate_email("User@Example.COM") == "user@example.com"  # Should lowercase
    
    # Invalid emails
    with pytest.raises(InvalidInputError):
        validate_email("not_an_email")
    
    with pytest.raises(InvalidInputError):
        validate_email("user@")
    
    with pytest.raises(InvalidInputError):
        validate_email("")


def test_sanitize_input():
    """Test input sanitization."""
    # Valid input
    assert sanitize_input("  test input  ") == "test input"
    assert sanitize_input("normal text") == "normal text"
    
    # Remove control characters
    result = sanitize_input("test\x00\x01input")
    assert "\x00" not in result
    assert "\x01" not in result
    
    # Length validation
    with pytest.raises(InvalidInputError):
        sanitize_input("x" * 1001)  # Too long
    
    with pytest.raises(InvalidInputError):
        sanitize_input("")  # Empty
    
    with pytest.raises(InvalidInputError):
        sanitize_input("   ")  # Only whitespace


def test_sanitize_input_custom_length():
    """Test input sanitization with custom max length."""
    assert sanitize_input("short", max_length=10) == "short"
    
    with pytest.raises(InvalidInputError):
        sanitize_input("too long text", max_length=5)
