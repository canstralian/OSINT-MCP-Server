"""Main OSINT MCP Server implementation."""

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .config import config
from .tools import (
    check_ip_reputation,
    check_robots_txt,
    check_ssl_certificate,
    dns_lookup,
    extract_metadata,
    get_http_headers,
    get_ip_info,
    get_mx_records,
    get_nameservers,
    reverse_dns_lookup,
)
from .utils import handle_error

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create MCP server
app = Server("osint-mcp-server")


# Tool handler adapters - responsible for parameter shaping and validation
async def _handle_dns_lookup(args: dict[str, Any]) -> dict[str, Any]:
    """Adapter for dns_lookup tool."""
    domain = args["domain"]
    record_type = args.get("record_type", "A")
    return await dns_lookup(domain, record_type)


async def _handle_reverse_dns_lookup(args: dict[str, Any]) -> dict[str, Any]:
    """Adapter for reverse_dns_lookup tool."""
    ip_address = args["ip_address"]
    return await reverse_dns_lookup(ip_address)


async def _handle_get_nameservers(args: dict[str, Any]) -> dict[str, Any]:
    """Adapter for get_nameservers tool."""
    domain = args["domain"]
    return await get_nameservers(domain)


async def _handle_get_mx_records(args: dict[str, Any]) -> dict[str, Any]:
    """Adapter for get_mx_records tool."""
    domain = args["domain"]
    return await get_mx_records(domain)


async def _handle_get_ip_info(args: dict[str, Any]) -> dict[str, Any]:
    """Adapter for get_ip_info tool."""
    ip_address = args["ip_address"]
    return await get_ip_info(ip_address)


async def _handle_check_ip_reputation(args: dict[str, Any]) -> dict[str, Any]:
    """Adapter for check_ip_reputation tool."""
    ip_address = args["ip_address"]
    return await check_ip_reputation(ip_address)


async def _handle_check_robots_txt(args: dict[str, Any]) -> dict[str, Any]:
    """Adapter for check_robots_txt tool."""
    url = args["url"]
    return await check_robots_txt(url)


async def _handle_get_http_headers(args: dict[str, Any]) -> dict[str, Any]:
    """Adapter for get_http_headers tool."""
    url = args["url"]
    return await get_http_headers(url)


async def _handle_extract_metadata(args: dict[str, Any]) -> dict[str, Any]:
    """Adapter for extract_metadata tool."""
    url = args["url"]
    return await extract_metadata(url)


async def _handle_check_ssl_certificate(args: dict[str, Any]) -> dict[str, Any]:
    """Adapter for check_ssl_certificate tool."""
    domain = args["domain"]
    return await check_ssl_certificate(domain)


# Tool handlers dispatch table with type annotation
TOOL_HANDLERS: dict[str, Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]] = {
    "dns_lookup": _handle_dns_lookup,
    "reverse_dns_lookup": _handle_reverse_dns_lookup,
    "get_nameservers": _handle_get_nameservers,
    "get_mx_records": _handle_get_mx_records,
    "get_ip_info": _handle_get_ip_info,
    "check_ip_reputation": _handle_check_ip_reputation,
    "check_robots_txt": _handle_check_robots_txt,
    "get_http_headers": _handle_get_http_headers,
    "extract_metadata": _handle_extract_metadata,
    "check_ssl_certificate": _handle_check_ssl_certificate,
}


# Tool definitions
@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available OSINT tools."""
    return [
        Tool(
            name="dns_lookup",
            description=(
                "Perform DNS lookup for a domain. "
                "Supports various record types (A, AAAA, MX, NS, TXT, etc.)"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "Domain name to lookup (e.g., example.com)",
                    },
                    "record_type": {
                        "type": "string",
                        "description": "DNS record type (default: A)",
                        "enum": ["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA"],
                        "default": "A",
                    },
                },
                "required": ["domain"],
            },
        ),
        Tool(
            name="reverse_dns_lookup",
            description="Perform reverse DNS lookup for an IP address to find associated hostnames",
            inputSchema={
                "type": "object",
                "properties": {
                    "ip_address": {
                        "type": "string",
                        "description": "IP address to lookup (IPv4 or IPv6)",
                    }
                },
                "required": ["ip_address"],
            },
        ),
        Tool(
            name="get_nameservers",
            description="Get nameserver information for a domain",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Domain name to lookup"}
                },
                "required": ["domain"],
            },
        ),
        Tool(
            name="get_mx_records",
            description="Get mail exchange (MX) records for a domain",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Domain name to lookup"}
                },
                "required": ["domain"],
            },
        ),
        Tool(
            name="get_ip_info",
            description="Get geolocation and network information for an IP address",
            inputSchema={
                "type": "object",
                "properties": {
                    "ip_address": {"type": "string", "description": "IP address to lookup"}
                },
                "required": ["ip_address"],
            },
        ),
        Tool(
            name="check_ip_reputation",
            description=(
                "Check IP reputation using threat intelligence databases (requires API key)"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "ip_address": {"type": "string", "description": "IP address to check"}
                },
                "required": ["ip_address"],
            },
        ),
        Tool(
            name="check_robots_txt",
            description="Check robots.txt for a URL and verify if it can be accessed",
            inputSchema={
                "type": "object",
                "properties": {"url": {"type": "string", "description": "URL to check"}},
                "required": ["url"],
            },
        ),
        Tool(
            name="get_http_headers",
            description="Get HTTP headers for a URL (uses HEAD request, minimal bandwidth)",
            inputSchema={
                "type": "object",
                "properties": {"url": {"type": "string", "description": "URL to check"}},
                "required": ["url"],
            },
        ),
        Tool(
            name="extract_metadata",
            description=(
                "Extract basic metadata from a webpage "
                "(title, description, etc.). Respects robots.txt."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to extract metadata from"}
                },
                "required": ["url"],
            },
        ),
        Tool(
            name="check_ssl_certificate",
            description="Check SSL/TLS certificate information for a domain",
            inputSchema={
                "type": "object",
                "properties": {"domain": {"type": "string", "description": "Domain to check"}},
                "required": ["domain"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Execute a tool with the given arguments."""
    try:
        # Validate arguments is a dict
        if not isinstance(arguments, dict):
            logger.error(
                f"Invalid arguments type for tool {name}: "
                f"expected dict, got {type(arguments).__name__}"
            )
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": False,
                            "error": "Invalid request payload: arguments must be a dictionary",
                        },
                        indent=2,
                    ),
                )
            ]

        logger.info(f"Executing tool: {name} with arguments keys: {tuple(arguments.keys())}")

        # Route to appropriate tool handler
        handler = TOOL_HANDLERS.get(name)

        if handler is None:
            result = {"success": False, "error": f"Unknown tool: {name}"}
        else:
            result = await handler(arguments)

        # Format result as TextContent
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}", exc_info=True)
        error_result = handle_error(e, f"Tool execution: {name}")
        return [TextContent(type="text", text=json.dumps(error_result, indent=2))]


def main():
    """Run the OSINT MCP Server."""
    logger.info(f"Starting {config.server_name} v{config.version}")
    logger.info(
        f"Ethical guardrails enabled: "
        f"rate_limit={config.ethical_guardrails.rate_limit_per_minute}/min"
    )
    logger.info(f"Respecting robots.txt: {config.ethical_guardrails.respect_robots_txt}")

    import asyncio

    async def run_server():
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())

    asyncio.run(run_server())


if __name__ == "__main__":
    main()
