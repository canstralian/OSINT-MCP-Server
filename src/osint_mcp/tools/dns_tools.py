"""DNS and WHOIS lookup tools."""
import asyncio
import logging
from typing import Any

import dns.resolver
import dns.reversename

from ..config import config
from ..utils import (
    DataNotFoundError,
    NetworkError,
    handle_error,
    rate_limiter,
    validate_domain,
    validate_ip_address,
)

logger = logging.getLogger(__name__)


async def dns_lookup(domain: str, record_type: str = "A") -> dict[str, Any]:
    """
    Perform DNS lookup for a domain.
    
    Args:
        domain: Domain name to lookup
        record_type: DNS record type (A, AAAA, MX, NS, TXT, etc.)
        
    Returns:
        Dictionary containing DNS records
    """
    try:
        # Validate input
        domain = validate_domain(domain)
        record_type = record_type.upper().strip()

        # Apply rate limiting
        await rate_limiter.acquire(f"dns:{domain}")

        logger.info(f"Performing DNS lookup: {domain} ({record_type})")

        # Perform DNS query
        resolver = dns.resolver.Resolver()
        resolver.timeout = config.ethical_guardrails.request_timeout
        resolver.lifetime = config.ethical_guardrails.request_timeout

        # Run DNS query in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        answers = await loop.run_in_executor(
            None,
            lambda: resolver.resolve(domain, record_type)
        )

        records = [str(rdata) for rdata in answers]

        result = {
            "success": True,
            "domain": domain,
            "record_type": record_type,
            "records": records,
            "ttl": answers.rrset.ttl if hasattr(answers, 'rrset') else None,
        }

        logger.info(f"DNS lookup successful: {domain} - found {len(records)} records")
        return result

    except dns.resolver.NXDOMAIN:
        raise DataNotFoundError(f"Domain not found: {domain}")
    except dns.resolver.NoAnswer:
        raise DataNotFoundError(f"No {record_type} records found for {domain}")
    except dns.resolver.Timeout:
        raise NetworkError(f"DNS query timeout for {domain}")
    except Exception as e:
        return handle_error(e, f"DNS lookup for {domain}")


async def reverse_dns_lookup(ip_address: str) -> dict[str, Any]:
    """
    Perform reverse DNS lookup for an IP address.
    
    Args:
        ip_address: IP address to lookup
        
    Returns:
        Dictionary containing reverse DNS information
    """
    try:
        # Validate input
        ip_address = validate_ip_address(ip_address)

        # Apply rate limiting
        await rate_limiter.acquire(f"dns:reverse:{ip_address}")

        logger.info(f"Performing reverse DNS lookup: {ip_address}")

        # Perform reverse DNS query
        resolver = dns.resolver.Resolver()
        resolver.timeout = config.ethical_guardrails.request_timeout

        # Convert IP to reverse DNS name
        rev_name = dns.reversename.from_address(ip_address)

        # Run DNS query in thread pool
        loop = asyncio.get_event_loop()
        answers = await loop.run_in_executor(
            None,
            lambda: resolver.resolve(rev_name, "PTR")
        )

        hostnames = [str(rdata) for rdata in answers]

        result = {
            "success": True,
            "ip_address": ip_address,
            "hostnames": hostnames,
        }

        logger.info(f"Reverse DNS lookup successful: {ip_address} -> {hostnames}")
        return result

    except dns.resolver.NXDOMAIN:
        raise DataNotFoundError(f"No reverse DNS record found for {ip_address}")
    except dns.resolver.Timeout:
        raise NetworkError(f"Reverse DNS query timeout for {ip_address}")
    except Exception as e:
        return handle_error(e, f"Reverse DNS lookup for {ip_address}")


async def get_nameservers(domain: str) -> dict[str, Any]:
    """
    Get nameservers for a domain.
    
    Args:
        domain: Domain name to lookup
        
    Returns:
        Dictionary containing nameserver information
    """
    try:
        # Validate input
        domain = validate_domain(domain)

        # Apply rate limiting
        await rate_limiter.acquire(f"dns:ns:{domain}")

        logger.info(f"Getting nameservers for: {domain}")

        # Get NS records
        resolver = dns.resolver.Resolver()
        resolver.timeout = config.ethical_guardrails.request_timeout

        loop = asyncio.get_event_loop()
        answers = await loop.run_in_executor(
            None,
            lambda: resolver.resolve(domain, "NS")
        )

        nameservers = [str(rdata) for rdata in answers]

        # Try to get IP addresses for nameservers
        ns_details = []
        for ns in nameservers:
            try:
                ns_answers = await loop.run_in_executor(
                    None,
                    lambda: resolver.resolve(ns, "A")
                )
                ips = [str(rdata) for rdata in ns_answers]
                ns_details.append({"hostname": ns, "ips": ips})
            except Exception:
                ns_details.append({"hostname": ns, "ips": []})

        result = {
            "success": True,
            "domain": domain,
            "nameservers": ns_details,
        }

        logger.info(f"Found {len(nameservers)} nameservers for {domain}")
        return result

    except dns.resolver.NXDOMAIN:
        raise DataNotFoundError(f"Domain not found: {domain}")
    except dns.resolver.NoAnswer:
        raise DataNotFoundError(f"No nameserver records found for {domain}")
    except Exception as e:
        return handle_error(e, f"Nameserver lookup for {domain}")


async def get_mx_records(domain: str) -> dict[str, Any]:
    """
    Get MX (mail exchange) records for a domain.
    
    Args:
        domain: Domain name to lookup
        
    Returns:
        Dictionary containing MX records
    """
    try:
        # Validate input
        domain = validate_domain(domain)

        # Apply rate limiting
        await rate_limiter.acquire(f"dns:mx:{domain}")

        logger.info(f"Getting MX records for: {domain}")

        # Get MX records
        resolver = dns.resolver.Resolver()
        resolver.timeout = config.ethical_guardrails.request_timeout

        loop = asyncio.get_event_loop()
        answers = await loop.run_in_executor(
            None,
            lambda: resolver.resolve(domain, "MX")
        )

        mx_records = [
            {
                "priority": rdata.preference,
                "hostname": str(rdata.exchange),
            }
            for rdata in answers
        ]

        # Sort by priority
        mx_records.sort(key=lambda x: x["priority"])

        result = {
            "success": True,
            "domain": domain,
            "mx_records": mx_records,
        }

        logger.info(f"Found {len(mx_records)} MX records for {domain}")
        return result

    except dns.resolver.NXDOMAIN:
        raise DataNotFoundError(f"Domain not found: {domain}")
    except dns.resolver.NoAnswer:
        raise DataNotFoundError(f"No MX records found for {domain}")
    except Exception as e:
        return handle_error(e, f"MX record lookup for {domain}")
