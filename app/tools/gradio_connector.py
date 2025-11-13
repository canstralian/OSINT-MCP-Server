#!/usr/bin/env python3
# app/tools/gradio_connector.py
# -*- coding: utf-8 -*-
"""
Gradio connector for OSINT-MCP-Server.

Discovers and proxies Gradio applications via their OpenAPI specs.
Only registers connectors for base URLs in the allowlist.
"""

import logging
from typing import Any

from app.cache import get_cache
from app.tools.base import OsintTool, ToolDefinition
from app.tools.connector import ConnectorManager

logger = logging.getLogger(__name__)


class GradioConnector(OsintTool):
    """
    Gradio application connector.

    Discovers Gradio apps via OpenAPI specs and proxies invocations
    to their endpoints. Only operates on allowlisted base URLs.
    """

    def __init__(self, base_url: str):
        """
        Initialize Gradio connector for a specific base URL.

        Args:
            base_url: Base URL of the Gradio application.
        """
        self.base_url = base_url
        self.manager = ConnectorManager()
        self.cache = get_cache()
        self.spec = None
        self.tools = []

        # Verify base_url is in allowlist
        if not self.manager.is_allowed(base_url):
            logger.warning(f"Gradio connector initialized for non-allowed URL: {base_url}")
            return

        # Fetch and cache OpenAPI spec
        self._discover_spec()

    def _discover_spec(self) -> None:
        """
        Discover and cache Gradio app's OpenAPI spec.

        Fetches the spec and synthesizes tool definitions.
        """
        cache_key = f"gradio_tools:{self.base_url}"

        # Check cache first
        cached_tools = self.cache.get(cache_key)
        if cached_tools:
            logger.debug(f"Gradio tools cache hit: {self.base_url}")
            self.tools = cached_tools
            return

        # Fetch spec
        self.spec = self.manager.fetch_openapi(self.base_url, timeout=8)
        if not self.spec:
            logger.warning(f"Failed to discover Gradio spec for {self.base_url}")
            return

        # Synthesize tools from spec
        self.tools = self.manager.synthesize_tools(self.base_url, self.spec)

        # Cache discovered tools (TTL 3600s = 1 hour)
        self.cache.set(cache_key, self.tools, ttl=3600)
        logger.info(f"Discovered {len(self.tools)} tools from Gradio app: {self.base_url}")

    def definition(self) -> ToolDefinition:
        """
        Return tool definition for this Gradio connector.

        Returns:
            ToolDefinition describing the Gradio app.
        """
        # If we have multiple tools from the spec, return a general definition
        return ToolDefinition(
            name=f"gradio_{self.base_url.replace('://', '_').replace('/', '_')}",
            description=f"Gradio application connector for {self.base_url}",
            parameters={
                "endpoint": {
                    "type": "string",
                    "description": "Gradio endpoint to invoke",
                    "required": True,
                },
                "inputs": {
                    "type": "object",
                    "description": "Input parameters for the endpoint",
                    "required": False,
                },
            },
            streamable=False,
            requires_auth=False,
            category="gradio_app",
        )

    def invoke(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Invoke a Gradio endpoint.

        Args:
            params: Dictionary with 'endpoint' and 'inputs'.

        Returns:
            Normalized result from the Gradio endpoint.

        Raises:
            ValueError: If parameters are invalid or URL not allowed.
        """
        if not self.manager.is_allowed(self.base_url):
            return self._normalize_output(
                text=f"Base URL not in allowlist: {self.base_url}",
                data={"error": "URL not allowed"},
                meta={"status": "error"},
            )

        endpoint = params.get("endpoint")
        if not endpoint:
            raise ValueError("Parameter 'endpoint' is required")

        inputs = params.get("inputs", {})

        # Find matching tool definition
        tool_def = None
        for tool in self.tools:
            if tool.get("meta", {}).get("path") == endpoint:
                tool_def = tool
                break

        if not tool_def:
            # Still try to invoke, even without matching tool def
            logger.warning(f"No tool definition found for endpoint: {endpoint}")
            method = "POST"  # Default for Gradio
            path = endpoint
        else:
            method = tool_def.get("meta", {}).get("method", "POST")
            path = tool_def.get("meta", {}).get("path", endpoint)

        # Proxy the invocation
        try:
            response_data = self.manager.proxy_invoke(
                base_url=self.base_url,
                path=path,
                method=method,
                params=inputs,
                timeout=60,  # Gradio calls may take longer
            )

            # Normalize response
            return self._normalize_output(
                text=f"Gradio endpoint {endpoint} invoked successfully",
                data=response_data,
                meta={"endpoint": endpoint, "base_url": self.base_url, "source": "gradio"},
            )

        except Exception as e:
            logger.error(f"Gradio invocation failed: {type(e).__name__}")
            return self._normalize_output(
                text=f"Gradio invocation failed: {type(e).__name__}",
                data={"error": str(e)},
                meta={"status": "error", "endpoint": endpoint, "base_url": self.base_url},
            )

    def list_endpoints(self) -> list[dict[str, Any]]:
        """
        List all available endpoints from the Gradio app.

        Returns:
            List of tool definitions for each endpoint.
        """
        return self.tools
