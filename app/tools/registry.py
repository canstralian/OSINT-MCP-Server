#!/usr/bin/env python3
# app/tools/registry.py
# -*- coding: utf-8 -*-
"""
Central registry for OSINT tools.

This module provides a centralized registry for managing tool instances,
allowing dynamic registration and retrieval of tools.
"""

import logging

from app.tools.base import OSINTTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Central registry for managing OSINT tool instances.

    Provides thread-safe registration and retrieval of tools.
    """

    def __init__(self):
        """Initialize empty tool registry."""
        self._tools: dict[str, OSINTTool] = {}

    def register(self, tool: OSINTTool) -> None:
        """
        Register a tool instance.

        Args:
            tool: OSINTTool instance to register

        Raises:
            ValueError: If tool name is empty or already registered
        """
        if not tool.name:
            raise ValueError("Tool must have a non-empty name")

        if tool.name in self._tools:
            logger.warning(f"Tool '{tool.name}' already registered, overwriting")

        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def unregister(self, tool_name: str) -> bool:
        """
        Unregister a tool by name.

        Args:
            tool_name: Name of tool to unregister

        Returns:
            True if tool was unregistered, False if not found
        """
        if tool_name in self._tools:
            del self._tools[tool_name]
            logger.info(f"Unregistered tool: {tool_name}")
            return True
        return False

    def get_tool(self, tool_name: str) -> OSINTTool | None:
        """
        Retrieve a tool by name.

        Args:
            tool_name: Name of tool to retrieve

        Returns:
            OSINTTool instance or None if not found
        """
        return self._tools.get(tool_name)

    def list_tools(self) -> list[str]:
        """
        List all registered tool names.

        Returns:
            List of registered tool names
        """
        return list(self._tools.keys())

    def get_all_tools(self) -> dict[str, OSINTTool]:
        """
        Get all registered tools.

        Returns:
            Dictionary mapping tool names to instances
        """
        return self._tools.copy()


# Global registry instance
_registry: ToolRegistry | None = None


def get_registry() -> ToolRegistry:
    """
    Get or create global tool registry.

    Returns:
        ToolRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def register_tool(tool: OSINTTool) -> None:
    """
    Register a tool in the global registry.

    Args:
        tool: Tool instance to register
    """
    registry = get_registry()
    registry.register(tool)


def get_tool(tool_name: str) -> OSINTTool | None:
    """
    Get a tool from the global registry.

    Args:
        tool_name: Name of tool to retrieve

    Returns:
        Tool instance or None
    """
    registry = get_registry()
    return registry.get_tool(tool_name)


def list_tools() -> list[str]:
    """
    List all registered tool names.

    Returns:
        List of tool names
    """
    registry = get_registry()
    return registry.list_tools()
