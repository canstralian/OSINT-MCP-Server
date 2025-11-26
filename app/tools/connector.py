#!/usr/bin/env python3
# app/tools/connector.py
# -*- coding: utf-8 -*-
"""
OpenAPI/Swagger connector manager for proxying external APIs.
"""

import logging
import os
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
import yaml

from app.cache import get_cache

logger = logging.getLogger(__name__)


class ConnectorManager:
    """
    Manager for discovering and proxying external API endpoints.

    Fetches OpenAPI/Swagger specs, synthesizes tool definitions,
    and proxies requests to external APIs with authentication and
    allowlist enforcement.
    """

    def __init__(self):
        """Initialize connector manager."""
        self.cache = get_cache()
        self.user_agent = os.getenv("OSINT_USER_AGENT", "osint-mcp/1.0")
        self.timeout = int(os.getenv("OSINT_CONNECTOR_TIMEOUT", "30"))

        # Parse allowlist from env var (comma-separated domains)
        allowlist_str = os.getenv("OSINT_CONNECTOR_ALLOWLIST", "")
        self.allowlist = set(
            domain.strip() for domain in allowlist_str.split(",") if domain.strip()
        )

        logger.info(f"ConnectorManager initialized with allowlist: {self.allowlist}")

    def _is_allowed(self, url: str) -> bool:
        """
        Check if URL is in allowlist.

        Args:
            url: URL to check

        Returns:
            True if allowed, False otherwise
        """
        if not self.allowlist:
            # No allowlist = disabled by default
            logger.warning("Connector allowlist not set. Proxying disabled.")
            return False

        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Check if domain or any parent domain is in allowlist
        parts = domain.split(".")
        for i in range(len(parts)):
            check_domain = ".".join(parts[i:])
            if check_domain in self.allowlist:
                return True

        logger.warning(f"Domain {domain} not in allowlist")
        return False

    def fetch_spec(self, base_url: str) -> dict[str, Any] | None:
        """
        Fetch OpenAPI/Swagger spec from various endpoints.

        Attempts to fetch from:
        - /openapi.json
        - /openapi.yaml
        - /swagger.json
        - /swagger.yaml
        - /info (Gradio)

        Args:
            base_url: Base URL of the API

        Returns:
            Parsed spec dict or None if not found
        """
        if not self._is_allowed(base_url):
            return None

        # Check cache first
        cache_key = f"spec:{base_url}"
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"Using cached spec for {base_url}")
            return cached

        # List of paths to try
        spec_paths = [
            "/openapi.json",
            "/openapi.yaml",
            "/swagger.json",
            "/swagger.yaml",
            "/api/openapi.json",
            "/docs/openapi.json",
        ]

        headers = {"User-Agent": self.user_agent}

        for path in spec_paths:
            url = urljoin(base_url, path)
            try:
                response = requests.get(
                    url,
                    headers=headers,
                    timeout=self.timeout,
                    allow_redirects=True,
                )

                if response.status_code == 200:
                    # Try to parse as JSON first
                    try:
                        spec = response.json()
                        logger.info(f"Fetched OpenAPI spec from {url}")
                        self.cache.set(cache_key, spec, ttl=3600)
                        return spec
                    except ValueError:
                        # Try as YAML
                        try:
                            spec = yaml.safe_load(response.text)
                            logger.info(f"Fetched OpenAPI spec (YAML) from {url}")
                            self.cache.set(cache_key, spec, ttl=3600)
                            return spec
                        except Exception as e:
                            logger.debug(f"Failed to parse spec from {url}: {e}")
                            continue
            except Exception as e:
                logger.debug(f"Failed to fetch spec from {url}: {e}")
                continue

        logger.warning(f"No OpenAPI spec found for {base_url}")
        return None

    def synthesize_tools(self, base_url: str, spec: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Synthesize tool definitions from OpenAPI spec.

        Args:
            base_url: Base URL of the API
            spec: OpenAPI specification dict

        Returns:
            List of tool definition dicts
        """
        tools = []

        paths = spec.get("paths", {})
        for path, path_item in paths.items():
            for method in ["get", "post", "put", "delete", "patch"]:
                if method not in path_item:
                    continue

                operation = path_item[method]
                operation_id = operation.get("operationId", f"{method}_{path.replace('/', '_')}")
                summary = operation.get("summary", "")
                description = operation.get("description", summary)

                # Build input schema from parameters
                parameters = operation.get("parameters", [])
                request_body = operation.get("requestBody", {})

                properties = {}
                required = []

                # Add parameters to schema
                for param in parameters:
                    param_name = param.get("name")
                    param_schema = param.get("schema", {"type": "string"})
                    properties[param_name] = param_schema

                    if param.get("required", False):
                        required.append(param_name)

                # Add request body if present
                if request_body:
                    content = request_body.get("content", {})
                    json_content = content.get("application/json", {})
                    body_schema = json_content.get("schema", {})

                    if body_schema:
                        properties["body"] = body_schema
                        if request_body.get("required", False):
                            required.append("body")

                input_schema = {
                    "type": "object",
                    "properties": properties,
                }
                if required:
                    input_schema["required"] = required

                tool = {
                    "name": operation_id,
                    "description": description or f"{method.upper()} {path}",
                    "inputSchema": input_schema,
                    "metadata": {
                        "base_url": base_url,
                        "path": path,
                        "method": method.upper(),
                    },
                }

                tools.append(tool)

        logger.info(f"Synthesized {len(tools)} tools from {base_url}")
        return tools

    def proxy_invoke(
        self,
        tool_metadata: dict[str, Any],
        params: dict[str, Any],
        auth_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Proxy request to external API endpoint.

        Args:
            tool_metadata: Tool metadata containing base_url, path, method
            params: Request parameters
            auth_headers: Optional authentication headers

        Returns:
            Response data

        Raises:
            ValueError: If URL not in allowlist
            requests.RequestException: On HTTP errors
        """
        base_url = tool_metadata["base_url"]
        path = tool_metadata["path"]
        method = tool_metadata["method"]

        if not self._is_allowed(base_url):
            raise ValueError(f"URL {base_url} not in allowlist")

        # Build URL
        url = urljoin(base_url, path)

        # Prepare headers
        headers = {
            "User-Agent": self.user_agent,
            "Content-Type": "application/json",
        }
        if auth_headers:
            headers.update(auth_headers)

        # Extract body and query params
        body = params.get("body")
        query_params = {k: v for k, v in params.items() if k != "body"}  # Remaining params are query params

        # Make request
        try:
            response = requests.request(
                method=method,
                url=url,
                params=query_params,
                json=body if body else None,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()

            # Try to parse JSON response
            try:
                data = response.json()
            except ValueError:
                data = {"text": response.text}

            return {
                "status": "success",
                "data": data,
                "meta": {
                    "url": url,
                    "status_code": response.status_code,
                },
            }

        except requests.RequestException as e:
            logger.error(f"Proxy request failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "meta": {
                    "url": url,
                },
            }
