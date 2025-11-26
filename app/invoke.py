#!/usr/bin/env python3
# app/invoke.py
# -*- coding: utf-8 -*-
"""
Tool invocation helper.

Provides a centralized function for invoking tools, used by stdio transport
and tests.
"""

import logging
from typing import Any

from app.security.auth import ClientIdentity
from app.tools.registry import get_registry

logger = logging.getLogger(__name__)


async def invoke_tool(
    tool_name: str, params: dict[str, Any], client_id: str = "anonymous"
) -> dict[str, Any]:
    """
    Invoke a tool by name with parameters.

    Args:
        tool_name: Name of tool to invoke
        params: Tool parameters
        client_id: Client identifier for auth/rate limiting

    Returns:
        Tool result dictionary

    Raises:
        ValueError: If tool not found or invalid params
        PermissionError: For authorization issues

    Example:
        result = await invoke_tool(
            "shodan",
            {"action": "search", "query": "apache"},
            "test-client"
        )
    """
    if not tool_name:
        raise ValueError("tool_name is required")

    if not isinstance(params, dict):
        raise ValueError("params must be a dictionary")

    # Get tool from registry
    registry = get_registry()
    tool = registry.get_tool(tool_name)

    if tool is None:
        available = registry.list_tools()
        raise ValueError(
            f"Tool '{tool_name}' not found. " f"Available tools: {', '.join(available)}"
        )

    # Create client identity
    client = ClientIdentity(client_id=client_id, scopes=[])

    # Execute tool
    try:
        result = await tool.execute(params, client)

        # Normalize output
        normalized = tool._normalize_output(result)

        return {
            "status": "success",
            "tool": tool_name,
            "result": normalized,
        }

    except (ValueError, PermissionError) as e:
        logger.error(f"Tool invocation error: {e}")
        return {
            "status": "error",
            "tool": tool_name,
            "error": str(e),
        }

    except Exception as e:
        logger.error(f"Unexpected error invoking tool: {e}", exc_info=True)
        return {
            "status": "error",
            "tool": tool_name,
            "error": f"Internal error: {str(e)}",
        }
