#!/usr/bin/env python3
# app/transports/sse.py
# -*- coding: utf-8 -*-
"""
Server-Sent Events (SSE) support for streaming responses.

This module provides utilities for streaming JSON events via SSE,
compatible with both Flask and FastAPI frameworks.
"""

import json
import logging
from collections.abc import AsyncGenerator, Generator
from typing import Any

logger = logging.getLogger(__name__)


def sse_event(
    data: Any,
    event: str = "message",
    id: str | int | None = None,
    retry: int | None = None,
) -> str:
    """
    Format data as a Server-Sent Event.

    Args:
        data: Data to send (will be JSON-encoded if not a string)
        event: Event type name
        id: Optional event ID
        retry: Optional retry timeout in milliseconds

    Returns:
        Formatted SSE event string

    Example:
        >>> sse_event({"status": "processing"}, event="update", id="1")
        'event: update\\nid: 1\\ndata: {"status": "processing"}\\n\\n'
    """
    lines = []

    if event:
        lines.append(f"event: {event}")

    if id is not None:
        lines.append(f"id: {id}")

    if retry is not None:
        lines.append(f"retry: {retry}")

    # Encode data as JSON if not already a string
    if isinstance(data, str):
        data_str = data
    else:
        try:
            data_str = json.dumps(data)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to JSON-encode SSE data: {e}")
            data_str = json.dumps({"error": "Encoding failed"})

    # Split data into multiple data: lines if it contains newlines
    for line in data_str.split("\n"):
        lines.append(f"data: {line}")

    # SSE messages end with double newline
    return "\n".join(lines) + "\n\n"


def stream(
    generator: Generator[Any, None, None] | AsyncGenerator[Any, None],
) -> Generator[str, None, None] | AsyncGenerator[str, None]:
    """
    Convert a generator of data into SSE-formatted strings.

    Supports both sync and async generators.

    Args:
        generator: Generator yielding data objects

    Yields:
        SSE-formatted event strings

    Example:
        # Sync generator
        def data_gen():
            for i in range(5):
                yield {"count": i}

        # Use with FastAPI
        return StreamingResponse(
            stream(data_gen()),
            media_type="text/event-stream"
        )

        # Async generator
        async def async_data_gen():
            for i in range(5):
                await asyncio.sleep(0.1)
                yield {"count": i}

        return StreamingResponse(
            stream(async_data_gen()),
            media_type="text/event-stream"
        )
    """
    # Check if generator is async
    import inspect

    if inspect.isasyncgen(generator):
        # Async generator
        async def async_stream():
            try:
                event_id = 0
                async for data in generator:
                    yield sse_event(data, id=event_id)
                    event_id += 1

                # Send completion event
                yield sse_event({"status": "complete"}, event="done")
            except Exception as e:
                # Log full error details server-side, send generic error to client
                logger.error(f"Error in SSE stream: {e}", exc_info=True)
                yield sse_event({"error": "Stream error"}, event="error")

        return async_stream()

    else:
        # Sync generator
        def sync_stream():
            try:
                event_id = 0
                for data in generator:
                    yield sse_event(data, id=event_id)
                    event_id += 1

                # Send completion event
                yield sse_event({"status": "complete"}, event="done")
            except Exception as e:
                # Log full error details server-side, send generic error to client
                logger.error(f"Error in SSE stream: {e}", exc_info=True)
                yield sse_event({"error": "Stream error"}, event="error")

        return sync_stream()
