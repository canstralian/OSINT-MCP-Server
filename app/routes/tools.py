#!/usr/bin/env python3
# app/routes/tools.py
# -*- coding: utf-8 -*-
"""
Flask blueprint for tool management and invocation endpoints.

Provides:
  - GET /tools: List all available tools with metadata
  - POST /tools/invoke: Invoke a tool by name with parameters

Supports SSE streaming for tools that declare streamable=True.
"""

import logging

try:
    from flask import Blueprint, jsonify, request

    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    Blueprint = None

from app.invoke import invoke_tool
from app.tools.registry import get_tool, get_tools_metadata

logger = logging.getLogger(__name__)


if FLASK_AVAILABLE:
    # Create blueprint
    tools_blueprint = Blueprint("tools", __name__)

    @tools_blueprint.route("/tools", methods=["GET"])
    def list_tools():
        """
        List all available tools with their metadata.

        Returns:
            JSON response with tools list.
        """
        try:
            tools = get_tools_metadata()
            return jsonify({"status": "ok", "tools": tools, "count": len(tools)})
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            return jsonify({"status": "error", "error": str(e)}), 500

    @tools_blueprint.route("/tools/invoke", methods=["POST"])
    def invoke():
        """
        Invoke a tool by name with parameters.

        Request body:
          {
            "tool": "tool_name",
            "params": {...},
            "stream": false  // optional
          }

        Returns:
            JSON response with invocation result or SSE stream.
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({"status": "error", "error": "Request body must be JSON"}), 400

            tool_name = data.get("tool")
            params = data.get("params", {})
            stream_requested = data.get("stream", False)

            if not tool_name:
                return jsonify({"status": "error", "error": "Parameter 'tool' is required"}), 400

            # Check if streaming is requested and supported
            if stream_requested:
                tool = get_tool(tool_name)
                if tool:
                    definition = tool.definition()
                    if definition.streamable:
                        # TODO: Implement SSE streaming
                        # For now, fall back to regular invocation
                        logger.warning(
                            f"Streaming requested for '{tool_name}' "
                            "but not yet fully implemented"
                        )

            # Invoke the tool
            result = invoke_tool(tool_name, params)

            return jsonify({"status": "ok", "result": result})

        except ValueError as e:
            logger.warning(f"Invalid invocation request: {e}")
            return jsonify({"status": "error", "error": str(e)}), 400

        except Exception as e:
            logger.error(f"Tool invocation failed: {e}")
            return jsonify({"status": "error", "error": str(e)}), 500

else:
    logger.warning("Flask not available, tools_blueprint not created")
    tools_blueprint = None
