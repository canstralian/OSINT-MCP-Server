#!/usr/bin/env python3
# app/tools/base.py
# -*- coding: utf-8 -*-
"""
Base classes and definitions for OSINT tools.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

# Import for backward compatibility
try:
    from app.security.auth import ClientIdentity
except ImportError:
    ClientIdentity = None


@dataclass
class ToolDefinition:
    """
    Dataclass representing a tool's definition for MCP protocol.

    Attributes:
        name: Unique identifier for the tool
        description: Human-readable description of tool functionality
        input_schema: JSON Schema describing expected input parameters
        streamable: Whether the tool supports streaming responses
        metadata: Additional metadata about the tool
    """

    name: str
    description: str
    input_schema: dict[str, Any]
    streamable: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert ToolDefinition to JSON-serializable dictionary.

        Returns:
            Dictionary representation of the tool definition
        """
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "streamable": self.streamable,
            "metadata": self.metadata,
        }


class OsintTool(ABC):
    """
    Abstract base class for OSINT tools.

    All OSINT tools must inherit from this class and implement
    the required methods: definition(), invoke(), and _normalize_output().
    """

    @abstractmethod
    def definition(self) -> ToolDefinition:
        """
        Return the tool's definition.

        Returns:
            ToolDefinition object describing the tool
        """
        pass

    @abstractmethod
    def invoke(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the tool with given parameters.

        Args:
            params: Dictionary of input parameters

        Returns:
            Dictionary containing the normalized tool output

        Raises:
            ValueError: If required parameters are missing or invalid
            Exception: For other execution errors
        """
        pass

    def _normalize_output(
        self, text: str = "", data: Any | None = None, meta: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Normalize tool output to consistent format.

        Args:
            text: Human-readable text representation
            data: Structured data from the tool
            meta: Metadata about the response (timing, source, etc.)

        Returns:
            Dictionary with keys: text, data, meta
        """
        return {
            "text": text,
            "data": data if data is not None else {},
            "meta": meta if meta is not None else {},
        }


# Backward compatibility: OSINTTool class for existing tools
class OSINTTool(ABC):
    """
    Abstract base class for OSINT tools (legacy interface).

    .. deprecated:: 0.1.0
        Use :class:`OsintTool` instead. This class is maintained for backward compatibility only.
    This is kept for backward compatibility with existing tools
    that use the async execute() method interface.
    """

    name: str = ""
    description: str = ""

    @abstractmethod
    async def execute(
        self,
        args: dict[str, Any],
        client: Any,  # ClientIdentity type
    ) -> dict[str, Any]:
        """
        Execute the tool asynchronously.

        Args:
            args: Tool arguments
            client: Client identity

        Returns:
            Result dictionary
        """
        pass
