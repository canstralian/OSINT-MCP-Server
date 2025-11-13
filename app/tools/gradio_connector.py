#!/usr/bin/env python3
# app/tools/gradio_connector.py
# -*- coding: utf-8 -*-
"""
Gradio app connector for MCP integration.

This connector discovers Gradio app endpoints and synthesizes MCP tool
definitions for each Gradio function. It provides proxy invocation to
Gradio run endpoints.

Environment Variables:
    OSINT_CONNECTOR_ALLOWLIST: Comma-separated list of allowed base URLs
    OSINT_USER_AGENT: User agent for requests

Security:
    - Only URLs in OSINT_CONNECTOR_ALLOWLIST are allowed to prevent open proxy
    - Timeouts enforced on all external requests
    - Input validation on all parameters

Cache TTLs:
    - Spec cache: 3600 seconds (1 hour)
"""

import logging
import os
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from app.cache import get_cache
from app.security.auth import ClientIdentity
from app.tools.base import OSINTTool, ToolDefinition

logger = logging.getLogger(__name__)

# Cache TTL
SPEC_CACHE_TTL = 3600  # 1 hour


class GradioConnector(OSINTTool):
    """
    Gradio app connector for discovering and proxying Gradio endpoints.

    Discovers Gradio app specifications and synthesizes MCP tool definitions
    for each function. Implements proxy invocation to Gradio endpoints.

    Security: Only proxies to URLs in OSINT_CONNECTOR_ALLOWLIST to avoid
    open proxy behavior.

    Example:
        # Set allowlist in environment
        os.environ["OSINT_CONNECTOR_ALLOWLIST"] = "https://example.gradio.app"

        connector = GradioConnector("https://example.gradio.app")
        tools = await connector.discover_tools()
    """

    name: str = "gradio"
    description: str = (
        "Proxy connector for Gradio applications. "
        "Discovers Gradio app functions and provides MCP integration."
    )
    cachable: bool = True
    cache_ttl_seconds: int = SPEC_CACHE_TTL

    def __init__(self, base_url: str | None = None):
        """
        Initialize Gradio connector.

        Args:
            base_url: Base URL of Gradio app

        Raises:
            ValueError: If base_url not in allowlist
        """
        self.base_url = base_url
        self.user_agent = os.getenv("OSINT_USER_AGENT", "osint-mcp/1.0")
        self.timeout = 30
        self._cache = get_cache()
        self._allowlist = self._load_allowlist()

        if base_url and not self._is_allowed(base_url):
            raise ValueError(
                f"Base URL {base_url} not in OSINT_CONNECTOR_ALLOWLIST. "
                "Add it to the allowlist to enable proxying."
            )

    def _load_allowlist(self) -> list[str]:
        """
        Load URL allowlist from environment.

        Returns:
            List of allowed base URLs
        """
        allowlist_str = os.getenv("OSINT_CONNECTOR_ALLOWLIST", "")
        if not allowlist_str:
            logger.warning(
                "OSINT_CONNECTOR_ALLOWLIST not set. " "Gradio connector will not proxy any URLs."
            )
            return []

        allowlist = [url.strip() for url in allowlist_str.split(",") if url.strip()]
        logger.info(f"Loaded Gradio allowlist: {allowlist}")
        return allowlist

    def _is_allowed(self, url: str) -> bool:
        """
        Check if URL is in allowlist.

        Args:
            url: URL to check

        Returns:
            True if allowed, False otherwise
        """
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        return base in self._allowlist

    def definition(self) -> ToolDefinition:
        """
        Return tool definition.

        Returns:
            ToolDefinition instance
        """
        return ToolDefinition(
            name=self.name,
            description=self.description,
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["discover", "invoke"],
                        "description": "Action: discover tools or invoke function",
                    },
                    "base_url": {"type": "string", "description": "Gradio app base URL"},
                    "function_name": {"type": "string", "description": "Function name to invoke"},
                    "arguments": {"type": "object", "description": "Function arguments"},
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
        Execute Gradio connector action.

        Args:
            args: Action arguments
            client: Client identity

        Returns:
            Action results

        Raises:
            ValueError: For invalid input
            PermissionError: For unauthorized URLs
        """
        action = args.get("action")
        if not action:
            raise ValueError("Missing required parameter: action")

        if action == "discover":
            base_url = args.get("base_url")
            if not base_url:
                raise ValueError("Missing required parameter: base_url")

            if not self._is_allowed(base_url):
                raise PermissionError(
                    f"URL {base_url} not in allowlist. "
                    "Add to OSINT_CONNECTOR_ALLOWLIST to enable."
                )

            return await self._discover_spec(base_url)

        elif action == "invoke":
            return await self._invoke_function(args)

        else:
            raise ValueError(f"Unknown action: {action}")

    async def _discover_spec(self, base_url: str) -> dict[str, Any]:
        """
        Discover Gradio app specification.

        Tries multiple endpoint patterns:
        - /api/predict
        - /info
        - /config
        - /openapi.json

        Args:
            base_url: Gradio app base URL

        Returns:
            Discovered spec and synthesized tools
        """
        # Check cache
        cache_key = f"gradio:spec:{base_url}"
        cached = self._cache.get(cache_key)
        if cached:
            cached["cached"] = True
            return self._normalize_output(cached)

        endpoints_to_try = [
            "/info",
            "/config",
            "/api",
            "/openapi.json",
        ]

        spec = {}

        async with httpx.AsyncClient(timeout=self.timeout) as http_client:
            for endpoint in endpoints_to_try:
                url = urljoin(base_url, endpoint)
                try:
                    response = await http_client.get(
                        url,
                        headers={"User-Agent": self.user_agent},
                    )
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            spec[endpoint] = data
                            logger.info(f"Discovered Gradio endpoint: {endpoint}")
                        except Exception as e:
                            logger.warning(f"Failed to parse JSON from {endpoint}: {e}")
                except Exception as e:
                    logger.debug(f"Endpoint {endpoint} not found: {e}")

        if not spec:
            raise ValueError(
                f"Could not discover Gradio spec for {base_url}. " "No endpoints responded."
            )

        # Synthesize tool definitions
        tools = self._synthesize_tools(base_url, spec)

        result = {
            "base_url": base_url,
            "spec": spec,
            "tools": tools,
            "cached": False,
        }

        # Cache result
        self._cache.set(cache_key, result, SPEC_CACHE_TTL)

        return self._normalize_output(result)

    def _synthesize_tools(self, base_url: str, spec: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Synthesize MCP tool definitions from Gradio spec.

        Args:
            base_url: Gradio app URL
            spec: Discovered specification

        Returns:
            List of synthesized tool definitions
        """
        tools = []

        # Try to extract functions from /info or /config
        info = spec.get("/info", {})
        config = spec.get("/config", {})

        # Look for named functions or endpoints
        functions = []

        if isinstance(info, dict):
            functions.extend(info.get("named_endpoints", []))

        if isinstance(config, dict):
            functions.extend(config.get("components", []))

        # Create tool definition for each function
        for idx, func in enumerate(functions):
            if isinstance(func, dict):
                name = func.get("name", f"fn_{idx}")
                description = func.get("description", f"Gradio function {name}")
            else:
                name = f"fn_{idx}"
                description = f"Gradio function {idx}"

            tool_def = {
                "name": f"gradio_{name}",
                "description": description,
                "base_url": base_url,
                "function_name": name,
            }
            tools.append(tool_def)

        return tools

    async def _invoke_function(self, args: dict[str, Any]) -> dict[str, Any]:
        """
        Invoke Gradio function.

        Args:
            args: Invocation arguments

        Returns:
            Function result
        """
        base_url = args.get("base_url")
        function_name = args.get("function_name")
        arguments = args.get("arguments", {})

        if not base_url or not function_name:
            raise ValueError("Missing required parameters: base_url, function_name")

        if not self._is_allowed(base_url):
            raise PermissionError(f"URL {base_url} not in allowlist")

        # Try different Gradio API patterns
        endpoints = [
            f"/run/{function_name}",
            f"/api/{function_name}",
            "/api/predict",
        ]

        async with httpx.AsyncClient(timeout=self.timeout) as http_client:
            for endpoint in endpoints:
                url = urljoin(base_url, endpoint)
                try:
                    response = await http_client.post(
                        url,
                        json={"data": [arguments]},
                        headers={"User-Agent": self.user_agent},
                    )

                    if response.status_code == 200:
                        result = response.json()
                        return self._normalize_output(
                            {
                                "function": function_name,
                                "result": result,
                                "cached": False,
                            }
                        )

                except Exception as e:
                    logger.debug(f"Endpoint {endpoint} failed: {e}")

        raise ValueError(
            f"Failed to invoke {function_name} at {base_url}. "
            "No endpoints responded successfully."
        )

    def _normalize_output(self, result: Any) -> dict[str, Any]:
        """
        Normalize output to standard format.

        Args:
            result: Raw result

        Returns:
            Normalized output with text, data, meta
        """
        if not isinstance(result, dict):
            return super()._normalize_output(result)

        # Generate summary text
        if "tools" in result:
            # Discovery result
            text = f"Discovered {len(result['tools'])} Gradio functions " f"at {result['base_url']}"
        elif "function" in result:
            # Invocation result
            text = f"Invoked Gradio function: {result['function']}"
        else:
            text = "Gradio operation completed"

        return {
            "text": text,
            "data": result,
            "meta": {
                "tool": self.name,
                "cached": result.get("cached", False),
            },
        }
