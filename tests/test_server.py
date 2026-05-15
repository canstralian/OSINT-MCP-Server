"""Tests for the osint_mcp.utils facade and server routing."""

import json

import pytest


def test_utils_facade_exports():
    """Verify all symbols needed by tool modules resolve at import time.

    If this test fails the server/tool modules will raise ImportError at
    startup – nothing will run.
    """
    from osint_mcp.utils import (  # noqa: F401
        DataNotFoundError,
        NetworkError,
        handle_error,
        rate_limiter,
        validate_domain,
        validate_ip_address,
        validate_result,
        validate_url,
    )

    assert DataNotFoundError
    assert NetworkError
    assert callable(handle_error)
    assert rate_limiter is not None
    assert callable(validate_domain)
    assert callable(validate_ip_address)
    assert callable(validate_url)
    assert callable(validate_result)


@pytest.mark.asyncio
async def test_server_list_tools_contains_expected():
    """list_tools() must expose the core public tool surface."""
    from osint_mcp.server import list_tools

    tools = await list_tools()
    names = {t.name for t in tools}

    assert "dns_lookup" in names
    assert "get_ip_info" in names
    assert "extract_metadata" in names


@pytest.mark.asyncio
async def test_server_call_tool_unknown_returns_error():
    """Calling an unknown tool name must return a structured error payload."""
    from osint_mcp.server import call_tool

    out = await call_tool("does_not_exist", {})

    assert len(out) == 1
    payload = out[0].text.lower()
    assert '"success": false' in payload
    assert "unknown tool" in payload


@pytest.mark.asyncio
async def test_server_call_tool_routes(monkeypatch):
    """call_tool must route by name and return the tool's JSON output."""
    import osint_mcp.server as server

    async def fake_dns_lookup(domain, record_type="A"):
        return {
            "success": True,
            "domain": domain,
            "record_type": record_type,
            "records": ["1.2.3.4"],
        }

    monkeypatch.setattr(server, "dns_lookup", fake_dns_lookup)

    out = await server.call_tool("dns_lookup", {"domain": "example.com", "record_type": "A"})

    assert len(out) == 1
    data = json.loads(out[0].text)
    assert data["domain"] == "example.com"
    assert "1.2.3.4" in data["records"]
