#!/usr/bin/env python3
# tests/test_tools_registry.py
# -*- coding: utf-8 -*-
"""
Tests for the tools registry module.
"""

from typing import Any

from app.tools.base import OsintTool, ToolDefinition
from app.tools.registry import ToolRegistry


class DummyTool(OsintTool):
    """Dummy tool for testing."""

    def definition(self) -> ToolDefinition:
        """Return dummy tool definition."""
        return ToolDefinition(
            name="dummy_tool",
            description="A dummy tool for testing",
            input_schema={
                "type": "object",
                "properties": {
                    "param1": {"type": "string"},
                },
                "required": ["param1"],
            },
        )

    def invoke(self, params: dict[str, Any]) -> dict[str, Any]:
        """Dummy invoke implementation."""
        return self._normalize_output(
            text=f"Dummy tool executed with: {params.get('param1')}",
            data={"param1": params.get("param1")},
            meta={"tool": "dummy"},
        )


def test_registry_initialization():
    """Test that registry initializes correctly."""
    registry = ToolRegistry()
    assert registry is not None
    assert registry.list() == []


def test_register_tool():
    """Test registering a tool."""
    registry = ToolRegistry()
    tool = DummyTool()

    registry.register(tool)

    assert "dummy_tool" in registry.list()
    assert registry.get("dummy_tool") is not None


def test_unregister_tool():
    """Test unregistering a tool."""
    registry = ToolRegistry()
    tool = DummyTool()

    registry.register(tool)
    assert "dummy_tool" in registry.list()

    result = registry.unregister("dummy_tool")
    assert result is True
    assert "dummy_tool" not in registry.list()

    # Try to unregister non-existent tool
    result = registry.unregister("nonexistent")
    assert result is False


def test_get_tool():
    """Test retrieving a tool."""
    registry = ToolRegistry()
    tool = DummyTool()

    registry.register(tool)

    retrieved = registry.get("dummy_tool")
    assert retrieved is not None
    assert isinstance(retrieved, DummyTool)

    # Try to get non-existent tool
    not_found = registry.get("nonexistent")
    assert not_found is None


def test_list_definitions():
    """Test listing tool definitions."""
    registry = ToolRegistry()
    tool = DummyTool()

    registry.register(tool)

    definitions = registry.list_definitions()
    assert len(definitions) == 1
    assert definitions[0]["name"] == "dummy_tool"
    assert "description" in definitions[0]
    assert "inputSchema" in definitions[0]


def test_tool_invocation():
    """Test that registered tools can be invoked."""
    registry = ToolRegistry()
    tool = DummyTool()

    registry.register(tool)

    retrieved = registry.get("dummy_tool")
    result = retrieved.invoke({"param1": "test_value"})

    assert result is not None
    assert result["text"] == "Dummy tool executed with: test_value"
    assert result["data"]["param1"] == "test_value"
    assert result["meta"]["tool"] == "dummy"


def test_multiple_tools():
    """Test registering multiple tools."""
    registry = ToolRegistry()

    # Create and register multiple dummy tools with different names
    class DummyTool2(DummyTool):
        def definition(self) -> ToolDefinition:
            return ToolDefinition(
                name="dummy_tool_2",
                description="Second dummy tool",
                input_schema={"type": "object", "properties": {}},
            )

    tool1 = DummyTool()
    tool2 = DummyTool2()

    registry.register(tool1)
    registry.register(tool2)

    assert len(registry.list()) == 2
    assert "dummy_tool" in registry.list()
    assert "dummy_tool_2" in registry.list()


def test_tool_overwrite():
    """Test that registering same tool name overwrites."""
    registry = ToolRegistry()
    tool1 = DummyTool()
    tool2 = DummyTool()

    registry.register(tool1)
    registry.register(tool2)

    # Should still only have one tool
    assert len(registry.list()) == 1
