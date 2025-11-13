#!/usr/bin/env python3
# app/tools/base.py
# -*- coding: utf-8 -*-
"""
Base classes and dataclasses for OSINT tools.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.security.auth import ClientIdentity


@dataclass
class ToolDefinition:
    """
    Dataclass representing an OSINT tool definition.

    Attributes:
        name: Tool name identifier
        description: Human-readable description
        input_schema: JSON schema for input parameters
        streamable: Whether the tool supports streaming responses
        cacheable: Whether results can be cached
        cache_ttl: Cache time-to-live in seconds
    """

    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    streamable: bool = False
    cacheable: bool = True
    cache_ttl: int = 3600


class OSINTTool(ABC):
    """
    Abstract base class for OSINT tools.

    All tools must implement the execute method and provide tool metadata.
    Tools should follow ethical OSINT practices and handle errors gracefully.
    """

    name: str = ""
    description: str = ""
    cachable: bool = True
    cache_ttl_seconds: int = 3600

    @abstractmethod
    async def execute(
        self,
        args: dict[str, Any],
        client: ClientIdentity,
    ) -> dict[str, Any]:
        """
        Execute the tool with given arguments.

        Args:
            args: Dictionary of input arguments
            client: Client identity for auth/rate limiting

        Returns:
            Dictionary containing tool results

        Raises:
            ValueError: For invalid input
            PermissionError: For authorization issues
        """
        pass

    def definition(self) -> ToolDefinition:
        """
        Return the tool definition with metadata.

        Returns:
            ToolDefinition instance describing this tool
        """
        return ToolDefinition(
            name=self.name,
            description=self.description,
            streamable=False,
            cacheable=self.cachable,
            cache_ttl=self.cache_ttl_seconds,
        )

    def _normalize_output(self, result: Any) -> dict[str, Any]:
        """
        Normalize tool output to consistent schema.

        Args:
            result: Raw tool result

        Returns:
            Dictionary with keys: text, data, meta
        """
        if isinstance(result, dict):
            # If already normalized
            if "text" in result and "data" in result:
                return result

            # Convert to normalized format
            return {
                "text": str(result.get("summary", "")),
                "data": result,
                "meta": {
                    "tool": self.name,
                    "cached": result.get("cached", False),
                },
            }

        # Simple string or other result
        return {"text": str(result), "data": {"result": result}, "meta": {"tool": self.name}}

    def build_cache_key(self, args: dict[str, Any]) -> str:
        """
        Build a cache key from tool arguments.

        Args:
            args: Tool arguments

        Returns:
            Cache key string
        """
        import hashlib
        import json

        sorted_args = json.dumps(args, sort_keys=True)
        args_hash = hashlib.sha256(sorted_args.encode()).hexdigest()[:16]
        return f"tool:{self.name}:{args_hash}"


class OsintTool(OSINTTool):
    """
    Alias for OSINTTool to support both naming conventions.
    """

    pass
