#!/usr/bin/env python3
# app/main.py
# -*- coding: utf-8 -*-
"""
FastAPI entrypoint for the OSINT MCP server.
"""

from typing import Any, Dict

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.logging_config import configure_logging
from app.mcp.server import router as mcp_router
from app.security.auth import get_current_client, ClientIdentity

configure_logging()

app = FastAPI(
    title="OSINT MCP Server",
    version="0.1.0",
    description="Production-ready OSINT MCP server with ethical guardrails.",
)


@app.on_event("startup")
async def on_startup() -> None:
    # Place for cache warmups, DB connections, etc.
    settings = get_settings()
    settings.logger.info("OSINT MCP server starting up.")


@app.middleware("http")
async def add_process_time_header(request: Request, call_next) -> JSONResponse:
    # Simple example; you can extend with real metrics.
    response = await call_next(request)
    return response


@app.get("/health", tags=["system"])
async def health_check() -> Dict[str, str]:
    """Basic health endpoint for probes."""
    return {"status": "ok"}


@app.get("/whoami", tags=["system"])
async def whoami(
    client: ClientIdentity = Depends(get_current_client),
) -> Dict[str, Any]:
    """Debug endpoint to inspect client identity."""
    return {
        "client_id": client.client_id,
        "scopes": client.scopes,
    }


# Mount MCP router (JSON-RPC-like interface for tools)
app.include_router(mcp_router, prefix="/mcp", tags=["mcp"])


@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    """Return uniform error schema for HTTPExceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
            },
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Catch-all handler for unhandled exceptions."""
    settings = get_settings()
    settings.logger.exception("Unhandled server error: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "error": {
                "code": "InternalServerError",
                "message": "An unexpected error occurred.",
            },
        },
    )
