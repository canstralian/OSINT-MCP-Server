# HF-MCP-Style Connector System Usage Guide

This document describes how to use the HF-MCP-style connector system added to OSINT-MCP-Server.

## Overview

The connector system provides:
- **Unified Tool Interface**: ToolDefinition dataclass and OsintTool base class
- **Redis Caching**: Configurable TTL caching with safe failure handling
- **OpenAPI/Gradio Discovery**: Automatic spec discovery and tool synthesis
- **Secure Proxying**: Allowlist-based endpoint proxying with timeout controls
- **Multiple Transports**: Stdio (JSON-RPC-like) and HTTP (Flask blueprint)

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Required for Shodan connector
export SHODAN_API_KEY=your_shodan_api_key_here

# Optional: Redis caching (defaults to redis://localhost:6379/0)
export REDIS_URL=redis://localhost:6379/0

# Optional: Custom user agent
export OSINT_USER_AGENT="osint-mcp/1.0"

# Optional: Allowlist for Gradio/external API connectors
export OSINT_CONNECTOR_ALLOWLIST="https://my-app1.example,https://my-app2.example"
```

### 3. Using the Stdio Transport

The stdio transport provides a simple JSON protocol over stdin/stdout:

```bash
# Run the transport
python scripts/stdio_transport.py

# Send requests (one JSON object per line):
{"id": "req1", "tool": "shodan", "params": {"action": "search", "query": "apache"}}

# Receive responses:
{"id": "req1", "status": "ok", "result": {...}}
```

### 4. Using the Flask Blueprint

```python
from flask import Flask
from app.routes.tools import tools_blueprint

app = Flask(__name__)
app.register_blueprint(tools_blueprint)

if __name__ == '__main__':
    app.run()
```

Then use the HTTP endpoints:

```bash
# List available tools
curl http://localhost:5000/tools

# Invoke a tool
curl -X POST http://localhost:5000/tools/invoke \
  -H "Content-Type: application/json" \
  -d '{"tool": "shodan", "params": {"action": "search", "query": "apache"}}'
```

## Available Tools

### Shodan Connector

**Tool Name**: `shodan`

**Actions**:
- `search` - Search Shodan database
- `host` - Lookup host information

**Parameters**:
- `action` (string, required): "search" or "host"
- `query` (string, required for search): Search query
- `ip` (string, required for host): IP address to lookup

**Examples**:

```python
from app.invoke import invoke_tool

# Search for Apache servers
result = invoke_tool('shodan', {
    'action': 'search',
    'query': 'apache'
})

# Lookup host information
result = invoke_tool('shodan', {
    'action': 'host',
    'ip': '8.8.8.8'
})
```

**Caching**:
- Search results: 900 seconds (15 minutes)
- Host details: 3600 seconds (1 hour)

### Gradio Connectors

**Tool Name**: `gradio_<normalized_url>`

**Auto-Discovery**: Gradio connectors are automatically registered for URLs in `OSINT_CONNECTOR_ALLOWLIST`

**Parameters**:
- `endpoint` (string, required): Gradio endpoint path
- `inputs` (object, optional): Input parameters

**Example**:

```python
from app.invoke import invoke_tool

# Assuming https://my-gradio-app.example is in allowlist
result = invoke_tool('gradio_https___my_gradio_app_example', {
    'endpoint': '/api/predict',
    'inputs': {'text': 'Hello world'}
})
```

## API Reference

### Core Classes

#### ToolDefinition

```python
from app.tools.base import ToolDefinition

definition = ToolDefinition(
    name="my_tool",
    description="My custom tool",
    parameters={
        "param1": {
            "type": "string",
            "description": "Parameter description",
            "required": True
        }
    },
    streamable=False,
    requires_auth=False,
    category="custom"
)
```

#### OsintTool

```python
from app.tools.base import OsintTool, ToolDefinition

class MyTool(OsintTool):
    def invoke(self, params):
        # Implementation
        return self._normalize_output(
            text="Result summary",
            data={"key": "value"},
            meta={"source": "my_tool"}
        )
    
    def definition(self):
        return ToolDefinition(
            name="my_tool",
            description="My tool description",
            parameters={}
        )
```

### Registry Functions

```python
from app.tools.registry import (
    register_tool,
    unregister_tool,
    get_tool,
    list_tools,
    get_tools_metadata
)

# Register a tool
my_tool = MyTool()
register_tool("my_tool", my_tool)

# List all tools
tools = list_tools()  # Returns: ['shodan', 'my_tool', ...]

# Get tool metadata
metadata = get_tools_metadata()

# Get specific tool
tool = get_tool("my_tool")

# Unregister tool
unregister_tool("my_tool")
```

### Invoke Helper

```python
from app.invoke import invoke_tool

# Invoke any registered tool
result = invoke_tool("tool_name", {"param": "value"})

# Result structure:
# {
#   "text": "Human-readable summary",
#   "data": {...},  # Structured data
#   "meta": {...}   # Metadata (source, timing, etc.)
# }
```

### Caching

```python
from app.cache import get_cache

cache = get_cache()

# Set value with TTL
cache.set("key", {"data": "value"}, ttl=3600)

# Get value
value = cache.get("key")

# Delete value
cache.delete("key")

# Use decorator
@cache.cache_result("prefix", ttl=900)
def expensive_operation(param):
    return {"result": param}
```

## Security Considerations

### API Keys

**Never hardcode API keys**. Always use environment variables:

```bash
export SHODAN_API_KEY=your_key_here
```

### Allowlist Enforcement

The `OSINT_CONNECTOR_ALLOWLIST` prevents open proxy behavior:

```bash
# Only these URLs can be proxied
export OSINT_CONNECTOR_ALLOWLIST="https://trusted-app1.com,https://trusted-app2.com"
```

If `OSINT_CONNECTOR_ALLOWLIST` is empty or unset, no Gradio/external connectors will be registered.

### Timeout Configuration

All external HTTP requests have conservative timeouts:
- OpenAPI spec discovery: 8 seconds
- Tool invocations: 20-60 seconds (depending on operation)

### Logging

All exceptions are logged safely without exposing secrets:
- API keys are never included in logs
- Only error types and sanitized messages are logged

## Troubleshooting

### Redis Connection Issues

If Redis is unavailable, caching is automatically disabled:

```
Redis cache unavailable: Connection refused. Caching disabled.
```

Tools will continue to work without caching.

### Shodan API Key Missing

If `SHODAN_API_KEY` is not set:

```python
result = invoke_tool('shodan', {'action': 'search', 'query': 'test'})
# Returns: {"text": "Shodan API key not configured", ...}
```

### Allowlist Issues

If a URL is not in `OSINT_CONNECTOR_ALLOWLIST`:

```
Base URL not in allowlist: https://untrusted-app.com
```

Add the URL to the allowlist or use a different connector.

## Advanced Usage

### Creating Custom Connectors

```python
from app.tools.base import OsintTool, ToolDefinition
from app.cache import get_cache

class CustomConnector(OsintTool):
    def __init__(self):
        self.cache = get_cache()
    
    def invoke(self, params):
        # Check cache
        cache_key = f"custom:{params.get('query')}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        # Perform operation
        result = self._normalize_output(
            text=f"Custom result for {params.get('query')}",
            data={"custom": True},
            meta={"source": "custom"}
        )
        
        # Cache result
        self.cache.set(cache_key, result, ttl=3600)
        return result
    
    def definition(self):
        return ToolDefinition(
            name="custom",
            description="Custom connector",
            parameters={
                "query": {
                    "type": "string",
                    "description": "Query parameter",
                    "required": True
                }
            }
        )

# Register the tool
from app.tools.registry import register_tool
register_tool("custom", CustomConnector())
```

### Using ConnectorManager Directly

```python
from app.tools.connector import ConnectorManager

manager = ConnectorManager()

# Discover OpenAPI spec
spec = manager.fetch_openapi("https://api.example.com")

# Synthesize tools from spec
tools = manager.synthesize_tools("https://api.example.com", spec)

# Proxy an invocation
result = manager.proxy_invoke(
    base_url="https://api.example.com",
    path="/api/endpoint",
    method="POST",
    params={"key": "value"},
    timeout=30
)
```

## Testing

Run the test suite:

```bash
# All tests
pytest tests/

# Just registry tests
pytest tests/test_tools_registry.py -v

# With coverage
pytest --cov=app tests/
```

## Next Steps

1. **Add More Connectors**: Implement connectors for VirusTotal, Censys, etc.
2. **Async Support**: Add async variants using httpx and aioredis
3. **Rate Limiting**: Implement Flask-Limiter on invocation endpoints
4. **Monitoring**: Add Sentry or similar for production error tracking
5. **CI/CD**: Set up automated testing and deployment workflows
