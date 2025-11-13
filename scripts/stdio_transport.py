#!/usr/bin/env python3
# scripts/stdio_transport.py
# -*- coding: utf-8 -*-
"""
Stdio transport for MCP tools.

Implements a newline-delimited JSON stdio transport that reads tool invocation
requests from stdin and writes results to stdout.

Protocol:
    Input (one JSON object per line):
    {"tool": "tool_name", "params": {...}, "id": "request_id"}

    Output (one JSON object per line):
    {"id": "request_id", "status": "success", "result": {...}}
    {"id": "request_id", "status": "error", "error": "error message"}

Usage:
    python scripts/stdio_transport.py

    # Send request:
    echo '{"tool": "shodan", "params": {"action": "search", "query": "test"}}' \\
        | python scripts/stdio_transport.py
"""

import asyncio
import json
import logging
import sys
from typing import Any

# Add parent directory to path so we can import app modules
sys.path.insert(0, "/home/runner/work/OSINT-MCP-Server/OSINT-MCP-Server")

from app.invoke import invoke_tool

# Configure logging to stderr so it doesn't interfere with stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


def write_response(response: dict[str, Any]) -> None:
    """
    Write JSON response to stdout.

    Args:
        response: Response dictionary
    """
    try:
        json_str = json.dumps(response)
        print(json_str, flush=True)
    except Exception as e:
        logger.error(f"Failed to write response: {e}")
        # Try to send error response
        error_response = {"status": "error", "error": "Failed to serialize response"}
        print(json.dumps(error_response), flush=True)


async def process_request(request: dict[str, Any]) -> dict[str, Any]:
    """
    Process a tool invocation request.

    Args:
        request: Request dictionary

    Returns:
        Response dictionary
    """
    request_id = request.get("id", "unknown")
    tool_name = request.get("tool")
    params = request.get("params", {})

    if not tool_name:
        return {"id": request_id, "status": "error", "error": "Missing required field: tool"}

    try:
        result = await invoke_tool(tool_name, params)
        return {"id": request_id, **result}
    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        return {"id": request_id, "status": "error", "error": str(e)}


async def main() -> None:
    """
    Main stdio transport loop.

    Reads newline-delimited JSON from stdin and writes responses to stdout.
    """
    logger.info("Stdio transport started")

    # Check if stdin is a TTY (interactive mode)
    if sys.stdin.isatty():
        logger.warning("Running in interactive mode. " "Enter JSON requests (one per line):")

    try:
        # Read from stdin line by line
        for line in sys.stdin:
            line = line.strip()

            if not line:
                continue

            try:
                # Parse JSON request
                request = json.loads(line)
                logger.info(f"Received request: {request.get('tool', 'unknown')}")

                # Process request
                response = await process_request(request)

                # Write response
                write_response(response)

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON input: {e}")
                write_response({"status": "error", "error": f"Invalid JSON: {str(e)}"})

            except Exception as e:
                logger.error(f"Unexpected error: {e}", exc_info=True)
                write_response({"status": "error", "error": f"Internal error: {str(e)}"})

    except KeyboardInterrupt:
        logger.info("Stdio transport interrupted")

    except Exception as e:
        logger.error(f"Fatal error in stdio transport: {e}", exc_info=True)
        sys.exit(1)

    logger.info("Stdio transport stopped")


if __name__ == "__main__":
    asyncio.run(main())
