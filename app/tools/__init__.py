#!/usr/bin/env python3
# app/tools/__init__.py
# -*- coding: utf-8 -*-
"""
Tool registry for MCP server.

This module maintains backward compatibility with the existing tool system
while also supporting the new registry-based approach.
"""

import logging
import os

from app.tools.base import OSINTTool
from app.tools.domain_recon import DomainReconTool
from app.tools.registry import get_registry

logger = logging.getLogger(__name__)

# Legacy tools dict for backward compatibility
_TOOLS: dict[str, OSINTTool] = {
    DomainReconTool.name: DomainReconTool(),
}


def get_tool(name: str) -> OSINTTool | None:
    """
    Retrieve a tool instance by name.

    First checks the new registry, then falls back to legacy _TOOLS dict.

    Args:
        name: Tool name

    Returns:
        OSINTTool instance or None
    """
    # Try new registry first
    registry = get_registry()
    tool = registry.get_tool(name)
    if tool:
        return tool

    # Fall back to legacy dict
    return _TOOLS.get(name)


def initialize_tools():
    """
    Initialize and register all available tools.

    Registers domain_recon and conditionally registers Shodan/Gradio connectors
    if API keys are configured.
    """
    registry = get_registry()

    # Register domain recon tool
    domain_tool = DomainReconTool()
    registry.register(domain_tool)
    logger.info("Registered domain_recon tool")

    # Register Shodan connector if API key is available
    shodan_api_key = os.getenv("SHODAN_API_KEY")
    if shodan_api_key:
        try:
            from app.tools.shodan_connector import ShodanConnector

            shodan = ShodanConnector()
            registry.register(shodan)
            logger.info("Registered Shodan connector")
        except Exception as e:
            logger.warning(f"Failed to register Shodan connector: {e}")
    else:
        logger.info("SHODAN_API_KEY not set, Shodan connector not registered")

    # Register Gradio connector if allowlist is configured
    connector_allowlist = os.getenv("OSINT_CONNECTOR_ALLOWLIST")
    if connector_allowlist:
        try:
            from app.tools.gradio_connector import GradioConnector

            gradio = GradioConnector()
            registry.register(gradio)
            logger.info("Registered Gradio connector")
        except Exception as e:
            logger.warning(f"Failed to register Gradio connector: {e}")
    else:
        logger.info("OSINT_CONNECTOR_ALLOWLIST not set, " "Gradio connector not registered")

    logger.info(f"Tool initialization complete. Available tools: {registry.list_tools()}")


# Auto-initialize tools on import
try:
    initialize_tools()
except Exception as e:
    logger.error(f"Error initializing tools: {e}", exc_info=True)
