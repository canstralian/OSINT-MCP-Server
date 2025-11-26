#!/usr/bin/env python3
# app/transports/sse.py
# -*- coding: utf-8 -*-
"""
Server-Sent Events (SSE) transport for streaming responses.
"""

import json
from collections.abc import Generator
from typing import Any


def sse_event(data: Any, event: str = "message", event_id: str | None = None) -> str:
    """
    Format data as an SSE event.

    Args:
        data: Data to send (will be JSON-serialized)
        event: Event type (default: "message")
        event_id: Optional event ID

    Returns:
        Formatted SSE event string
    """
    lines = []

    if event_id:
        lines.append(f"id: {event_id}")

    if event:
        lines.append(f"event: {event}")

    # Serialize data to JSON
    if isinstance(data, (dict, list)):
        data_str = json.dumps(data, default=str)
    else:
        data_str = str(data)

    # Split data into lines for proper SSE format
    for line in data_str.split("\n"):
        lines.append(f"data: {line}")

    # SSE events end with double newline
    lines.append("")
    lines.append("")

    return "\n".join(lines)


def stream(
    generator: Generator[Any, None, None], event: str = "message"
) -> Generator[str, None, None]:
    """
    Stream data from a generator as SSE events.

    Args:
        generator: Generator producing data items
        event: Event type for all events (default: "message")

    Yields:
        Formatted SSE event strings
    """
    event_id = 0

    for data in generator:
        event_id += 1
        yield sse_event(data, event=event, event_id=str(event_id))
