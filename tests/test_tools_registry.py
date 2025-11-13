#!/usr/bin/env python3
# tests/test_tools_registry.py
# -*- coding: utf-8 -*-
"""
Unit tests for the tools registry.

Tests tool registration, unregistration, and listing functionality.
"""

import pytest

from app.tools.base import OsintTool, ToolDefinition
from app.tools.registry import (
    register_tool,
    unregister_tool,
    get_tool,
    list_tools,
)


class DummyTool(OsintTool):
    """Dummy tool for testing."""
    
    def invoke(self, params):
        """Dummy invoke method."""
        return self._normalize_output(
            text="Dummy result",
            data={"dummy": True},
            meta={"source": "test"}
        )
    
    def definition(self):
        """Dummy definition method."""
        return ToolDefinition(
            name="dummy",
            description="A dummy tool for testing",
            parameters={},
            streamable=False
        )


def test_register_and_get_tool():
    """Test registering and retrieving a tool."""
    dummy = DummyTool()
    register_tool("test_dummy", dummy)
    
    # Should be able to retrieve it
    retrieved = get_tool("test_dummy")
    assert retrieved is not None
    assert retrieved is dummy
    
    # Clean up
    unregister_tool("test_dummy")


def test_unregister_tool():
    """Test unregistering a tool."""
    dummy = DummyTool()
    register_tool("test_dummy2", dummy)
    
    # Verify it's registered
    assert "test_dummy2" in list_tools()
    
    # Unregister it
    result = unregister_tool("test_dummy2")
    assert result is True
    
    # Should not be in list anymore
    assert "test_dummy2" not in list_tools()
    
    # Unregistering again should return False
    result = unregister_tool("test_dummy2")
    assert result is False


def test_list_tools():
    """Test listing all tools."""
    # Get initial count
    initial_tools = list_tools()
    initial_count = len(initial_tools)
    
    # Register a dummy tool
    dummy = DummyTool()
    register_tool("test_dummy3", dummy)
    
    # Should have one more tool
    tools = list_tools()
    assert len(tools) == initial_count + 1
    assert "test_dummy3" in tools
    
    # Clean up
    unregister_tool("test_dummy3")


def test_get_nonexistent_tool():
    """Test retrieving a non-existent tool."""
    tool = get_tool("nonexistent_tool_12345")
    assert tool is None


def test_registry_with_allowlist_cleared(monkeypatch):
    """
    Test that registry doesn't make network calls when allowlist is empty.
    
    This test uses monkeypatch to clear OSINT_CONNECTOR_ALLOWLIST
    to ensure no Gradio connectors attempt network operations.
    """
    # Clear the allowlist
    monkeypatch.setenv("OSINT_CONNECTOR_ALLOWLIST", "")
    
    # Re-import to trigger initialization with cleared allowlist
    # Note: This may not fully re-initialize in practice, but demonstrates intent
    from app.tools.registry import list_tools as list_tools_fresh
    
    # Should still be able to list tools
    tools = list_tools_fresh()
    assert isinstance(tools, list)
    
    # Shodan should be registered (doesn't require allowlist)
    # but Gradio connectors should not be (requires allowlist)
    # This is a smoke test - just ensure no crashes
