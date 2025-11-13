#!/usr/bin/env python3
# app/transports/sse.py
# -*- coding: utf-8 -*-
"""
Server-Sent Events (SSE) transport helpers.

Provides utilities for streaming responses using SSE format.
"""

import json
from collections.abc import Generator
from typing import Any

try:
    from flask import Response
except ImportError:
    # Flask may not be available in all contexts
    Response = None


def sse_event(data: Any, event: str | None = None) -> str:
    """
    Format data as an SSE event.

    Args:
        data: Data to send (will be JSON serialized).
        event: Optional event type.

    Returns:
        Formatted SSE event string.
    """
    msg = ""
    if event:
        msg += f"event: {event}\n"
    msg += f"data: {json.dumps(data, default=str)}\n\n"
    return msg


def stream(generator: Generator[Any, None, None]):
    """
    Create a Flask Response for SSE streaming.

    Args:
        generator: Generator yielding data to stream.

    Returns:
        Flask Response with SSE content type.

    Raises:
        ImportError: If Flask is not available.
    """
    if Response is None:
        raise ImportError("Flask is required for SSE streaming")

    def event_stream():
        """Wrap generator to format as SSE events."""
        try:
            for item in generator:
                yield sse_event(item)
        except Exception as e:
            # Send error event
            yield sse_event({"error": str(e), "type": type(e).__name__}, event="error")

    return Response(
        event_stream(),
        content_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
