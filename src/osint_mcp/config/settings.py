"""Configuration management for OSINT MCP Server."""
import os

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


class EthicalGuardrails(BaseModel):
    """Ethical guidelines and rate limiting configuration."""

    # Rate limiting (requests per minute)
    rate_limit_per_minute: int = Field(default=10, ge=1, le=60)

    # Respect robots.txt
    respect_robots_txt: bool = Field(default=True)

    # User agent for web requests
    user_agent: str = Field(
        default="OSINT-MCP-Server/0.1.0 (Educational/Research Purpose)"
    )

    # Maximum concurrent requests
    max_concurrent_requests: int = Field(default=5, ge=1, le=20)

    # Request timeout in seconds
    request_timeout: int = Field(default=30, ge=5, le=120)

    # Enable logging of requests
    log_requests: bool = Field(default=True)

    # Blocked domains (never query these)
    blocked_domains: list[str] = Field(default_factory=list)

    # Require explicit consent for sensitive operations
    require_consent: bool = Field(default=True)


class ServerConfig(BaseModel):
    """Main server configuration."""

    # Server settings
    server_name: str = Field(default="OSINT MCP Server")
    version: str = Field(default="0.1.0")

    # Ethical guardrails
    ethical_guardrails: EthicalGuardrails = Field(default_factory=EthicalGuardrails)

    # API Keys (optional, loaded from environment)
    api_keys: dict[str, str | None] = Field(default_factory=dict)

    # Cache settings
    enable_cache: bool = Field(default=True)
    cache_ttl_seconds: int = Field(default=3600, ge=60)

    @classmethod
    def from_env(cls) -> "ServerConfig":
        """Load configuration from environment variables."""
        config = cls()

        # Load rate limiting from env
        if rate_limit := os.getenv("OSINT_RATE_LIMIT"):
            config.ethical_guardrails.rate_limit_per_minute = int(rate_limit)

        # Load user agent from env
        if user_agent := os.getenv("OSINT_USER_AGENT"):
            config.ethical_guardrails.user_agent = user_agent

        # Load API keys
        config.api_keys = {
            "ipinfo": os.getenv("IPINFO_API_KEY"),
            "shodan": os.getenv("SHODAN_API_KEY"),
        }

        return config


# Global configuration instance
config = ServerConfig.from_env()
