"""IP geolocation and information tools."""
import logging
from typing import Any

import httpx

from ..config import config
from ..utils import (
    NetworkError,
    handle_error,
    rate_limiter,
    validate_ip_address,
)

logger = logging.getLogger(__name__)


async def get_ip_info(ip_address: str) -> dict[str, Any]:
    """
    Get geolocation and network information for an IP address.
    Uses free ip-api.com service (no API key required for non-commercial use).
    
    Args:
        ip_address: IP address to lookup
        
    Returns:
        Dictionary containing IP information
    """
    try:
        # Validate input
        ip_address = validate_ip_address(ip_address)

        # Apply rate limiting
        await rate_limiter.acquire(f"ipinfo:{ip_address}")

        logger.info(f"Getting IP information for: {ip_address}")

        # Use ip-api.com (free, no key required, but rate limited)
        url = f"http://ip-api.com/json/{ip_address}"

        async with httpx.AsyncClient(
            timeout=config.ethical_guardrails.request_timeout,
            headers={"User-Agent": config.ethical_guardrails.user_agent}
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        if data.get("status") == "fail":
            logger.warning(f"IP lookup failed for {ip_address}: {data.get('message')}")
            return {
                "success": False,
                "error": data.get("message", "Unknown error"),
                "ip_address": ip_address,
            }

        result = {
            "success": True,
            "ip_address": ip_address,
            "country": data.get("country"),
            "country_code": data.get("countryCode"),
            "region": data.get("regionName"),
            "region_code": data.get("region"),
            "city": data.get("city"),
            "zip_code": data.get("zip"),
            "latitude": data.get("lat"),
            "longitude": data.get("lon"),
            "timezone": data.get("timezone"),
            "isp": data.get("isp"),
            "organization": data.get("org"),
            "as_number": data.get("as"),
        }

        logger.info(f"IP info retrieved for {ip_address}: {data.get('country')}, {data.get('city')}")
        return result

    except httpx.HTTPStatusError as e:
        raise NetworkError(f"HTTP error getting IP info: {e.response.status_code}")
    except httpx.TimeoutException:
        raise NetworkError(f"Timeout getting IP info for {ip_address}")
    except Exception as e:
        return handle_error(e, f"IP info lookup for {ip_address}")


async def check_ip_reputation(ip_address: str) -> dict[str, Any]:
    """
    Check IP reputation using AbuseIPDB free tier.
    Note: Requires ABUSEIPDB_API_KEY environment variable for full functionality.
    
    Args:
        ip_address: IP address to check
        
    Returns:
        Dictionary containing reputation information
    """
    try:
        # Validate input
        ip_address = validate_ip_address(ip_address)

        # Apply rate limiting
        await rate_limiter.acquire(f"ipreput:{ip_address}")

        logger.info(f"Checking IP reputation for: {ip_address}")

        api_key = config.api_keys.get("abuseipdb")

        if not api_key:
            logger.warning("AbuseIPDB API key not configured, skipping reputation check")
            return {
                "success": False,
                "error": "API key not configured",
                "message": "Set ABUSEIPDB_API_KEY environment variable to enable reputation checks",
                "ip_address": ip_address,
            }

        url = "https://api.abuseipdb.com/api/v2/check"
        headers = {
            "Key": api_key,
            "Accept": "application/json",
            "User-Agent": config.ethical_guardrails.user_agent,
        }
        params = {
            "ipAddress": ip_address,
            "maxAgeInDays": "90",
        }

        async with httpx.AsyncClient(
            timeout=config.ethical_guardrails.request_timeout
        ) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

        ip_data = data.get("data", {})

        result = {
            "success": True,
            "ip_address": ip_address,
            "abuse_confidence_score": ip_data.get("abuseConfidenceScore"),
            "total_reports": ip_data.get("totalReports"),
            "is_public": ip_data.get("isPublic"),
            "is_whitelisted": ip_data.get("isWhitelisted"),
            "country_code": ip_data.get("countryCode"),
            "usage_type": ip_data.get("usageType"),
            "isp": ip_data.get("isp"),
            "domain": ip_data.get("domain"),
        }

        logger.info(
            f"IP reputation checked for {ip_address}: "
            f"score={result['abuse_confidence_score']}"
        )
        return result

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            raise NetworkError("Rate limit exceeded for AbuseIPDB API")
        raise NetworkError(f"HTTP error checking IP reputation: {e.response.status_code}")
    except httpx.TimeoutException:
        raise NetworkError(f"Timeout checking IP reputation for {ip_address}")
    except Exception as e:
        return handle_error(e, f"IP reputation check for {ip_address}")
