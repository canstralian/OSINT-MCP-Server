#!/usr/bin/env python3
# app/tools/base.py
# -*- coding: utf-8 -*-
"""
Base classes and dataclasses for OSINT tools.

This module defines the abstract interface for OSINT tools and
the ToolDefinition schema used by the connector system.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolDefinition:
    """
    Schema describing a tool's metadata, parameters, and capabilities.
    
    Used by the connector system to expose tool information
    to clients and validate invocations.
    """
    
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    streamable: bool = False
    requires_auth: bool = False
    category: Optional[str] = None
    version: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert ToolDefinition to a dictionary.
        
        Returns:
            Dict representation of the tool definition.
        """
        return asdict(self)


class OsintTool(ABC):
    """
    Abstract base class for all OSINT tools.
    
    Tools should inherit from this class and implement the invoke() method.
    The _normalize_output() method ensures consistent response format.
    """
    
    @abstractmethod
    def invoke(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the tool with given parameters.
        
        Args:
            params: Dictionary of parameters for the tool invocation.
            
        Returns:
            Dictionary containing the tool's results.
            
        Raises:
            ValueError: If parameters are invalid.
            Exception: For any tool-specific errors.
        """
        pass
    
    def _normalize_output(
        self, 
        text: Optional[str] = None, 
        data: Optional[Any] = None, 
        meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Normalize tool output to a consistent format.
        
        All tools should return results with text, data, and meta keys
        for consistent handling by the connector infrastructure.
        
        Args:
            text: Human-readable text summary of results.
            data: Structured data (list, dict, etc.).
            meta: Metadata about the invocation (timing, source, etc.).
            
        Returns:
            Dictionary with keys: text, data, meta.
        """
        return {
            "text": text or "",
            "data": data or {},
            "meta": meta or {}
        }
    
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """
        Return the tool's definition metadata.
        
        Returns:
            ToolDefinition describing this tool.
        """
        pass


# Compatibility alias for existing code
OSINTTool = OsintTool
