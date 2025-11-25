#!/usr/bin/env python3
# app/tools/shodan_connector.py
# -*- coding: utf-8 -*-
"""
Shodan connector for OSINT-MCP-Server.

Provides search and host lookup functionality via Shodan API.
"""

import logging
import os
from typing import Any

import requests

from app.cache import get_cache
from app.tools.base import OsintTool, ToolDefinition

logger = logging.getLogger(__name__)


class ShodanConnector(OsintTool):
    """
    Shodan API connector for host and service intelligence.

    Supports 'search' and 'host' actions with caching.
    Requires SHODAN_API_KEY environment variable.
    """

    def __init__(self):
        """Initialize Shodan connector with API key and cache."""
        self.api_key = os.getenv("SHODAN_API_KEY")
        if not self.api_key:
            logger.warning("SHODAN_API_KEY not set. Shodan connector will fail.")
        self.cache = get_cache()
        self.base_url = "https://api.shodan.io"

    def definition(self) -> ToolDefinition:
        """
        Return tool definition for Shodan connector.

        Returns:
            ToolDefinition for this tool.
        """
        return ToolDefinition(
            name="shodan",
            description=(
                "Query Shodan API for host and service information. "
                "Supports 'search' and 'host' actions."
            ),
            parameters={
                "action": {
                    "type": "string",
                    "description": "Action to perform: 'search' or 'host'",
                    "required": True,
                    "enum": ["search", "host"],
                },
                "query": {
                    "type": "string",
                    "description": "Search query (for action=search)",
                    "required": False,
                },
                "ip": {
                    "type": "string",
                    "description": "IP address (for action=host)",
                    "required": False,
                },
            },
            streamable=False,
            requires_auth=True,
            category="threat_intelligence",
        )

    def invoke(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute Shodan query.

        Args:
            params: Dictionary with 'action', 'query', or 'ip'.

        Returns:
            Normalized result dictionary.

        Raises:
            ValueError: If parameters are invalid.
            Exception: For API errors.
        """
        if not self.api_key:
            return self._normalize_output(
                text="Shodan API key not configured",
                data={"error": "SHODAN_API_KEY not set"},
                meta={"status": "error"},
            )

        action = params.get("action")
        if not action:
            raise ValueError("Parameter 'action' is required")

        if action == "search":
            return self._search(params.get("query", ""))
        elif action == "host":
            return self._host_lookup(params.get("ip", ""))
        else:
            raise ValueError(f"Invalid action: {action}")

    def _search(self, query: str) -> dict[str, Any]:
        """
        Perform Shodan search query.

        Args:
            query: Search query string.

        Returns:
            Normalized search results.
        """
        if not query:
            raise ValueError("Parameter 'query' is required for search action")

        # Check cache (TTL 900s = 15 minutes)
        cache_key = f"shodan_search:{query}"
        cached = self.cache.get(cache_key)
        if cached:
            logger.debug(f"Shodan search cache hit: {query}")
            return cached

        # Make API request
        url = f"{self.base_url}/shodan/host/search"
        try:
            response = requests.get(url, params={"key": self.api_key, "query": query}, timeout=20)
            response.raise_for_status()
            data = response.json()

            # Normalize output
            result = self._normalize_output(
                text=f"Found {data.get('total', 0)} results for query: {query}",
                data={"total": data.get("total", 0), "matches": data.get("matches", [])},
                meta={"query": query, "action": "search", "source": "shodan"},
            )

            # Cache results
            self.cache.set(cache_key, result, ttl=900)
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Shodan search failed: {type(e).__name__}")
            return self._normalize_output(
                text=f"Shodan search failed: {type(e).__name__}",
                data={"error": str(e)},
                meta={"status": "error", "action": "search"},
            )

    def _host_lookup(self, ip: str) -> dict[str, Any]:
        """
        Lookup Shodan information for a specific host.

        Args:
            ip: IP address to lookup.

        Returns:
            Normalized host details.
        """
        if not ip:
            raise ValueError("Parameter 'ip' is required for host action")

        # Check cache (TTL 3600s = 1 hour)
        cache_key = f"shodan_host:{ip}"
        cached = self.cache.get(cache_key)
        if cached:
            logger.debug(f"Shodan host cache hit: {ip}")
            return cached

        # Make API request
        url = f"{self.base_url}/shodan/host/{ip}"
        try:
            response = requests.get(url, params={"key": self.api_key}, timeout=20)
            response.raise_for_status()
            data = response.json()

            # Normalize output
            result = self._normalize_output(
                text=f"Host information for {ip}",
                data={
                    "ip": data.get("ip_str", ip),
                    "hostnames": data.get("hostnames", []),
                    "ports": data.get("ports", []),
                    "vulns": data.get("vulns", []),
                    "organization": data.get("org", ""),
                    "country": data.get("country_name", ""),
                },
                meta={"ip": ip, "action": "host", "source": "shodan"},
            )

            # Cache results
            self.cache.set(cache_key, result, ttl=3600)
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Shodan host lookup failed: {type(e).__name__}")
            return self._normalize_output(
                text=f"Shodan host lookup failed: {type(e).__name__}",
                data={"error": str(e)},
                meta={"status": "error", "action": "host"},
            )
