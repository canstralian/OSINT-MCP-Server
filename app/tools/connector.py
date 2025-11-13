#!/usr/bin/env python3
# app/tools/connector.py
# -*- coding: utf-8 -*-
"""
OpenAPI connector manager for dynamic tool discovery and proxying.

This module provides a ConnectorManager that:
- Discovers OpenAPI specifications from external APIs
- Synthesizes MCP tool definitions from OpenAPI operations
- Proxies invocations to external API endpoints
- Caches specs for performance

Environment Variables:
    OSINT_USER_AGENT: User agent for HTTP requests

Cache TTLs:
    - Spec cache: 3600 seconds (1 hour)
"""

import logging
import os
from typing import Any
from urllib.parse import urljoin

import httpx

from app.cache import get_cache
from app.tools.base import ToolDefinition

logger = logging.getLogger(__name__)

# Cache TTL
SPEC_CACHE_TTL = 3600  # 1 hour


class ConnectorManager:
    """
    Manages OpenAPI-based external tool connectors.

    Discovers OpenAPI specifications from external services and synthesizes
    MCP tool definitions. Provides proxy invocation to external endpoints.

    Example:
        manager = ConnectorManager()
        spec = await manager.fetch_spec("https://api.example.com")
        tools = manager.synthesize_tools(spec)
        result = await manager.proxy_invoke(url, method, params, headers)
    """

    def __init__(self):
        """Initialize connector manager."""
        self.user_agent = os.getenv("OSINT_USER_AGENT", "osint-mcp/1.0")
        self.timeout = 30
        self._cache = get_cache()

    async def fetch_spec(self, base_url: str) -> dict[str, Any] | None:
        """
        Fetch OpenAPI specification from a service.

        Tries multiple common OpenAPI endpoint patterns:
        - /openapi.json
        - /swagger.json
        - /api/openapi.json
        - /api/swagger.json
        - /api-docs
        - /v1/openapi.json

        Args:
            base_url: Base URL of the API service

        Returns:
            OpenAPI specification dict or None if not found
        """
        # Check cache first
        cache_key = f"connector:spec:{base_url}"
        cached = self._cache.get(cache_key)
        if cached:
            logger.info(f"Using cached spec for {base_url}")
            return cached

        endpoints_to_try = [
            "/openapi.json",
            "/swagger.json",
            "/api/openapi.json",
            "/api/swagger.json",
            "/api-docs",
            "/v1/openapi.json",
            "/docs/openapi.json",
        ]

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for endpoint in endpoints_to_try:
                url = urljoin(base_url, endpoint)
                try:
                    logger.debug(f"Trying OpenAPI endpoint: {url}")
                    response = await client.get(
                        url,
                        headers={"User-Agent": self.user_agent},
                        follow_redirects=True,
                    )

                    if response.status_code == 200:
                        try:
                            spec = response.json()
                            logger.info(f"Found OpenAPI spec at {url}")

                            # Validate it looks like OpenAPI
                            if self._validate_openapi_spec(spec):
                                # Cache the spec
                                self._cache.set(cache_key, spec, SPEC_CACHE_TTL)
                                return spec
                            else:
                                logger.warning(
                                    f"Response from {url} doesn't look like " "OpenAPI spec"
                                )
                        except Exception as e:
                            logger.debug(f"Failed to parse JSON from {url}: {e}")

                except httpx.TimeoutException:
                    logger.warning(f"Timeout fetching {url}")
                except Exception as e:
                    logger.debug(f"Error fetching {url}: {e}")

        logger.warning(f"Could not find OpenAPI spec for {base_url}")
        return None

    def _validate_openapi_spec(self, spec: dict[str, Any]) -> bool:
        """
        Validate that a dict looks like an OpenAPI specification.

        Args:
            spec: Potential OpenAPI spec

        Returns:
            True if looks valid, False otherwise
        """
        if not isinstance(spec, dict):
            return False

        # Check for OpenAPI version markers
        if "openapi" in spec:  # OpenAPI 3.x
            return True
        if "swagger" in spec:  # Swagger 2.x
            return True

        # Check for common OpenAPI structure
        if "paths" in spec and isinstance(spec["paths"], dict):
            return True

        return False

    def synthesize_tools(self, spec: dict[str, Any], base_url: str) -> list[ToolDefinition]:
        """
        Synthesize MCP tool definitions from OpenAPI spec.

        Creates a ToolDefinition for each operation in the OpenAPI spec.

        Args:
            spec: OpenAPI specification
            base_url: Base URL of the API

        Returns:
            List of ToolDefinition instances
        """
        tools = []

        paths = spec.get("paths", {})

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            for method in ["get", "post", "put", "delete", "patch"]:
                operation = path_item.get(method)
                if not operation or not isinstance(operation, dict):
                    continue

                # Build tool name from operationId or path
                operation_id = operation.get("operationId")
                if operation_id:
                    tool_name = operation_id
                else:
                    # Generate name from method and path
                    clean_path = path.strip("/").replace("/", "_")
                    tool_name = f"{method}_{clean_path}"

                # Get description
                description = operation.get(
                    "summary", operation.get("description", f"{method.upper()} {path}")
                )

                # Build input schema from parameters
                input_schema = self._build_input_schema(operation)

                tool_def = ToolDefinition(
                    name=tool_name,
                    description=description,
                    input_schema=input_schema,
                )

                # Store metadata for proxy invocation
                tool_def.base_url = base_url  # type: ignore
                tool_def.path = path  # type: ignore
                tool_def.method = method  # type: ignore

                tools.append(tool_def)

        logger.info(f"Synthesized {len(tools)} tools from OpenAPI spec at {base_url}")
        return tools

    def _build_input_schema(self, operation: dict[str, Any]) -> dict[str, Any]:
        """
        Build JSON schema for tool input from OpenAPI operation.

        Args:
            operation: OpenAPI operation object

        Returns:
            JSON schema dict
        """
        schema = {
            "type": "object",
            "properties": {},
            "required": [],
        }

        # Process parameters (query, path, header)
        parameters = operation.get("parameters", [])
        for param in parameters:
            if not isinstance(param, dict):
                continue

            name = param.get("name")
            if not name:
                continue

            param_schema = param.get("schema", {})
            description = param.get("description", "")

            schema["properties"][name] = {
                **param_schema,
                "description": description,
            }

            if param.get("required"):
                schema["required"].append(name)

        # Process request body
        request_body = operation.get("requestBody")
        if request_body:
            content = request_body.get("content", {})
            json_content = content.get("application/json", {})
            body_schema = json_content.get("schema", {})

            if body_schema:
                schema["properties"]["body"] = body_schema
                if request_body.get("required"):
                    schema["required"].append("body")

        return schema

    async def proxy_invoke(
        self,
        url: str,
        method: str = "GET",
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        json_data: dict[str, Any] | None = None,
        auth_header: str | None = None,
        auth_query_param: str | None = None,
    ) -> dict[str, Any]:
        """
        Proxy an invocation to an external API endpoint.

        Supports various authentication methods:
        - Header-based auth (Bearer tokens, API keys)
        - Query parameter auth

        Args:
            url: Full URL to invoke
            method: HTTP method (GET, POST, etc.)
            params: Query parameters
            headers: HTTP headers
            json_data: JSON request body
            auth_header: Auth header value (e.g., "Bearer token")
            auth_query_param: Auth query parameter name/value

        Returns:
            Response data

        Raises:
            ValueError: For request errors
        """
        params = params or {}
        headers = headers or {}

        # Add user agent
        headers["User-Agent"] = self.user_agent

        # Add authentication if provided
        if auth_header:
            headers["Authorization"] = auth_header

        if auth_query_param:
            # Parse "name=value" format
            if "=" in auth_query_param:
                key, value = auth_query_param.split("=", 1)
                params[key] = value

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method.upper(),
                    url=url,
                    params=params,
                    headers=headers,
                    json=json_data,
                )

                response.raise_for_status()

                # Try to parse JSON response
                try:
                    return response.json()
                except Exception:
                    # Return text response if not JSON
                    return {"text": response.text}

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error proxying to {url}: {e}")
            raise ValueError(
                f"Proxy request failed: {e.response.status_code} " f"{e.response.reason_phrase}"
            )
        except httpx.TimeoutException:
            logger.error(f"Timeout proxying to {url}")
            raise ValueError("Proxy request timed out")
        except Exception as e:
            logger.error(f"Error proxying to {url}: {e}")
            raise ValueError(f"Proxy request failed: {str(e)}")
