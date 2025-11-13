#!/usr/bin/env python3
# app/tools/registry.py
# -*- coding: utf-8 -*-
"""
Central tool registry for OSINT-MCP-Server.

Manages registration and lookup of all available tools, including
connectors for Shodan and Gradio applications.
"""

import logging
import os

from app.tools.base import OsintTool
from app.tools.gradio_connector import GradioConnector
from app.tools.shodan_connector import ShodanConnector

logger = logging.getLogger(__name__)


# Global registry mapping tool names to tool instances
_REGISTRY: dict[str, OsintTool] = {}


def _initialize_default_tools():
    """
    Initialize default tools at import time.

    Registers ShodanConnector and GradioConnectors for any
    base URLs in OSINT_CONNECTOR_ALLOWLIST.
    """
    # Register Shodan connector
    try:
        shodan = ShodanConnector()
        register_tool("shodan", shodan)
        logger.info("Registered ShodanConnector")
    except Exception as e:
        logger.warning(f"Failed to register ShodanConnector: {e}")

    # Register Gradio connectors for allowlisted URLs
    allowlist_str = os.getenv("OSINT_CONNECTOR_ALLOWLIST", "")
    allowlist = [url.strip() for url in allowlist_str.split(",") if url.strip()]

    for base_url in allowlist:
        try:
            gradio = GradioConnector(base_url)
            # Use normalized name for the tool
            tool_name = f"gradio_{base_url.replace('://', '_').replace('/', '_').replace('.', '_')}"
            register_tool(tool_name, gradio)
            logger.info(f"Registered GradioConnector for {base_url}")
        except Exception as e:
            logger.warning(f"Failed to register GradioConnector for {base_url}: {e}")


def register_tool(tool_name: str, tool: OsintTool) -> None:
    """
    Register a tool in the global registry.

    Args:
        tool_name: Unique name for the tool.
        tool: OsintTool instance.
    """
    _REGISTRY[tool_name] = tool
    logger.debug(f"Registered tool: {tool_name}")


def unregister_tool(tool_name: str) -> bool:
    """
    Unregister a tool from the global registry.

    Args:
        tool_name: Name of the tool to unregister.

    Returns:
        True if tool was unregistered, False if not found.
    """
    if tool_name in _REGISTRY:
        del _REGISTRY[tool_name]
        logger.debug(f"Unregistered tool: {tool_name}")
        return True
    return False


def get_tool(tool_name: str) -> OsintTool | None:
    """
    Retrieve a tool instance by name.

    Args:
        tool_name: Name of the tool.

    Returns:
        OsintTool instance or None if not found.
    """
    return _REGISTRY.get(tool_name)


def list_tools() -> list[str]:
    """
    List all registered tool names.

    Returns:
        List of tool names.
    """
    return list(_REGISTRY.keys())


def get_tools_metadata() -> list[dict[str, any]]:
    """
    Get metadata for all registered tools.

    Returns:
        List of tool definition dictionaries.
    """
    metadata = []
    for name, tool in _REGISTRY.items():
        try:
            definition = tool.definition()
            tool_dict = definition.to_dict()
            tool_dict["name"] = name  # Ensure name matches registry key
            metadata.append(tool_dict)
        except Exception as e:
            logger.warning(f"Failed to get definition for tool '{name}': {e}")
    return metadata


# Initialize default tools when module is imported
_initialize_default_tools()
