#!/usr/bin/env python3
# app/invoke.py
# -*- coding: utf-8 -*-
"""
Tool invocation helper for OSINT-MCP-Server.

Provides a unified interface for invoking tools by name with
parameter validation and output normalization.
"""

import logging
from typing import Any

from app.tools.registry import get_tool

logger = logging.getLogger(__name__)


def invoke_tool(tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
    """
    Invoke a tool by name with given parameters.

    Validates inputs, calls the tool's invoke method, and normalizes
    the output using the tool's _normalize_output if available.

    Args:
        tool_name: Name of the tool to invoke.
        params: Dictionary of parameters for the tool.

    Returns:
        Normalized result dictionary with keys: text, data, meta.

    Raises:
        ValueError: If tool not found or parameters invalid.
        Exception: For tool-specific errors.
    """
    # Validate tool name
    if not tool_name:
        raise ValueError("tool_name is required")

    if not isinstance(params, dict):
        raise ValueError("params must be a dictionary")

    # Get tool from registry
    tool = get_tool(tool_name)
    if not tool:
        raise ValueError(f"Tool not found: {tool_name}")

    logger.info(f"Invoking tool: {tool_name}")

    try:
        # Invoke the tool
        result = tool.invoke(params)

        # Ensure result has expected structure
        if not isinstance(result, dict):
            logger.warning(f"Tool '{tool_name}' returned non-dict result, normalizing")
            # Try to normalize using tool's method
            if hasattr(tool, "_normalize_output"):
                result = tool._normalize_output(text=str(result), data={"raw": result})
            else:
                result = {"text": str(result), "data": {"raw": result}, "meta": {}}

        # Ensure required keys are present
        if "text" not in result:
            result["text"] = ""
        if "data" not in result:
            result["data"] = {}
        if "meta" not in result:
            result["meta"] = {}

        logger.debug(f"Tool '{tool_name}' invoked successfully")
        return result

    except Exception as e:
        logger.error(f"Tool '{tool_name}' invocation failed: {type(e).__name__}: {e}")
        # Re-raise for caller to handle
        raise
