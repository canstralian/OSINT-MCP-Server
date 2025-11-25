# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-11-25

### Added
- Initial release of OSINT MCP Server
- Core MCP server implementation with stdio transport
- Comprehensive ethical guardrails system:
  - Token bucket rate limiting (configurable, default 10/min)
  - robots.txt compliance for web requests
  - Domain blocklist support
  - User agent identification
  - Request logging
- DNS and domain tools:
  - DNS lookup (A, AAAA, MX, NS, TXT, CNAME, SOA records)
  - Reverse DNS lookup
  - Nameserver information retrieval
  - MX record retrieval
- IP intelligence tools:
  - IP geolocation (using ip-api.com)
  - IP reputation checking (AbuseIPDB integration)
- Web intelligence tools:
  - robots.txt checker
  - HTTP headers retrieval
  - Web metadata extraction
  - SSL certificate checking
- Utility modules:
  - Comprehensive error handling
  - Input validation and sanitization
  - Rate limiting implementation
  - Configuration management
- Testing infrastructure:
  - 14 unit tests with pytest
  - Test coverage for core functionality
  - Async test support
- Documentation:
  - Comprehensive README
  - Usage examples (EXAMPLES.md)
  - Contributing guidelines (CONTRIBUTING.md)
  - Example configuration (.env.example)
- Code quality:
  - Ruff linting compliance
  - Black code formatting
  - Type hints throughout
  - Google-style docstrings

### Security
- No known security vulnerabilities
- CodeQL security scanning passed
- Input validation on all user inputs
- Rate limiting to prevent abuse
- Ethical guardrails enforced

## [Unreleased]

### Planned Features
- Additional OSINT tools:
  - WHOIS lookup
  - Subdomain enumeration (ethical)
  - Certificate transparency log search
  - GitHub/GitLab public profile lookup
- Enhanced error reporting
- Caching layer for repeated queries
- Performance optimizations
- Additional API integrations (with API keys)
- Extended documentation and tutorials

[0.1.0]: https://github.com/canstralian/OSINT-MCP-Server/releases/tag/v0.1.0
[Unreleased]: https://github.com/canstralian/OSINT-MCP-Server/compare/v0.1.0...HEAD
