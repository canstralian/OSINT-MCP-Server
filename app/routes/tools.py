#!/usr/bin/env python3
# app/routes/tools.py
# -*- coding: utf-8 -*-
"""
Tools API router for listing and invoking OSINT tools.

This module provides:
- GET /tools - List all available tools (native and proxied)
- POST /invoke - Invoke a tool with parameters

Supports streaming responses via SSE for streamable tools.

Usage Examples:
    # List tools
    curl http://localhost:8000/tools

    # Invoke a tool
    curl -X POST http://localhost:8000/invoke \
      -H "Content-Type: application/json" \
      -d '{"tool": "shodan", "params": {"action": "search", "query": "apache"}}'

    # Invoke with streaming
    curl -X POST http://localhost:8000/invoke?stream=true \
      -H "Content-Type: application/json" \
      -d '{"tool": "streamable_tool", "params": {}}'
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.security.auth import ClientIdentity
from app.tools.registry import get_registry
from app.transports.sse import stream

logger = logging.getLogger(__name__)

router = APIRouter()


class InvokeRequest(BaseModel):
    """Request model for tool invocation."""

    tool: str
    params: dict[str, Any] = {}


class ToolInfo(BaseModel):
    """Tool information model."""

    name: str
    description: str
    streamable: bool = False
    cacheable: bool = True


class InvokeResponse(BaseModel):
    """Response model for tool invocation."""

    status: str
    result: dict[str, Any] | None = None
    error: str | None = None


@router.get("/tools", response_model=list[ToolInfo])
async def list_tools() -> list[ToolInfo]:
    """
    List all available OSINT tools.

    Returns both native registered tools and any proxied tools discovered
    by connectors (Gradio endpoints, OpenAPI connectors, etc.).

    Returns:
        List of tool information objects

    Example:
        GET /tools

        Response:
        [
          {
            "name": "shodan",
            "description": "Search Shodan database...",
            "streamable": false,
            "cacheable": true
          },
          ...
        ]
    """
    registry = get_registry()
    tools = registry.get_all_tools()

    tool_list = []
    for tool_name, tool in tools.items():
        try:
            definition = tool.definition()
            tool_info = ToolInfo(
                name=definition.name,
                description=definition.description,
                streamable=definition.streamable,
                cacheable=definition.cacheable,
            )
            tool_list.append(tool_info)
        except Exception as e:
            logger.error(f"Error getting definition for tool {tool_name}: {e}")

    return tool_list


@router.post("/invoke", response_model=InvokeResponse)
async def invoke_tool(
    request: InvokeRequest,
    stream_output: bool = Query(False, alias="stream"),
) -> InvokeResponse:
    """
    Invoke an OSINT tool with parameters.

    Handles both local and proxied tool invocations. Supports streaming
    responses for tools that declare streamable=True in their definition.

    Args:
        request: Tool invocation request
        stream_output: Enable SSE streaming for streamable tools

    Returns:
        Tool invocation result

    Raises:
        HTTPException: For various error conditions

    Example (non-streaming):
        POST /invoke
        {
          "tool": "shodan",
          "params": {
            "action": "search",
            "query": "apache"
          }
        }

        Response:
        {
          "status": "success",
          "result": {
            "text": "Shodan search for 'apache' found 1000 results",
            "data": {...},
            "meta": {...}
          }
        }

    Example (streaming):
        POST /invoke?stream=true
        {
          "tool": "streaming_tool",
          "params": {}
        }

        Returns: text/event-stream response
    """
    registry = get_registry()
    tool = registry.get_tool(request.tool)

    if tool is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Tool '{request.tool}' not found"
        )

    # Get tool definition to check capabilities
    try:
        definition = tool.definition()
    except Exception as e:
        logger.error(f"Error getting tool definition: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get tool definition",
        )

    # Validate streaming request
    if stream_output and not definition.streamable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tool '{request.tool}' does not support streaming",
        )

    # Create a dummy client identity for now
    # In production, this should come from authentication
    client = ClientIdentity(client_id="anonymous", scopes=[])

    # Execute the tool
    try:
        if stream_output:
            # Return streaming response
            async def result_generator():
                # For now, execute once and wrap in SSE
                # A true streaming tool would yield multiple results
                result = await tool.execute(request.params, client)
                normalized = tool._normalize_output(result)
                yield normalized

            return StreamingResponse(
                stream(result_generator()),
                media_type="text/event-stream",
            )

        else:
            # Standard invocation
            result = await tool.execute(request.params, client)
            normalized = tool._normalize_output(result)

            return InvokeResponse(
                status="success",
                result=normalized,
            )

    except ValueError as e:
        logger.warning(f"Invalid input for tool {request.tool}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except PermissionError as e:
        logger.warning(f"Permission denied for tool {request.tool}: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    except Exception as e:
        logger.error(f"Error executing tool {request.tool}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tool execution failed: {str(e)}",
        )
