"""Validation utilities for OSINT operations."""
import re
from urllib.parse import urlparse

import validators

from ..config import config
from .errors import EthicalViolationError, InvalidInputError


def validate_domain(domain: str) -> str:
    """
    Validate and sanitize a domain name.
    
    Args:
        domain: Domain name to validate
        
    Returns:
        Sanitized domain name
        
    Raises:
        InvalidInputError: If domain is invalid
        EthicalViolationError: If domain is blocked
    """
    domain = domain.strip().lower()

    # Remove protocol if present
    if "://" in domain:
        domain = urlparse(f"http://{domain}").netloc or domain.split("://")[1].split("/")[0]

    # Remove path if present
    domain = domain.split("/")[0]

    # Validate format
    if not validators.domain(domain):
        raise InvalidInputError(f"Invalid domain format: {domain}")

    # Check against blocked domains
    if domain in config.ethical_guardrails.blocked_domains:
        raise EthicalViolationError(
            f"Domain '{domain}' is blocked by ethical guardrails",
            details={"domain": domain}
        )

    return domain


def validate_ip_address(ip: str) -> str:
    """
    Validate an IP address.
    
    Args:
        ip: IP address to validate
        
    Returns:
        Sanitized IP address
        
    Raises:
        InvalidInputError: If IP address is invalid
    """
    ip = ip.strip()

    if not validators.ipv4(ip) and not validators.ipv6(ip):
        raise InvalidInputError(f"Invalid IP address: {ip}")

    return ip


def validate_url(url: str) -> str:
    """
    Validate a URL.
    
    Args:
        url: URL to validate
        
    Returns:
        Sanitized URL
        
    Raises:
        InvalidInputError: If URL is invalid
    """
    url = url.strip()

    if not validators.url(url):
        raise InvalidInputError(f"Invalid URL: {url}")

    return url


def validate_email(email: str) -> str:
    """
    Validate an email address (for metadata lookup only).
    
    Args:
        email: Email address to validate
        
    Returns:
        Sanitized email address
        
    Raises:
        InvalidInputError: If email is invalid
    """
    email = email.strip().lower()

    if not validators.email(email):
        raise InvalidInputError(f"Invalid email format: {email}")

    return email


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """
    Sanitize user input to prevent injection attacks.
    
    Args:
        text: Text to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized text
        
    Raises:
        InvalidInputError: If input is invalid
    """
    if not isinstance(text, str):
        raise InvalidInputError("Input must be a string")

    text = text.strip()

    if len(text) > max_length:
        raise InvalidInputError(f"Input exceeds maximum length of {max_length}")

    if not text:
        raise InvalidInputError("Input cannot be empty")

    # Remove control characters except whitespace
    text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)

    return text
