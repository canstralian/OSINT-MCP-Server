#!/usr/bin/env python3
# scripts/stdio_transport.py
# -*- coding: utf-8 -*-
"""
Newline-delimited JSON stdio transport for OSINT-MCP-Server.

Provides a simple protocol for tool invocation over stdin/stdout:
  Request:  {"id": "req1", "tool": "shodan", "params": {...}}
  Response: {"id": "req1", "status": "ok", "result": {...}}
  Error:    {"id": "req1", "status": "error", "error": "message"}
"""

import json
import logging
import sys
from typing import Any

# Import invoke_tool from app.invoke
try:
    from app.invoke import invoke_tool
except ImportError:
    # Fallback if module not found
    def invoke_tool(tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        return {"error": "app.invoke module not available", "tool": tool_name}


# Configure logging to stderr to not interfere with stdout protocol
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", stream=sys.stderr
)
logger = logging.getLogger(__name__)


def process_request(request: dict[str, Any]) -> dict[str, Any]:
    """
    Process a single tool invocation request.

    Args:
        request: Request dict with id, tool, and params.

    Returns:
        Response dict with id, status, and result or error.
    """
    request_id = request.get("id", "unknown")
    tool_name = request.get("tool")
    params = request.get("params", {})

    if not tool_name:
        return {"id": request_id, "status": "error", "error": "Missing 'tool' field in request"}

    try:
        logger.info(f"Invoking tool '{tool_name}' (request_id={request_id})")
        result = invoke_tool(tool_name, params)

        return {"id": request_id, "status": "ok", "result": result}

    except Exception as e:
        logger.error(f"Tool invocation failed for '{tool_name}': {type(e).__name__}: {e}")
        return {"id": request_id, "status": "error", "error": f"{type(e).__name__}: {str(e)}"}


def main():
    """
    Main stdio transport loop.

    Reads newline-delimited JSON from stdin and writes responses to stdout.
    """
    logger.info("OSINT-MCP stdio transport started")

    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
                response = process_request(request)

                # Write response to stdout
                print(json.dumps(response), flush=True)

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON input: {e}")
                error_response = {
                    "id": "unknown",
                    "status": "error",
                    "error": f"Invalid JSON: {str(e)}",
                }
                print(json.dumps(error_response), flush=True)

            except Exception as e:
                logger.exception(f"Unexpected error: {e}")
                error_response = {
                    "id": "unknown",
                    "status": "error",
                    "error": f"Unexpected error: {str(e)}",
                }
                print(json.dumps(error_response), flush=True)

    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down")

    finally:
        logger.info("OSINT-MCP stdio transport stopped")


if __name__ == "__main__":
    main()
