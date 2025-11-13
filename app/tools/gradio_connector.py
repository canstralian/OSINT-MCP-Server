#!/usr/bin/env python3
# app/tools/gradio_connector.py
# -*- coding: utf-8 -*-
"""
Gradio app connector for ML model integration.
"""

import logging
import os
from typing import Any
from urllib.parse import urljoin, urlparse

import requests

from app.cache import get_cache

logger = logging.getLogger(__name__)


class GradioConnector:
    """
    Connector for Gradio ML applications.

    Discovers Gradio app specs and provides proxy invocation
    to Gradio endpoints with automatic argument translation.
    """

    def __init__(self):
        """Initialize Gradio connector."""
        self.cache = get_cache()
        self.user_agent = os.getenv("OSINT_USER_AGENT", "osint-mcp/1.0")
        self.timeout = int(os.getenv("OSINT_CONNECTOR_TIMEOUT", "30"))

        # Parse allowlist
        allowlist_str = os.getenv("OSINT_CONNECTOR_ALLOWLIST", "")
        self.allowlist = set(
            domain.strip() for domain in allowlist_str.split(",") if domain.strip()
        )

        logger.info(f"GradioConnector initialized with allowlist: {self.allowlist}")

    def _is_allowed(self, url: str) -> bool:
        """
        Check if URL is in allowlist.

        Args:
            url: URL to check

        Returns:
            True if allowed, False otherwise
        """
        if not self.allowlist:
            logger.warning("Connector allowlist not set. Proxying disabled.")
            return False

        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Check domain and parent domains
        parts = domain.split(".")
        for i in range(len(parts)):
            check_domain = ".".join(parts[i:])
            if check_domain in self.allowlist:
                return True

        return False

    def discover_spec(self, base_url: str) -> dict[str, Any] | None:
        """
        Discover Gradio app spec.

        Attempts to fetch from:
        - /info
        - /config
        - /api
        - /openapi.json

        Args:
            base_url: Base URL of Gradio app

        Returns:
            Parsed spec dict or None
        """
        if not self._is_allowed(base_url):
            return None

        # Check cache
        cache_key = f"gradio:spec:{base_url}"
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"Using cached Gradio spec for {base_url}")
            return cached

        spec_paths = ["/info", "/config", "/api", "/openapi.json"]
        headers = {"User-Agent": self.user_agent}

        for path in spec_paths:
            url = urljoin(base_url, path)
            try:
                response = requests.get(
                    url,
                    headers=headers,
                    timeout=self.timeout,
                )

                if response.status_code == 200:
                    try:
                        spec = response.json()
                        logger.info(f"Discovered Gradio spec from {url}")
                        self.cache.set(cache_key, spec, ttl=3600)
                        return spec
                    except ValueError:
                        continue
            except Exception as e:
                logger.debug(f"Failed to fetch Gradio spec from {url}: {e}")
                continue

        logger.warning(f"No Gradio spec found for {base_url}")
        return None

    def synthesize_tools(self, base_url: str, spec: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Synthesize tool definitions from Gradio spec.

        Args:
            base_url: Base URL of Gradio app
            spec: Gradio spec dict

        Returns:
            List of tool definition dicts
        """
        tools = []

        # Gradio /info endpoint format
        if "named_endpoints" in spec:
            endpoints = spec["named_endpoints"]

            for endpoint_name, endpoint_info in endpoints.items():
                # Build input schema from parameters
                parameters = endpoint_info.get("parameters", [])
                properties = {}
                required = []

                for i, param in enumerate(parameters):
                    param_name = param.get("label", f"param_{i}")
                    param_type = param.get("type", "string")

                    # Map Gradio types to JSON Schema types
                    schema_type = "string"
                    if param_type in ["number", "slider"]:
                        schema_type = "number"
                    elif param_type in ["checkbox"]:
                        schema_type = "boolean"

                    properties[param_name] = {
                        "type": schema_type,
                        "description": param.get("description", ""),
                    }

                    if param.get("required", True):
                        required.append(param_name)

                tool = {
                    "name": f"gradio_{endpoint_name}",
                    "description": endpoint_info.get(
                        "description", f"Gradio endpoint: {endpoint_name}"
                    ),
                    "inputSchema": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                    "metadata": {
                        "base_url": base_url,
                        "endpoint": endpoint_name,
                        "type": "gradio",
                    },
                }

                tools.append(tool)

        # OpenAPI format
        elif "paths" in spec:
            # Use similar logic to OpenAPI connector
            paths = spec.get("paths", {})
            for path, path_item in paths.items():
                if "/predict" in path or "/run" in path:
                    for method in ["post"]:
                        if method in path_item:
                            operation = path_item[method]
                            operation_id = operation.get("operationId", path.replace("/", "_"))

                            tool = {
                                "name": f"gradio_{operation_id}",
                                "description": operation.get("description", ""),
                                "inputSchema": operation.get("requestBody", {})
                                .get("content", {})
                                .get("application/json", {})
                                .get("schema", {}),
                                "metadata": {
                                    "base_url": base_url,
                                    "path": path,
                                    "method": method.upper(),
                                    "type": "gradio",
                                },
                            }

                            tools.append(tool)

        logger.info(f"Synthesized {len(tools)} Gradio tools from {base_url}")
        return tools

    def proxy_invoke(self, tool_metadata: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
        """
        Proxy invocation to Gradio endpoint.

        Args:
            tool_metadata: Tool metadata with base_url, endpoint info
            params: Input parameters

        Returns:
            Response data

        Raises:
            ValueError: If URL not in allowlist
        """
        base_url = tool_metadata["base_url"]

        if not self._is_allowed(base_url):
            raise ValueError(f"URL {base_url} not in allowlist")

        # Determine endpoint path
        if "endpoint" in tool_metadata:
            # Named endpoint format
            endpoint = tool_metadata["endpoint"]
            url = urljoin(base_url, f"/run/{endpoint}")

            # Convert params to Gradio data format
            data = {"data": list(params.values())}
        else:
            # OpenAPI format
            path = tool_metadata.get("path", "/api/predict")
            url = urljoin(base_url, path)
            data = params

        headers = {
            "User-Agent": self.user_agent,
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                url,
                json=data,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()

            result = response.json()

            return {
                "status": "success",
                "data": result.get("data", result),
                "meta": {
                    "url": url,
                    "status_code": response.status_code,
                },
            }

        except requests.RequestException as e:
            logger.error(f"Gradio proxy request failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "meta": {
                    "url": url,
                },
            }
