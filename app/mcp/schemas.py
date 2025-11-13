#!/usr/bin/env python3
# app/mcp/schemas.py
# -*- coding: utf-8 -*-
"""
MCP request and response schemas.
"""

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class MCPToolRequest(BaseModel):
    """Generic MCP tool invocation request."""

    request_id: str = Field(..., alias="requestId")
    tool_name: str = Field(..., alias="tool")
    args: Dict[str, Any] = Field(default_factory=dict)


class MCPError(BaseModel):
    """Error payload returned by tools or server."""

    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class MCPToolResponse(BaseModel):
    """Standard response envelope for MCP tool calls."""

    request_id: str = Field(..., alias="requestId")
    tool_name: str = Field(..., alias="tool")
    status: Literal["success", "error"]
    data: Optional[Dict[str, Any]] = None
    error: Optional[MCPError] = None
