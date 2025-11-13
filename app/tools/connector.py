#!/usr/bin/env python3
# app/tools/connector.py
# -*- coding: utf-8 -*-
"""
Connector Manager for discovering and proxying external OpenAPI/Gradio endpoints.

Discovers API specs, synthesizes tool definitions, and proxies invocations
with security controls (allowlist, timeout, safe logging).
"""

import json
import logging
import os
from typing import Any
from urllib.parse import urljoin

import requests

from app.cache import get_cache

logger = logging.getLogger(__name__)


class ConnectorManager:
    """
    Manages discovery and invocation of external API endpoints.

    Supports OpenAPI and Gradio spec discovery, caching, and
    secure proxying with allowlist enforcement.
    """

    # Common paths to check for API specs
    SPEC_PATHS = [
        "/openapi.json",
        "/openapi.yaml",
        "/swagger.json",
        "/swagger.yaml",
        "/info",
        "/api",
    ]

    def __init__(self):
        """Initialize ConnectorManager with cache and allowlist."""
        self.cache = get_cache()
        self.user_agent = os.getenv("OSINT_USER_AGENT", "osint-mcp/1.0")
        # Parse allowlist from comma-separated env var
        allowlist_str = os.getenv("OSINT_CONNECTOR_ALLOWLIST", "")
        self.allowlist = [url.strip() for url in allowlist_str.split(",") if url.strip()]
        if not self.allowlist:
            logger.info("OSINT_CONNECTOR_ALLOWLIST is empty. " "Proxied connectors are disabled.")

    def is_allowed(self, base_url: str) -> bool:
        """
        Check if base_url is in the allowlist.

        Args:
            base_url: Base URL to check.

        Returns:
            True if allowed, False otherwise.
        """
        if not self.allowlist:
            return False

        # Normalize URL for comparison
        normalized = base_url.rstrip("/")
        return any(normalized.startswith(allowed.rstrip("/")) for allowed in self.allowlist)

    def fetch_openapi(self, base_url: str, timeout: int = 8) -> dict[str, Any] | None:
        """
        Discover and fetch OpenAPI spec from base_url.

        Tries multiple common spec paths and caches successful results.

        Args:
            base_url: Base URL of the API.
            timeout: Request timeout in seconds.

        Returns:
            Parsed OpenAPI spec dict or None if not found.
        """
        if not self.is_allowed(base_url):
            logger.warning(f"Base URL not in allowlist: {base_url}")
            return None

        # Check cache first
        cache_key = f"openapi_spec:{base_url}"
        cached_spec = self.cache.get(cache_key)
        if cached_spec:
            logger.debug(f"OpenAPI spec cache hit: {base_url}")
            return cached_spec

        # Try each spec path
        for path in self.SPEC_PATHS:
            url = urljoin(base_url, path)
            try:
                response = requests.get(
                    url, timeout=timeout, headers={"User-Agent": self.user_agent}
                )
                if response.status_code == 200:
                    spec = response.json()
                    # Cache spec for 1 hour
                    self.cache.set(cache_key, spec, ttl=3600)
                    logger.info(f"Discovered OpenAPI spec at {url}")
                    return spec
            except Exception as e:
                # Log without exposing sensitive data
                logger.debug(f"Failed to fetch spec from {path}: {type(e).__name__}")

        logger.warning(f"No OpenAPI spec found for {base_url}")
        return None

    def synthesize_tools(self, base_url: str, spec: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Synthesize tool definitions from OpenAPI spec.

        Converts each operation in the spec to a tool definition.

        Args:
            base_url: Base URL of the API.
            spec: Parsed OpenAPI spec.

        Returns:
            List of tool definition dicts.
        """
        tools = []
        paths = spec.get("paths", {})

        for path, methods in paths.items():
            for method, operation in methods.items():
                if method.upper() not in ["GET", "POST", "PUT", "DELETE"]:
                    continue

                operation_id = operation.get("operationId", f"{method}_{path.replace('/', '_')}")

                tool_def = {
                    "name": operation_id,
                    "description": operation.get(
                        "summary", operation.get("description", f"{method.upper()} {path}")
                    ),
                    "parameters": self._extract_parameters(operation),
                    "streamable": False,
                    "requires_auth": self._requires_auth(operation),
                    "category": "external_api",
                    "meta": {"base_url": base_url, "path": path, "method": method.upper()},
                }
                tools.append(tool_def)

        return tools

    def _extract_parameters(self, operation: dict[str, Any]) -> dict[str, Any]:
        """
        Extract parameters from OpenAPI operation.

        Args:
            operation: OpenAPI operation object.

        Returns:
            Dictionary describing parameters.
        """
        params = {}
        for param in operation.get("parameters", []):
            param_name = param.get("name")
            if param_name:
                params[param_name] = {
                    "type": param.get("schema", {}).get("type", "string"),
                    "description": param.get("description", ""),
                    "required": param.get("required", False),
                }
        return params

    def _requires_auth(self, operation: dict[str, Any]) -> bool:
        """
        Check if operation requires authentication.

        Args:
            operation: OpenAPI operation object.

        Returns:
            True if auth required, False otherwise.
        """
        security = operation.get("security", [])
        return len(security) > 0

    def proxy_invoke(
        self,
        base_url: str,
        path: str,
        method: str,
        params: dict[str, Any],
        auth: dict[str, Any] | None = None,
        timeout: int = 20,
    ) -> dict[str, Any]:
        """
        Proxy an invocation to an external endpoint.

        Args:
            base_url: Base URL of the API.
            path: API path to invoke.
            method: HTTP method (GET, POST, etc.).
            params: Parameters to send.
            auth: Optional auth configuration (headers or query params).
            timeout: Request timeout in seconds.

        Returns:
            Response data from the endpoint.

        Raises:
            ValueError: If base_url not in allowlist.
            Exception: For request failures (without exposing secrets).
        """
        if not self.is_allowed(base_url):
            raise ValueError(f"Base URL not in allowlist: {base_url}")

        url = urljoin(base_url, path)
        headers = {"User-Agent": self.user_agent}

        # Add auth headers if provided
        if auth and "headers" in auth:
            headers.update(auth["headers"])

        # Prepare query params
        query_params = params.copy()
        if auth and "query" in auth:
            query_params.update(auth["query"])

        try:
            if method.upper() == "GET":
                response = requests.get(url, params=query_params, headers=headers, timeout=timeout)
            elif method.upper() == "POST":
                response = requests.post(url, json=params, headers=headers, timeout=timeout)
            else:
                response = requests.request(
                    method.upper(), url, json=params, headers=headers, timeout=timeout
                )

            response.raise_for_status()

            # Try to parse JSON response
            try:
                return response.json()
            except json.JSONDecodeError:
                return {"text": response.text}

        except requests.exceptions.RequestException as e:
            # Log without exposing sensitive details
            logger.error(
                f"Proxy invocation failed: {type(e).__name__} " f"for {method.upper()} {path}"
            )
            raise Exception(f"Failed to invoke {method.upper()} {path}: " f"{type(e).__name__}")
