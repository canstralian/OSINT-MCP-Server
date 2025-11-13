#!/usr/bin/env python3
# app/mcp/server.py
# -*- coding: utf-8 -*-
"""
MCP router that dispatches tool calls.
"""

from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status

from app.cache.redis_cache import get_cache
from app.mcp.schemas import MCPToolRequest, MCPToolResponse, MCPError
from app.security.auth import ClientIdentity, get_current_client
from app.tools import registry
from app.tools.base import OSINTTool
from app.validators.targets import validate_target_constraints

router = APIRouter()


@router.post("/tool", response_model=MCPToolResponse)
async def invoke_tool(
    request: MCPToolRequest,
    client: ClientIdentity = Depends(get_current_client),
) -> MCPToolResponse:
    """
    Invoke an OSINT tool via MCP.
    This is a simple JSON endpoint; you can wrap JSON-RPC semantics above it.
    """
    tool: OSINTTool = registry.get_tool(request.tool_name)
    if tool is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{request.tool_name}' not found.",
        )

    # Basic ethical guardrail: validate input target fields if present.
    validate_target_constraints(request.args)

    cache = await get_cache()
    cache_key = tool.build_cache_key(request.args)

    if tool.cachable:
        cached = await cache.get(cache_key)
        if cached is not None:
            return MCPToolResponse(
                requestId=request.request_id,
                tool=request.tool_name,
                status="success",
                data={"cached": True, "result": cached},
            )

    try:
        result: Dict = await tool.execute(args=request.args, client=client)
    except ValueError as exc:
        # Input-related errors
        return MCPToolResponse(
            requestId=request.request_id,
            tool=request.tool_name,
            status="error",
            error=MCPError(
                code="InvalidInput",
                message=str(exc),
            ),
        )
    except PermissionError as exc:
        return MCPToolResponse(
            requestId=request.request_id,
            tool=request.tool_name,
            status="error",
            error=MCPError(
                code="Forbidden",
                message=str(exc),
            ),
        )
    except Exception as exc:
        # System / unexpected errors
        return MCPToolResponse(
            requestId=request.request_id,
            tool=request.tool_name,
            status="error",
            error=MCPError(
                code="InternalError",
                message="Tool execution failed.",
                details={"hint": str(exc)},
            ),
        )

    if tool.cachable:
        await cache.set(cache_key, result, ttl_seconds=tool.cache_ttl_seconds)

    return MCPToolResponse(
        requestId=request.request_id,
        tool=request.tool_name,
        status="success",
        data=result,
    )
