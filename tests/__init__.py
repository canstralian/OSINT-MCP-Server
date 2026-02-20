"""Test package initialization."""


def test_imports():
    """Test that main package imports work."""
    from osint_mcp import ServerConfig, __version__, config

    assert __version__ == "0.1.0"
    assert config is not None
    assert ServerConfig is not None


def test_utils_imports():
    """Test utility imports."""
    from osint_mcp.utils import (
        InvalidInputError,
        OSINTError,
        RateLimitError,
        rate_limiter,
    )

    assert OSINTError is not None
    assert RateLimitError is not None
    assert InvalidInputError is not None
    assert rate_limiter is not None


def test_tools_imports():
    """Test tool imports."""
    from osint_mcp.tools import (
        check_robots_txt,
        dns_lookup,
        get_ip_info,
    )

    assert dns_lookup is not None
    assert get_ip_info is not None
    assert check_robots_txt is not None
