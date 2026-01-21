#!/usr/bin/env python3
# app/tools/shodan_connector.py
# -*- coding: utf-8 -*-
"""
Shodan API connector for OSINT intelligence gathering.
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
    Shodan API connector for device and vulnerability intelligence.

    Provides search and host lookup capabilities using the Shodan API.
    Results are cached to minimize API usage.
    """

    def __init__(self):
        """Initialize Shodan connector."""
        self.api_key = os.getenv("SHODAN_API_KEY")
        if not self.api_key:
            logger.warning("SHODAN_API_KEY not set. Shodan connector will not function.")

        self.base_url = "https://api.shodan.io"
        self.cache = get_cache()
        self.timeout = int(os.getenv("OSINT_CONNECTOR_TIMEOUT", "30"))
        self.user_agent = os.getenv("OSINT_USER_AGENT", "osint-mcp/1.0")

    def definition(self) -> ToolDefinition:
        """
        Return tool definition for Shodan connector.

        Returns:
            ToolDefinition object
        """
        return ToolDefinition(
            name="shodan_search",
            description="Search Shodan for devices, services, and vulnerabilities. "
            'Supports queries like "apache", "port:22", "country:US", etc.',
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query using Shodan query syntax",
                    },
                    "facets": {
                        "type": "string",
                        "description": (
                            'Optional comma-separated list of facets '
                            '(e.g., "country,org")'
                        ),
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number for pagination (default: 1)",
                        "default": 1,
                    },
                },
                "required": ["query"],
            },
            streamable=False,
            metadata={
                "source": "shodan",
                "requires_api_key": True,
            },
        )

    def invoke(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute Shodan search or host lookup.

        Args:
            params: Parameters containing query, facets, page, or ip

        Returns:
            Normalized output with search/host results

        Raises:
            ValueError: If API key not configured or required params missing
        """
        if not self.api_key:
            raise ValueError("SHODAN_API_KEY environment variable not set")

        # Determine operation type
        if "ip" in params:
            return self._host(params["ip"])
        else:
            query = params.get("query")
            if not query:
                raise ValueError("Either 'query' or 'ip' parameter is required")

            facets = params.get("facets")
            page = params.get("page", 1)

            return self._search(query, facets, page)

    def _search(self, query: str, facets: str = None, page: int = 1) -> dict[str, Any]:
        """
        Search Shodan database.

        Args:
            query: Search query
            facets: Optional facets
            page: Page number

        Returns:
            Normalized search results
        """
        # Check cache
        cache_key = f"shodan:search:{query}:{facets}:{page}"
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"Using cached Shodan search results for query: {query}")
            return cached

        # Make API request
        url = f"{self.base_url}/shodan/host/search"
        params = {
            "query": query,
            "page": page,
        }
        if facets:
            params["facets"] = facets

        headers = {
            "User-Agent": self.user_agent,
            "Authorization": f"SHODAN {self.api_key}",
        }

        try:
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            # Normalize output
            total = data.get("total", 0)
            matches = data.get("matches", [])

            # Build text summary
            text = f"Found {total} results for query: {query}\n\n"
            for i, match in enumerate(matches[:5], 1):
                ip = match.get("ip_str", "N/A")
                port = match.get("port", "N/A")
                org = match.get("org", "N/A")
                text += f"{i}. {ip}:{port} ({org})\n"

            if len(matches) > 5:
                text += f"\n... and {len(matches) - 5} more results"

            result = self._normalize_output(
                text=text,
                data={
                    "total": total,
                    "matches": matches,
                    "facets": data.get("facets", {}),
                },
                meta={
                    "query": query,
                    "page": page,
                    "source": "shodan",
                },
            )

            # Cache for 15 minutes (900s)
            self.cache.set(cache_key, result, ttl=900)

            return result

        except requests.RequestException as e:
            logger.error(f"Shodan search failed: {e}")
            return self._normalize_output(
                text="Shodan search failed. Please check your query and try again.", data={}, meta={"error": "Shodan search failed"}
            )

    def _host(self, ip: str) -> dict[str, Any]:
        """
        Get detailed information about a host.

        Args:
            ip: IP address to lookup

        Returns:
            Normalized host information
        """
        # Check cache
        cache_key = f"shodan:host:{ip}"
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"Using cached Shodan host data for IP: {ip}")
            return cached

        # Make API request
        url = f"{self.base_url}/shodan/host/{ip}"
        headers = {
            "User-Agent": self.user_agent,
            "Authorization": f"Bearer {self.api_key}",
        }

        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            # Build text summary
            org = data.get("org", "N/A")
            country = data.get("country_name", "N/A")
            ports = data.get("ports", [])

            text = f"Host: {ip}\n"
            text += f"Organization: {org}\n"
            text += f"Country: {country}\n"
            text += f"Open Ports: {', '.join(map(str, ports[:10]))}\n"

            if len(ports) > 10:
                text += f"... and {len(ports) - 10} more ports"

            result = self._normalize_output(
                text=text,
                data=data,
                meta={
                    "ip": ip,
                    "source": "shodan",
                },
            )

            # Cache for 1 hour (3600s)
            self.cache.set(cache_key, result, ttl=3600)

            return result

        except requests.RequestException as e:
            logger.error(f"Shodan host lookup failed: {e}")
            return self._normalize_output(
                text=f"Shodan host lookup failed: {str(e)}", data={}, meta={"error": str(e)}
            )
