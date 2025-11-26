#!/usr/bin/env python3
# app/routes/tools.py
# -*- coding: utf-8 -*-
"""
FastAPI routes for tool discovery and invocation.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.invoke import invoke_tool
from app.tools.registry import get_registry
from app.transports import sse_event

logger = logging.getLogger(__name__)


# Request/Response models
class InvokeRequest(BaseModel):
    """Request model for tool invocation."""

    tool: str
    params: dict[str, Any] = {}
    stream: bool = False


class InvokeResponse(BaseModel):
    """Response model for tool invocation."""

    status: str
    result: dict[str, Any] = {}
    error: str | None = None


# Create router
router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("/", response_model=dict[str, Any])
async def list_tools() -> dict[str, Any]:
    """
    List all available tools.

    Returns both native registered tools and proxied tools
    discovered by ConnectorManager.

    Returns:
        Dictionary containing list of tool definitions
    """
    try:
        registry = get_registry()

        # Get native tool definitions
        native_tools = registry.list_definitions()

        # TODO: Add proxied tools from ConnectorManager
        # For now, just return native tools
        proxied_tools = []

        return {
            "status": "success",
            "tools": {
                "native": native_tools,
                "proxied": proxied_tools,
            },
            "total": len(native_tools) + len(proxied_tools),
        }

    except Exception as e:
        logger.error(f"Error listing tools: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/invoke", response_model=InvokeResponse)
async def invoke(request: InvokeRequest) -> Response:
    """
    Invoke a tool with given parameters.

    Supports both normal and streaming responses based on the
    'stream' parameter and tool capabilities.

    Args:
        request: InvokeRequest containing tool name, params, and stream flag

    Returns:
        Tool result or streaming response

    Raises:
        HTTPException: On errors during invocation
    """
    try:
        # Validate tool exists and get definition
        registry = get_registry()
        tool = registry.get(request.tool)

        if not tool:
            raise HTTPException(status_code=404, detail=f"Tool '{request.tool}' not found")

        definition = tool.definition()

        # Check if streaming is requested but not supported
        if request.stream and not definition.streamable:
            raise HTTPException(
                status_code=400, detail=f"Tool '{request.tool}' does not support streaming"
            )

        # Invoke tool
        result = invoke_tool(request.tool, request.params)

        # Handle streaming response
        if request.stream and definition.streamable:
            # Create SSE stream
            def event_generator():
                # Send result as single event for now
                # Tools can be enhanced to yield multiple events
                yield sse_event(result, event="result")

            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )

        # Normal JSON response
        return {
            "status": "success",
            "result": result,
        }

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Error invoking tool: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check() -> dict[str, str]:
    """
    Health check endpoint for tools service.

    Returns:
        Status message
    """
    return {"status": "ok", "service": "tools"}
