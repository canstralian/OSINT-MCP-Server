"""Tests for server.py call_tool implementation."""

from unittest.mock import AsyncMock, patch

import pytest

from osint_mcp.server import call_tool


@pytest.mark.asyncio
async def test_call_tool_validates_arguments_dict():
    """Test that call_tool validates arguments is a dict."""
    # Test with non-dict arguments
    result = await call_tool("dns_lookup", "not a dict")
    assert len(result) == 1
    assert "error" in result[0].text.lower()
    assert "invalid" in result[0].text.lower()


@pytest.mark.asyncio
async def test_call_tool_dns_lookup_with_default_record_type():
    """Test dns_lookup uses default record_type when not provided."""
    with patch("osint_mcp.server.dns_lookup", new_callable=AsyncMock) as mock_dns:
        mock_dns.return_value = {
            "success": True,
            "domain": "example.com",
            "record_type": "A",
            "records": ["93.184.216.34"],
        }

        result = await call_tool("dns_lookup", {"domain": "example.com"})

        # Verify dns_lookup was called with default record_type="A"
        mock_dns.assert_called_once_with("example.com", "A")
        assert len(result) == 1
        # Verify the response contains the expected domain in JSON format
        import json

        response_data = json.loads(result[0].text)
        assert response_data["domain"] == "example.com"
        assert response_data["success"] is True


@pytest.mark.asyncio
async def test_call_tool_dns_lookup_with_custom_record_type():
    """Test dns_lookup respects custom record_type parameter."""
    with patch("osint_mcp.server.dns_lookup", new_callable=AsyncMock) as mock_dns:
        mock_dns.return_value = {
            "success": True,
            "domain": "example.com",
            "record_type": "MX",
            "records": [],
        }

        await call_tool("dns_lookup", {"domain": "example.com", "record_type": "MX"})

        # Verify dns_lookup was called with custom record_type="MX"
        mock_dns.assert_called_once_with("example.com", "MX")


@pytest.mark.asyncio
async def test_call_tool_reverse_dns_lookup():
    """Test reverse_dns_lookup with ip_address parameter."""
    with patch("osint_mcp.server.reverse_dns_lookup", new_callable=AsyncMock) as mock_rdns:
        mock_rdns.return_value = {
            "success": True,
            "ip_address": "8.8.8.8",
            "hostnames": ["dns.google"],
        }

        result = await call_tool("reverse_dns_lookup", {"ip_address": "8.8.8.8"})

        # Verify reverse_dns_lookup was called correctly
        mock_rdns.assert_called_once_with("8.8.8.8")
        assert len(result) == 1


@pytest.mark.asyncio
async def test_call_tool_unknown_tool():
    """Test handling of unknown tool name."""
    result = await call_tool("unknown_tool", {"param": "value"})

    assert len(result) == 1
    assert "unknown" in result[0].text.lower()


@pytest.mark.asyncio
async def test_call_tool_handles_exceptions():
    """Test that call_tool handles exceptions gracefully."""
    with patch("osint_mcp.server.dns_lookup", new_callable=AsyncMock) as mock_dns:
        mock_dns.side_effect = Exception("Test error")

        result = await call_tool("dns_lookup", {"domain": "example.com"})

        assert len(result) == 1
        # Should return error result, not raise exception
        assert "error" in result[0].text.lower() or "fail" in result[0].text.lower()
