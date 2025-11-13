"""Web scraping and metadata extraction tools with ethical guardrails."""
import logging
from typing import Any
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from ..config import config
from ..utils import (
    EthicalViolationError,
    NetworkError,
    handle_error,
    rate_limiter,
    validate_domain,
    validate_url,
)

logger = logging.getLogger(__name__)


async def check_robots_txt(url: str) -> dict[str, Any]:
    """
    Check robots.txt for a domain and verify if URL can be accessed.
    
    Args:
        url: URL to check
        
    Returns:
        Dictionary with robots.txt information
    """
    try:
        url = validate_url(url)
        parsed = urlparse(url)
        domain = parsed.netloc

        # Apply rate limiting
        await rate_limiter.acquire(f"robots:{domain}")

        robots_url = f"{parsed.scheme}://{domain}/robots.txt"

        logger.info(f"Checking robots.txt for: {domain}")

        async with httpx.AsyncClient(
            timeout=config.ethical_guardrails.request_timeout,
            headers={"User-Agent": config.ethical_guardrails.user_agent},
            follow_redirects=True,
        ) as client:
            try:
                response = await client.get(robots_url)
                robots_content = response.text if response.status_code == 200 else ""
            except Exception:
                robots_content = ""

        # Parse robots.txt
        rp = RobotFileParser()
        rp.parse(robots_content.split('\n')) if robots_content else None

        can_fetch = (
            rp.can_fetch(config.ethical_guardrails.user_agent, url)
            if robots_content
            else True
        )

        result = {
            "success": True,
            "url": url,
            "domain": domain,
            "robots_txt_exists": bool(robots_content),
            "can_fetch": can_fetch,
            "robots_txt_url": robots_url,
        }

        if robots_content:
            # Extract crawl delay if specified
            crawl_delay = rp.crawl_delay(config.ethical_guardrails.user_agent)
            if crawl_delay:
                result["crawl_delay_seconds"] = crawl_delay

        logger.info(f"Robots.txt check for {domain}: can_fetch={can_fetch}")
        return result

    except Exception as e:
        return handle_error(e, f"Robots.txt check for {url}")


async def get_http_headers(url: str) -> dict[str, Any]:
    """
    Get HTTP headers for a URL (HEAD request only, minimal bandwidth).
    
    Args:
        url: URL to check
        
    Returns:
        Dictionary containing HTTP headers
    """
    try:
        url = validate_url(url)
        parsed = urlparse(url)
        domain = parsed.netloc

        # Check robots.txt first if enabled
        if config.ethical_guardrails.respect_robots_txt:
            robots_check = await check_robots_txt(url)
            if not robots_check.get("can_fetch", True):
                raise EthicalViolationError(
                    f"robots.txt disallows access to {url}",
                    details={"url": url}
                )

        # Apply rate limiting
        await rate_limiter.acquire(f"http:{domain}")

        logger.info(f"Getting HTTP headers for: {url}")

        async with httpx.AsyncClient(
            timeout=config.ethical_guardrails.request_timeout,
            headers={"User-Agent": config.ethical_guardrails.user_agent},
            follow_redirects=True,
        ) as client:
            response = await client.head(url)

        result = {
            "success": True,
            "url": url,
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "final_url": str(response.url),
        }

        logger.info(f"HTTP headers retrieved for {url}: status={response.status_code}")
        return result

    except httpx.HTTPStatusError as e:
        return {
            "success": False,
            "error": f"HTTP error: {e.response.status_code}",
            "url": url,
            "status_code": e.response.status_code,
        }
    except httpx.TimeoutException:
        raise NetworkError(f"Timeout getting headers for {url}")
    except Exception as e:
        return handle_error(e, f"HTTP headers for {url}")


async def extract_metadata(url: str) -> dict[str, Any]:
    """
    Extract basic metadata from a webpage (title, description, etc.).
    Only fetches public information, respects robots.txt.
    
    Args:
        url: URL to extract metadata from
        
    Returns:
        Dictionary containing page metadata
    """
    try:
        url = validate_url(url)
        parsed = urlparse(url)
        domain = parsed.netloc

        # Check robots.txt first if enabled
        if config.ethical_guardrails.respect_robots_txt:
            robots_check = await check_robots_txt(url)
            if not robots_check.get("can_fetch", True):
                raise EthicalViolationError(
                    f"robots.txt disallows access to {url}",
                    details={"url": url}
                )

        # Apply rate limiting
        await rate_limiter.acquire(f"http:{domain}")

        logger.info(f"Extracting metadata from: {url}")

        async with httpx.AsyncClient(
            timeout=config.ethical_guardrails.request_timeout,
            headers={"User-Agent": config.ethical_guardrails.user_agent},
            follow_redirects=True,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            html = response.text

        # Basic metadata extraction (without heavy HTML parsing library)
        metadata = {
            "success": True,
            "url": url,
            "final_url": str(response.url),
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type", ""),
            "content_length": len(html),
        }

        # Extract title
        if "<title>" in html.lower():
            start = html.lower().find("<title>") + 7
            end = html.lower().find("</title>", start)
            if end > start:
                metadata["title"] = html[start:end].strip()

        # Extract basic meta tags
        meta_tags = {}
        for meta_type in ["description", "keywords", "author"]:
            search_str = f'name="{meta_type}"'
            if search_str in html.lower():
                idx = html.lower().find(search_str)
                content_start = html.lower().find('content="', idx)
                if content_start > -1:
                    content_start += 9
                    content_end = html.find('"', content_start)
                    if content_end > content_start:
                        meta_tags[meta_type] = html[content_start:content_end].strip()

        if meta_tags:
            metadata["meta_tags"] = meta_tags

        logger.info(f"Metadata extracted from {url}")
        return metadata

    except httpx.HTTPStatusError as e:
        return {
            "success": False,
            "error": f"HTTP error: {e.response.status_code}",
            "url": url,
            "status_code": e.response.status_code,
        }
    except httpx.TimeoutException:
        raise NetworkError(f"Timeout extracting metadata from {url}")
    except Exception as e:
        return handle_error(e, f"Metadata extraction from {url}")


async def check_ssl_certificate(domain: str) -> dict[str, Any]:
    """
    Check SSL/TLS certificate information for a domain.
    
    Args:
        domain: Domain to check
        
    Returns:
        Dictionary containing SSL certificate information
    """
    try:
        domain = validate_domain(domain)

        # Apply rate limiting
        await rate_limiter.acquire(f"ssl:{domain}")

        logger.info(f"Checking SSL certificate for: {domain}")

        url = f"https://{domain}"

        async with httpx.AsyncClient(
            timeout=config.ethical_guardrails.request_timeout,
            headers={"User-Agent": config.ethical_guardrails.user_agent},
        ) as client:
            response = await client.get(url)

            # Get certificate information from the connection
            # Note: httpx doesn't expose cert details easily, so we get basic info
            result = {
                "success": True,
                "domain": domain,
                "https_enabled": True,
                "status_code": response.status_code,
                "http_version": response.http_version,
            }

        logger.info(f"SSL check completed for {domain}")
        return result

    except httpx.ConnectError:
        return {
            "success": True,
            "domain": domain,
            "https_enabled": False,
            "error": "HTTPS not available or connection failed",
        }
    except Exception as e:
        return handle_error(e, f"SSL check for {domain}")
