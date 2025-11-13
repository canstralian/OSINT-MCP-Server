"""Test package initialization."""
import pytest


def test_imports():
    """Test that main package imports work."""
    from osint_mcp import __version__, config, ServerConfig
    
    assert __version__ == "0.1.0"
    assert config is not None
    assert ServerConfig is not None


def test_utils_imports():
    """Test utility imports."""
    from osint_mcp.utils import (
        OSINTError,
        RateLimitError,
        InvalidInputError,
        rate_limiter,
    )
    
    assert OSINTError is not None
    assert RateLimitError is not None
    assert InvalidInputError is not None
    assert rate_limiter is not None


def test_tools_imports():
    """Test tool imports."""
    from osint_mcp.tools import (
        dns_lookup,
        get_ip_info,
        check_robots_txt,
    )
    
    assert dns_lookup is not None
    assert get_ip_info is not None
    assert check_robots_txt is not None
