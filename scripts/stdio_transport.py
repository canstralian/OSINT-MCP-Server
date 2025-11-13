#!/usr/bin/env python3
# scripts/stdio_transport.py
# -*- coding: utf-8 -*-
"""
Newline-delimited JSON stdio transport for MCP tools.

Reads JSON-RPC-like requests from stdin and writes responses to stdout.
Each line should be a JSON object with 'tool' and 'params' fields.
"""

import json
import logging
import sys

# Setup basic logging to stderr so it doesn't interfere with stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


def main():
    """
    Main stdio transport loop.

    Reads newline-delimited JSON from stdin, invokes tools,
    and writes responses to stdout.
    """
    try:
        # Import invoke_tool here to avoid circular imports
        from app.invoke import invoke_tool

        logger.info("Stdio transport started. Reading from stdin...")

        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            try:
                # Parse request
                request = json.loads(line)
                tool_name = request.get("tool")
                params = request.get("params", {})

                if not tool_name:
                    response = {
                        "status": "error",
                        "error": 'Missing "tool" field in request',
                    }
                    print(json.dumps(response), flush=True)
                    continue

                logger.info(f"Invoking tool: {tool_name}")

                # Invoke tool
                result = invoke_tool(tool_name, params)

                # Write response
                response = {
                    "status": "success",
                    "result": result,
                }
                print(json.dumps(response, default=str), flush=True)

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
                response = {
                    "status": "error",
                    "error": f"Invalid JSON: {str(e)}",
                }
                print(json.dumps(response), flush=True)

            except Exception as e:
                logger.error(f"Error invoking tool: {e}", exc_info=True)
                response = {
                    "status": "error",
                    "error": str(e),
                }
                print(json.dumps(response, default=str), flush=True)

    except KeyboardInterrupt:
        logger.info("Stdio transport interrupted by user")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Fatal error in stdio transport: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
