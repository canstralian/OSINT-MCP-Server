#!/usr/bin/env python3
# app/tools/registry.py
# -*- coding: utf-8 -*-
"""
Central registry for OSINT tools.
"""

import builtins
import logging

from app.tools.base import OsintTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Central registry for managing OSINT tool instances.

    Provides methods to register, unregister, and retrieve tools.
    """

    def __init__(self):
        """Initialize empty tool registry."""
        self._tools: dict[str, OsintTool] = {}
        logger.info("ToolRegistry initialized")

    def register(self, tool: OsintTool) -> None:
        """
        Register a tool instance.

        Args:
            tool: OsintTool instance to register

        Raises:
            ValueError: If tool with same name already registered
        """
        definition = tool.definition()
        name = definition.name

        if name in self._tools:
            logger.warning(f"Tool {name} already registered, overwriting")

        self._tools[name] = tool
        logger.info(f"Registered tool: {name}")

    def unregister(self, name: str) -> bool:
        """
        Unregister a tool by name.

        Args:
            name: Tool name to unregister

        Returns:
            True if tool was unregistered, False if not found
        """
        if name in self._tools:
            del self._tools[name]
            logger.info(f"Unregistered tool: {name}")
            return True

        logger.warning(f"Tool {name} not found in registry")
        return False

    def get(self, name: str) -> OsintTool | None:
        """
        Retrieve a tool by name.

        Args:
            name: Tool name

        Returns:
            OsintTool instance or None if not found
        """
        return self._tools.get(name)

    def list(self) -> list[str]:
        """
        List all registered tool names.

        Returns:
            List of tool names
        """
        return list(self._tools.keys())

    def list_definitions(self) -> builtins.list[dict]:
        """
        List all tool definitions.

        Returns:
            List of tool definition dicts
        """
        definitions = []
        for tool in self._tools.values():
            definition = tool.definition()
            definitions.append(definition.to_dict())
        return definitions


# Global registry instance
_registry: ToolRegistry | None = None


def get_registry() -> ToolRegistry:
    """
    Get or create global registry instance.

    Returns:
        ToolRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
        _initialize_default_tools()
    return _registry


def _initialize_default_tools() -> None:
    """
    Initialize and register default tools.

    This is called once when the registry is first created.
    """
    try:
        # Import and register Shodan connector
        from app.tools.shodan_connector import ShodanConnector

        shodan = ShodanConnector()
        _registry.register(shodan)
        logger.info("Registered default Shodan connector")

    except Exception as e:
        logger.warning(f"Failed to register Shodan connector: {e}")

    # Add more default tools here as needed
