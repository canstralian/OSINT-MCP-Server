#!/usr/bin/env python3
# tests/test_tools_registry.py
# -*- coding: utf-8 -*-
"""
Unit tests for tools registry and connectors.

Simple smoke tests to verify tools can be registered and basic functionality
works with mocked environment variables.
"""

import os
from unittest.mock import patch

import pytest

# Skip all tests in this file if fastapi is not installed
# These tests require the app/ directory which has FastAPI dependencies
pytest.importorskip("fastapi")

from app.tools.gradio_connector import GradioConnector
from app.tools.registry import ToolRegistry, get_registry
from app.tools.shodan_connector import ShodanConnector


def test_registry_create():
    """Test creating a new registry."""
    registry = ToolRegistry()
    assert registry is not None
    assert len(registry.list_tools()) == 0


def test_registry_register_tool():
    """Test registering a tool."""
    registry = ToolRegistry()

    # Create a mock tool
    with patch.dict(os.environ, {"SHODAN_API_KEY": "test_key"}):
        tool = ShodanConnector()
        registry.register(tool)

    assert "shodan" in registry.list_tools()
    retrieved = registry.get_tool("shodan")
    assert retrieved is not None
    assert retrieved.name == "shodan"


def test_registry_unregister_tool():
    """Test unregistering a tool."""
    registry = ToolRegistry()

    with patch.dict(os.environ, {"SHODAN_API_KEY": "test_key"}):
        tool = ShodanConnector()
        registry.register(tool)

    assert "shodan" in registry.list_tools()

    success = registry.unregister("shodan")
    assert success is True
    assert "shodan" not in registry.list_tools()


def test_registry_get_nonexistent_tool():
    """Test getting a tool that doesn't exist."""
    registry = ToolRegistry()
    tool = registry.get_tool("nonexistent")
    assert tool is None


def test_shodan_connector_creation():
    """Test creating Shodan connector with mocked API key."""
    with patch.dict(os.environ, {"SHODAN_API_KEY": "test_key"}):
        connector = ShodanConnector()
        assert connector.name == "shodan"
        assert connector.api_key == "test_key"


def test_shodan_connector_definition():
    """Test Shodan connector tool definition."""
    with patch.dict(os.environ, {"SHODAN_API_KEY": "test_key"}):
        connector = ShodanConnector()
        definition = connector.definition()

        assert definition.name == "shodan"
        assert definition.description != ""
        assert "action" in definition.input_schema.get("properties", {})


def test_gradio_connector_creation():
    """Test creating Gradio connector."""
    connector = GradioConnector()
    assert connector.name == "gradio"


def test_gradio_connector_allowlist():
    """Test Gradio connector URL allowlist."""
    with patch.dict(os.environ, {"OSINT_CONNECTOR_ALLOWLIST": "https://example.com"}):
        connector = GradioConnector()
        assert connector._is_allowed("https://example.com")
        assert not connector._is_allowed("https://evil.com")


def test_gradio_connector_definition():
    """Test Gradio connector tool definition."""
    connector = GradioConnector()
    definition = connector.definition()

    assert definition.name == "gradio"
    assert definition.description != ""
    assert "action" in definition.input_schema.get("properties", {})


def test_global_registry():
    """Test global registry singleton."""
    registry1 = get_registry()
    registry2 = get_registry()
    assert registry1 is registry2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
