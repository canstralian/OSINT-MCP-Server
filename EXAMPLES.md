# OSINT MCP Server Examples

This document provides practical examples of using the OSINT MCP Server.

## Basic Usage

### Starting the Server

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python -m osint_mcp
```

The server will start and communicate via stdin/stdout following the Model Context Protocol.

## Tool Examples

### DNS Lookup

Query different types of DNS records:

```json
{
  "tool": "dns_lookup",
  "arguments": {
    "domain": "example.com",
    "record_type": "A"
  }
}
```

Supported record types:
- `A` - IPv4 addresses
- `AAAA` - IPv6 addresses
- `MX` - Mail exchange servers
- `NS` - Nameservers
- `TXT` - Text records
- `CNAME` - Canonical name records
- `SOA` - Start of authority

### Reverse DNS Lookup

Find hostnames associated with an IP address:

```json
{
  "tool": "reverse_dns_lookup",
  "arguments": {
    "ip_address": "8.8.8.8"
  }
}
```

### Get Nameservers

Retrieve authoritative nameservers for a domain:

```json
{
  "tool": "get_nameservers",
  "arguments": {
    "domain": "example.com"
  }
}
```

### Get MX Records

Get mail exchange records for a domain:

```json
{
  "tool": "get_mx_records",
  "arguments": {
    "domain": "example.com"
  }
}
```

### IP Geolocation

Get location and network information for an IP:

```json
{
  "tool": "get_ip_info",
  "arguments": {
    "ip_address": "1.1.1.1"
  }
}
```

Returns:
- Country, region, city
- Latitude/longitude
- Timezone
- ISP and organization
- AS number

### IP Reputation Check

Check if an IP has been reported for malicious activity:

```json
{
  "tool": "check_ip_reputation",
  "arguments": {
    "ip_address": "1.2.3.4"
  }
}
```

**Note:** Requires `ABUSEIPDB_API_KEY` environment variable.

### Check robots.txt

Verify if a URL can be crawled according to robots.txt:

```json
{
  "tool": "check_robots_txt",
  "arguments": {
    "url": "https://example.com/page"
  }
}
```

### Get HTTP Headers

Retrieve HTTP headers for a URL (uses HEAD request):

```json
{
  "tool": "get_http_headers",
  "arguments": {
    "url": "https://example.com"
  }
}
```

### Extract Metadata

Extract webpage metadata (title, description, etc.):

```json
{
  "tool": "extract_metadata",
  "arguments": {
    "url": "https://example.com"
  }
}
```

**Note:** Respects robots.txt automatically.

### Check SSL Certificate

Verify SSL/TLS configuration:

```json
{
  "tool": "check_ssl_certificate",
  "arguments": {
    "domain": "example.com"
  }
}
```

## Configuration

### Environment Variables

Create a `.env` file with:

```bash
# Rate limiting (requests per minute)
OSINT_RATE_LIMIT=10

# User agent
OSINT_USER_AGENT=OSINT-MCP-Server/0.1.0 (Research)

# Optional API keys
ABUSEIPDB_API_KEY=your_key_here
IPINFO_API_KEY=your_key_here
```

### Ethical Guardrails

The server includes built-in ethical protections:

1. **Rate Limiting**: Default 10 requests/minute (configurable)
2. **robots.txt Compliance**: Automatically checked for web requests
3. **Blocked Domains**: Can configure domains to never query
4. **User Agent**: Clearly identifies the server
5. **Request Logging**: All requests are logged

## Integration with MCP Clients

### Claude Desktop

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "osint": {
      "command": "python",
      "args": ["-m", "osint_mcp"],
      "env": {
        "OSINT_RATE_LIMIT": "10",
        "ABUSEIPDB_API_KEY": "your_key_here"
      }
    }
  }
}
```

### Other MCP Clients

Any MCP-compatible client can use this server. Configure it to:
1. Run `python -m osint_mcp` as the command
2. Communicate via stdin/stdout
3. Follow the Model Context Protocol specification

## Error Handling

All tools return consistent error information:

```json
{
  "success": false,
  "error": "Error message",
  "error_type": "InvalidInputError",
  "details": {
    "additional": "context"
  }
}
```

Common error types:
- `InvalidInputError` - Invalid input format
- `RateLimitError` - Rate limit exceeded
- `EthicalViolationError` - Blocked by ethical guardrails
- `NetworkError` - Network/connection issues
- `DataNotFoundError` - Requested data not available

## Best Practices

### 1. Respect Rate Limits

Don't make too many requests too quickly:

```python
# Good: Spread out requests
for domain in domains:
    result = await dns_lookup(domain)
    await asyncio.sleep(1)  # Wait between requests
```

### 2. Handle Errors Gracefully

Always check the `success` field:

```python
result = await get_ip_info(ip_address)
if result.get("success"):
    print(f"Location: {result['country']}, {result['city']}")
else:
    print(f"Error: {result['error']}")
```

### 3. Use Appropriate Tools

- Use DNS lookup for domain information
- Use IP tools for IP addresses
- Don't try to query private IP addresses
- Respect robots.txt for web scraping

### 4. Configure API Keys

Some features require API keys:

```bash
# Get free API keys:
# AbuseIPDB: https://www.abuseipdb.com/
# IPInfo: https://ipinfo.io/

export ABUSEIPDB_API_KEY="your_key"
export IPINFO_API_KEY="your_key"
```

## Troubleshooting

### Rate Limit Errors

If you get rate limit errors, either:
1. Wait before making more requests
2. Increase `OSINT_RATE_LIMIT` in `.env`

### robots.txt Blocks

If robots.txt blocks access:
1. Respect the block (don't bypass it)
2. Check if a different URL path is allowed
3. Contact the website owner for permission

### DNS Lookup Failures

Common causes:
- Domain doesn't exist (NXDOMAIN)
- No records of that type
- DNS server timeout

### Network Timeouts

If requests timeout:
1. Check your internet connection
2. The target server may be slow/down
3. Firewall may be blocking requests

## Security Considerations

### What This Server Does NOT Do

❌ Bypass security measures
❌ Access private/internal networks
❌ Crack passwords or encryption
❌ Exploit vulnerabilities
❌ Access unauthorized data

### What This Server DOES Do

✅ Query public DNS records
✅ Access publicly available web pages
✅ Respect robots.txt and rate limits
✅ Use clear user agent identification
✅ Log all activities

### Legal and Ethical Use

Only use this server for:
- Authorized security research
- Personal domain/IP research
- Threat intelligence (on your own infrastructure)
- Educational purposes
- Public information gathering

Always:
1. Get permission before testing systems you don't own
2. Respect privacy and legal boundaries
3. Follow applicable laws and regulations
4. Use responsibly and ethically

## Support

For issues or questions:
- GitHub Issues: https://github.com/canstralian/OSINT-MCP-Server/issues
- Documentation: See README.md

## License

MIT License - See LICENSE file for details
