#!/usr/bin/env python3
# app/tools/shodan_connector.py
# -*- coding: utf-8 -*-
"""
Shodan OSINT connector.

This module provides integration with the Shodan API for host intelligence,
search, and network scanning information. All data is gathered from Shodan's
publicly available database.

Environment Variables:
    SHODAN_API_KEY: Shodan API key (required)
    OSINT_USER_AGENT: User agent for requests (optional)

Cache TTLs:
    - Search results: 900 seconds (15 minutes)
    - Host details: 3600 seconds (1 hour)
"""

import logging
import os
from typing import Any

import requests

from app.cache import get_cache
from app.security.auth import ClientIdentity
from app.tools.base import OSINTTool, ToolDefinition

logger = logging.getLogger(__name__)

# Cache TTL defaults
SEARCH_CACHE_TTL = 900  # 15 minutes
HOST_CACHE_TTL = 3600  # 1 hour


class ShodanConnector(OSINTTool):
    """
    Shodan API connector for OSINT operations.

    Provides search and host lookup capabilities using the Shodan API.
    Requires SHODAN_API_KEY environment variable.

    Example:
        connector = ShodanConnector()
        result = await connector.execute(
            {"action": "search", "query": "apache"},
            client
        )
    """

    name: str = "shodan"
    description: str = (
        "Search Shodan database for hosts, services, and vulnerabilities. "
        "Provides host intelligence and network scanning data."
    )
    cachable: bool = True
    cache_ttl_seconds: int = HOST_CACHE_TTL

    def __init__(self):
        """Initialize Shodan connector."""
        self.api_key = os.getenv("SHODAN_API_KEY")
        if not self.api_key:
            logger.warning("SHODAN_API_KEY not set. Shodan connector will not function.")

        self.base_url = "https://api.shodan.io"
        self.user_agent = os.getenv("OSINT_USER_AGENT", "osint-mcp/1.0")
        self.timeout = 30
        self._cache = get_cache()

    def definition(self) -> ToolDefinition:
        """
        Return tool definition with input schema.

        Returns:
            ToolDefinition with complete schema
        """
        return ToolDefinition(
            name=self.name,
            description=self.description,
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["search", "host"],
                        "description": "Action to perform: search or host lookup",
                    },
                    "query": {"type": "string", "description": "Search query (for search action)"},
                    "ip": {"type": "string", "description": "IP address (for host action)"},
                },
                "required": ["action"],
            },
            cacheable=self.cachable,
            cache_ttl=self.cache_ttl_seconds,
        )

    async def execute(
        self,
        args: dict[str, Any],
        client: ClientIdentity,
    ) -> dict[str, Any]:
        """
        Execute Shodan query.

        Args:
            args: Query arguments with action and parameters
            client: Client identity

        Returns:
            Query results

        Raises:
            ValueError: For invalid input
            PermissionError: For auth issues
        """
        if not self.api_key:
            raise PermissionError(
                "Shodan API key not configured. " "Set SHODAN_API_KEY environment variable."
            )

        action = args.get("action")
        if not action:
            raise ValueError("Missing required parameter: action")

        if action == "search":
            return await self._search(args)
        elif action == "host":
            return await self._host(args)
        else:
            raise ValueError(f"Unknown action: {action}")

    async def _search(self, args: dict[str, Any]) -> dict[str, Any]:
        """
        Execute Shodan search query.

        Args:
            args: Query arguments

        Returns:
            Search results
        """
        query = args.get("query")
        if not query:
            raise ValueError("Missing required parameter: query")

        # Check cache
        cache_key = f"shodan:search:{query}"
        cached = self._cache.get(cache_key)
        if cached:
            cached["cached"] = True
            return self._normalize_output(cached)

        # Make API request
        try:
            response = requests.get(
                f"{self.base_url}/shodan/host/search",
                params={"key": self.api_key, "query": query},
                headers={"User-Agent": self.user_agent},
                timeout=self.timeout,
            )
            response.raise_for_status()

            data = response.json()
            result = {
                "query": query,
                "total": data.get("total", 0),
                "matches": data.get("matches", []),
                "cached": False,
            }

            # Cache result
            self._cache.set(cache_key, result, SEARCH_CACHE_TTL)

            return self._normalize_output(result)

        except requests.RequestException as e:
            logger.error(f"Shodan search failed: {e}")
            raise ValueError(f"Shodan search failed: {str(e)}")

    async def _host(self, args: dict[str, Any]) -> dict[str, Any]:
        """
        Get host information from Shodan.

        Args:
            args: Query arguments with IP address

        Returns:
            Host information
        """
        ip = args.get("ip")
        if not ip:
            raise ValueError("Missing required parameter: ip")

        # Check cache
        cache_key = f"shodan:host:{ip}"
        cached = self._cache.get(cache_key)
        if cached:
            cached["cached"] = True
            return self._normalize_output(cached)

        # Make API request
        try:
            response = requests.get(
                f"{self.base_url}/shodan/host/{ip}",
                params={"key": self.api_key},
                headers={"User-Agent": self.user_agent},
                timeout=self.timeout,
            )
            response.raise_for_status()

            data = response.json()
            result = {
                "ip": ip,
                "hostnames": data.get("hostnames", []),
                "ports": data.get("ports", []),
                "vulns": data.get("vulns", []),
                "os": data.get("os"),
                "org": data.get("org"),
                "data": data.get("data", []),
                "cached": False,
            }

            # Cache result
            self._cache.set(cache_key, result, HOST_CACHE_TTL)

            return self._normalize_output(result)

        except requests.RequestException as e:
            logger.error(f"Shodan host lookup failed: {e}")
            raise ValueError(f"Shodan host lookup failed: {str(e)}")

    def _normalize_output(self, result: Any) -> dict[str, Any]:
        """
        Normalize output to standard format.

        Args:
            result: Raw result data

        Returns:
            Normalized output with text, data, meta fields
        """
        if not isinstance(result, dict):
            return super()._normalize_output(result)

        # Generate summary text
        if "query" in result:
            # Search result
            text = f"Shodan search for '{result['query']}' " f"found {result['total']} results"
        elif "ip" in result:
            # Host result
            text = (
                f"Shodan host info for {result['ip']}: "
                f"{len(result.get('ports', []))} ports, "
                f"{len(result.get('vulns', []))} vulnerabilities"
            )
        else:
            text = "Shodan query completed"

        return {
            "text": text,
            "data": result,
            "meta": {
                "tool": self.name,
                "cached": result.get("cached", False),
            },
        }
