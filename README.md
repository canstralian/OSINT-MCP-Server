# OSINT MCP Server

A comprehensive Open Source Intelligence (OSINT) Model Context Protocol (MCP) server with proper structure, error handling, and ethical guardrails. This server focuses on gathering publicly available information while respecting privacy, legal boundaries, and ethical standards.

## Features

### 🛡️ Ethical Guardrails
- **Rate Limiting**: Configurable request limits to prevent abuse
- **robots.txt Compliance**: Respects website crawling rules
- **Consent Requirements**: Optional explicit consent for sensitive operations
- **Blocked Domains**: Configurable domain blocklist
- **User Agent Identification**: Clear identification of requests

### 🔍 OSINT Tools

#### DNS & Network Tools
- **DNS Lookup**: Query DNS records (A, AAAA, MX, NS, TXT, CNAME, SOA)
- **Reverse DNS**: Find hostnames associated with IP addresses
- **Nameserver Information**: Get authoritative nameservers for domains
- **MX Records**: Retrieve mail exchange records

#### IP Intelligence
- **IP Geolocation**: Get location and network information for IP addresses
- **IP Reputation**: Check IP addresses against threat intelligence databases (requires API key)

#### Web Intelligence
- **robots.txt Checker**: Verify if URLs can be accessed
- **HTTP Headers**: Retrieve HTTP headers (minimal bandwidth)
- **Metadata Extraction**: Extract webpage metadata (title, description, etc.)
- **SSL Certificate Check**: Verify SSL/TLS configuration

### 🏗️ Architecture
- **Modular Design**: Clean separation of concerns (config, tools, utils)
- **Error Handling**: Comprehensive error handling with detailed logging
- **Rate Limiting**: Token bucket algorithm for fair resource usage
- **Validation**: Input validation and sanitization
- **Async Operations**: Efficient async/await patterns

## Installation

### Prerequisites
- Python 3.10 or higher
- pip or uv package manager

### Install from source

```bash
# Clone the repository
git clone https://github.com/canstralian/OSINT-MCP-Server.git
cd OSINT-MCP-Server

# Install dependencies
pip install -r requirements.txt

# Or install in development mode
pip install -e .
```

## Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` to customize settings:
```bash
# Rate limiting (requests per minute)
OSINT_RATE_LIMIT=10

# User agent for web requests
OSINT_USER_AGENT=OSINT-MCP-Server/0.1.0 (Educational/Research Purpose)

# Optional API Keys
ABUSEIPDB_API_KEY=your_key_here
IPINFO_API_KEY=your_key_here
SHODAN_API_KEY=your_key_here
```

## Usage

### Running the Server

```bash
# Run directly
python -m osint_mcp

# Or use the installed package
osint-mcp-server
```

### Using with MCP Client

The server implements the Model Context Protocol and can be used with any MCP-compatible client (e.g., Claude Desktop, other AI assistants).

Example MCP client configuration:
```json
{
  "mcpServers": {
    "osint": {
      "command": "python",
      "args": ["-m", "osint_mcp"]
    }
  }
}
```

### Example Tool Calls

#### DNS Lookup
```json
{
  "tool": "dns_lookup",
  "arguments": {
    "domain": "example.com",
    "record_type": "A"
  }
}
```

#### IP Geolocation
```json
{
  "tool": "get_ip_info",
  "arguments": {
    "ip_address": "8.8.8.8"
  }
}
```

#### Web Metadata Extraction
```json
{
  "tool": "extract_metadata",
  "arguments": {
    "url": "https://example.com"
  }
}
```

## Project Structure

```
OSINT-MCP-Server/
├── src/
│   └── osint_mcp/
│       ├── __init__.py          # Package initialization
│       ├── __main__.py          # Entry point
│       ├── server.py            # MCP server implementation
│       ├── config/              # Configuration management
│       │   ├── __init__.py
│       │   └── settings.py      # Server and ethical settings
│       ├── tools/               # OSINT tools
│       │   ├── __init__.py
│       │   ├── dns_tools.py     # DNS and domain tools
│       │   ├── ip_tools.py      # IP intelligence tools
│       │   └── web_tools.py     # Web scraping tools
│       └── utils/               # Utility modules
│           ├── __init__.py
│           ├── errors.py        # Error handling
│           ├── rate_limiter.py  # Rate limiting
│           └── validators.py    # Input validation
├── tests/                       # Test suite
├── pyproject.toml              # Project metadata
├── requirements.txt            # Dependencies
├── .env.example               # Example configuration
└── README.md                  # This file
```

## Ethical Guidelines

This server is designed with ethical OSINT practices in mind:

1. **Public Information Only**: Only accesses publicly available information
2. **Respect robots.txt**: Honors website crawling policies
3. **Rate Limiting**: Prevents overwhelming target servers
4. **Transparent Identification**: Uses clear user agent strings
5. **No Exploitation**: Does not attempt to bypass security measures
6. **Privacy Respect**: Does not collect or store personal information
7. **Legal Compliance**: Adheres to applicable laws and regulations

### Recommended Use Cases
✅ Security research and vulnerability assessment (with permission)
✅ Digital footprint analysis for personal or organizational security
✅ Threat intelligence gathering
✅ Domain and infrastructure research
✅ Educational purposes and learning

### Prohibited Use Cases
❌ Unauthorized access or hacking attempts
❌ Harassment or stalking
❌ Privacy violations
❌ Any illegal activities
❌ Bypassing security measures

## Development

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=osint_mcp --cov-report=html
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/
```

## API Keys

Some features require API keys for enhanced functionality:

- **AbuseIPDB**: IP reputation checking (free tier available)
  - Get your key at: https://www.abuseipdb.com/
- **IPInfo**: Enhanced IP geolocation (optional)
  - Get your key at: https://ipinfo.io/
- **Shodan**: Port scanning and service detection (optional)
  - Get your key at: https://www.shodan.io/

The server works without API keys but with limited functionality.

## Contributing

Contributions are welcome! Please ensure your contributions:
1. Follow ethical OSINT principles
2. Include appropriate tests
3. Maintain code quality standards
4. Update documentation as needed

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This tool is provided for educational and research purposes only. Users are responsible for ensuring their use complies with all applicable laws and regulations. The authors and contributors are not responsible for misuse or damage caused by this tool.

Always obtain proper authorization before conducting security research or intelligence gathering on systems or data you do not own or have explicit permission to test.

## Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/canstralian/OSINT-MCP-Server/issues
- Documentation: See this README and inline code documentation

## Acknowledgments

Built with:
- [MCP (Model Context Protocol)](https://modelcontextprotocol.io/)
- [httpx](https://www.python-httpx.org/) - Modern HTTP client
- [dnspython](https://www.dnspython.org/) - DNS toolkit
- [pydantic](https://pydantic.dev/) - Data validation
- [validators](https://validators.readthedocs.io/) - Data validation library
