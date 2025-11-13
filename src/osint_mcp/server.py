"""Main OSINT MCP Server implementation."""
import logging
from typing import Any

from mcp.server import Server
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
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create MCP server
app = Server("osint-mcp-server")


# Tool definitions
@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available OSINT tools."""
    return [
        Tool(
            name="dns_lookup",
            description="Perform DNS lookup for a domain. Supports various record types (A, AAAA, MX, NS, TXT, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "Domain name to lookup (e.g., example.com)"
                    },
                    "record_type": {
                        "type": "string",
                        "description": "DNS record type (default: A)",
                        "enum": ["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA"],
                        "default": "A"
                    }
                },
                "required": ["domain"]
            }
        ),
        Tool(
            name="reverse_dns_lookup",
            description="Perform reverse DNS lookup for an IP address to find associated hostnames",
            inputSchema={
                "type": "object",
                "properties": {
                    "ip_address": {
                        "type": "string",
                        "description": "IP address to lookup (IPv4 or IPv6)"
                    }
                },
                "required": ["ip_address"]
            }
        ),
        Tool(
            name="get_nameservers",
            description="Get nameserver information for a domain",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "Domain name to lookup"
                    }
                },
                "required": ["domain"]
            }
        ),
        Tool(
            name="get_mx_records",
            description="Get mail exchange (MX) records for a domain",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "Domain name to lookup"
                    }
                },
                "required": ["domain"]
            }
        ),
        Tool(
            name="get_ip_info",
            description="Get geolocation and network information for an IP address",
            inputSchema={
                "type": "object",
                "properties": {
                    "ip_address": {
                        "type": "string",
                        "description": "IP address to lookup"
                    }
                },
                "required": ["ip_address"]
            }
        ),
        Tool(
            name="check_ip_reputation",
            description="Check IP reputation using threat intelligence databases (requires API key)",
            inputSchema={
                "type": "object",
                "properties": {
                    "ip_address": {
                        "type": "string",
                        "description": "IP address to check"
                    }
                },
                "required": ["ip_address"]
            }
        ),
        Tool(
            name="check_robots_txt",
            description="Check robots.txt for a URL and verify if it can be accessed",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to check"
                    }
                },
                "required": ["url"]
            }
        ),
        Tool(
            name="get_http_headers",
            description="Get HTTP headers for a URL (uses HEAD request, minimal bandwidth)",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to check"
                    }
                },
                "required": ["url"]
            }
        ),
        Tool(
            name="extract_metadata",
            description="Extract basic metadata from a webpage (title, description, etc.). Respects robots.txt.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to extract metadata from"
                    }
                },
                "required": ["url"]
            }
        ),
        Tool(
            name="check_ssl_certificate",
            description="Check SSL/TLS certificate information for a domain",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "Domain to check"
                    }
                },
                "required": ["domain"]
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Execute a tool with the given arguments."""
    try:
        logger.info(f"Executing tool: {name} with arguments: {arguments}")

        # Route to appropriate tool
        result = None

        if name == "dns_lookup":
            result = await dns_lookup(
                arguments["domain"],
                arguments.get("record_type", "A")
            )
        elif name == "reverse_dns_lookup":
            result = await reverse_dns_lookup(arguments["ip_address"])
        elif name == "get_nameservers":
            result = await get_nameservers(arguments["domain"])
        elif name == "get_mx_records":
            result = await get_mx_records(arguments["domain"])
        elif name == "get_ip_info":
            result = await get_ip_info(arguments["ip_address"])
        elif name == "check_ip_reputation":
            result = await check_ip_reputation(arguments["ip_address"])
        elif name == "check_robots_txt":
            result = await check_robots_txt(arguments["url"])
        elif name == "get_http_headers":
            result = await get_http_headers(arguments["url"])
        elif name == "extract_metadata":
            result = await extract_metadata(arguments["url"])
        elif name == "check_ssl_certificate":
            result = await check_ssl_certificate(arguments["domain"])
        else:
            result = {
                "success": False,
                "error": f"Unknown tool: {name}"
            }

        # Format result as TextContent
        import json
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]

    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}", exc_info=True)
        error_result = handle_error(e, f"Tool execution: {name}")
        import json
        return [TextContent(
            type="text",
            text=json.dumps(error_result, indent=2)
        )]


def main():
    """Run the OSINT MCP Server."""
    logger.info(f"Starting {config.server_name} v{config.version}")
    logger.info(f"Ethical guardrails enabled: rate_limit={config.ethical_guardrails.rate_limit_per_minute}/min")
    logger.info(f"Respecting robots.txt: {config.ethical_guardrails.respect_robots_txt}")

    import asyncio

    from mcp.server.stdio import stdio_server

    async def run_server():
        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options()
            )

    asyncio.run(run_server())


if __name__ == "__main__":
    main()
