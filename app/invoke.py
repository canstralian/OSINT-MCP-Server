#!/usr/bin/env python3
# app/invoke.py
# -*- coding: utf-8 -*-
"""
Tool invocation helper for unified tool execution.
"""

import logging
from typing import Any

from app.tools.registry import get_registry

logger = logging.getLogger(__name__)


def invoke_tool(tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
    """
    Invoke a tool by name with given parameters.

    This is the central entry point for tool invocation, used by
    both the HTTP API and stdio transport.

    Args:
        tool_name: Name of the tool to invoke
        params: Dictionary of parameters for the tool

    Returns:
        Tool result dictionary with normalized output

    Raises:
        ValueError: If tool not found or parameters invalid
    """
    # Input validation
    if not tool_name or not isinstance(tool_name, str):
        raise ValueError("tool_name must be a non-empty string")

    if params is None:
        params = {}

    if not isinstance(params, dict):
        raise ValueError("params must be a dictionary")

    # Get tool from registry
    registry = get_registry()
    tool = registry.get(tool_name)

    if not tool:
        available_tools = registry.list()
        raise ValueError(
            f"Tool '{tool_name}' not found. " f"Available tools: {', '.join(available_tools)}"
        )

    # Invoke tool
    logger.info(f"Invoking tool: {tool_name} with params: {params}")

    try:
        result = tool.invoke(params)
        logger.info(f"Tool {tool_name} executed successfully")
        return result

    except Exception as e:
        logger.error(f"Tool {tool_name} execution failed: {e}", exc_info=True)
        # Re-raise to let caller handle
        raise
