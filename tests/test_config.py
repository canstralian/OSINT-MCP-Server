"""Tests for configuration module."""
import os
import pytest
from osint_mcp.config import ServerConfig, EthicalGuardrails


def test_ethical_guardrails_defaults():
    """Test default ethical guardrails configuration."""
    guardrails = EthicalGuardrails()
    
    assert guardrails.rate_limit_per_minute == 10
    assert guardrails.respect_robots_txt is True
    assert guardrails.max_concurrent_requests == 5
    assert guardrails.request_timeout == 30
    assert guardrails.log_requests is True
    assert guardrails.require_consent is True
    assert isinstance(guardrails.blocked_domains, list)


def test_server_config_defaults():
    """Test default server configuration."""
    config = ServerConfig()
    
    assert config.server_name == "OSINT MCP Server"
    assert config.version == "0.1.0"
    assert isinstance(config.ethical_guardrails, EthicalGuardrails)
    assert config.enable_cache is True
    assert config.cache_ttl_seconds == 3600


def test_server_config_from_env(monkeypatch):
    """Test loading configuration from environment variables."""
    monkeypatch.setenv("OSINT_RATE_LIMIT", "20")
    monkeypatch.setenv("OSINT_USER_AGENT", "Test Agent")
    monkeypatch.setenv("IPINFO_API_KEY", "test_key_123")
    
    config = ServerConfig.from_env()
    
    assert config.ethical_guardrails.rate_limit_per_minute == 20
    assert config.ethical_guardrails.user_agent == "Test Agent"
    assert config.api_keys["ipinfo"] == "test_key_123"


def test_ethical_guardrails_validation():
    """Test ethical guardrails validation."""
    # Valid configuration
    guardrails = EthicalGuardrails(rate_limit_per_minute=30)
    assert guardrails.rate_limit_per_minute == 30
    
    # Test boundaries
    with pytest.raises(ValueError):
        EthicalGuardrails(rate_limit_per_minute=0)  # Too low
    
    with pytest.raises(ValueError):
        EthicalGuardrails(rate_limit_per_minute=100)  # Too high
