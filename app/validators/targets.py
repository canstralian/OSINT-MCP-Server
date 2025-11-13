#!/usr/bin/env python3
# app/validators/targets.py
# -*- coding: utf-8 -*-
"""
Validators and ethical guardrails for OSINT targets.
"""

import ipaddress
import re
from typing import Any, Dict

_DOMAIN_REGEX = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
    r"(?:\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*\.[A-Za-z]{2,}$"
)


def validate_domain(domain: str) -> None:
    """
    Validate domain syntax and enforce public-domain-style patterns.
    Raises ValueError if invalid.
    """
    if not _DOMAIN_REGEX.match(domain):
        raise ValueError("Domain is not syntactically valid.")

    # Disallow obvious internal domains.
    if domain.endswith(".local") or domain.endswith(".lan"):
        raise ValueError("Internal domains are not permitted for OSINT queries.")


def is_private_ip(value: str) -> bool:
    """Return True if the provided IP address is private/reserved."""
    try:
        ip_obj = ipaddress.ip_address(value)
    except ValueError:
        return False
    return ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved


def validate_target_constraints(args: Dict[str, Any]) -> None:
    """
    Apply high-level ethical guardrails to target parameters.

    Blocks internal or clearly non-public targets.
    """
    for key, value in args.items():
        if "ip" in key and isinstance(value, str) and is_private_ip(value):
            raise ValueError(
                "Private or internal IPs are not permitted OSINT targets."
            )
