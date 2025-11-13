# Contributing to OSINT MCP Server

Thank you for your interest in contributing to the OSINT MCP Server! This document provides guidelines and instructions for contributing.

## Code of Conduct

### Our Pledge

We are committed to making participation in this project a harassment-free experience for everyone, regardless of level of experience, gender, gender identity and expression, sexual orientation, disability, personal appearance, body size, race, ethnicity, age, religion, or nationality.

### Our Standards

Examples of behavior that contributes to creating a positive environment:
- Using welcoming and inclusive language
- Being respectful of differing viewpoints
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

### Ethical Requirements

All contributions must:
- Respect privacy and legal boundaries
- Not enable illegal activities
- Not bypass security measures
- Follow ethical OSINT principles
- Include appropriate ethical guardrails

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- Basic understanding of OSINT principles
- Commitment to ethical practices

### Development Setup

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/OSINT-MCP-Server.git
   cd OSINT-MCP-Server
   ```

3. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

4. Create a branch for your feature:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Workflow

### Before Making Changes

1. Check existing issues and PRs to avoid duplicates
2. Create an issue to discuss major changes
3. Ensure your change aligns with the project's ethical guidelines

### Making Changes

1. **Write Clean Code**
   - Follow PEP 8 style guidelines
   - Use type hints
   - Write descriptive docstrings
   - Keep functions focused and small

2. **Add Tests**
   - Write tests for new features
   - Ensure existing tests pass
   - Aim for high code coverage

3. **Update Documentation**
   - Update README.md if needed
   - Update EXAMPLES.md for new tools
   - Add docstrings to all functions

### Code Style

We use the following tools:

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/
```

Run before committing:
```bash
# Format
black src/ tests/

# Check for issues
ruff check src/ tests/ --fix

# Run tests
pytest
```

### Writing Tests

Tests should:
- Be in the `tests/` directory
- Use pytest framework
- Test both success and failure cases
- Use descriptive test names

Example:
```python
def test_validate_domain_success():
    """Test domain validation with valid input."""
    result = validate_domain("example.com")
    assert result == "example.com"

def test_validate_domain_invalid():
    """Test domain validation with invalid input."""
    with pytest.raises(InvalidInputError):
        validate_domain("not_a_domain")
```

### Committing Changes

1. **Commit Messages**
   - Use clear, descriptive commit messages
   - Start with a verb (Add, Fix, Update, Remove)
   - Reference issues when applicable

   Example:
   ```
   Add email validation function

   - Implements email format validation
   - Adds tests for valid and invalid emails
   - Updates documentation

   Fixes #123
   ```

2. **Sign Your Commits**
   ```bash
   git commit -s -m "Your commit message"
   ```

## Adding New Features

### New OSINT Tools

When adding a new OSINT tool:

1. **Create the tool function** in appropriate module:
   ```python
   async def my_osint_tool(param: str) -> dict[str, Any]:
       """
       Tool description.
       
       Args:
           param: Parameter description
           
       Returns:
           Dictionary with results
       """
       try:
           # Validate input
           param = validate_input(param)
           
           # Apply rate limiting
           await rate_limiter.acquire(f"tool:{param}")
           
           # Perform operation
           result = await do_operation(param)
           
           return {
               "success": True,
               "data": result
           }
       except Exception as e:
           return handle_error(e, f"Tool operation for {param}")
   ```

2. **Add to server.py** in `list_tools()` and `call_tool()`

3. **Write tests** in `tests/test_tools.py`

4. **Add example** to EXAMPLES.md

5. **Ensure ethical compliance**:
   - Add rate limiting
   - Validate inputs
   - Respect robots.txt (if web-based)
   - Handle errors gracefully

### New Utilities

When adding utilities:

1. Place in appropriate `utils/` module
2. Write comprehensive tests
3. Add to `utils/__init__.py` exports
4. Document with clear docstrings

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=osint_mcp --cov-report=html

# Run specific test file
pytest tests/test_validators.py

# Run specific test
pytest tests/test_validators.py::test_validate_domain
```

### Test Coverage

- Aim for >80% code coverage
- Test edge cases and error conditions
- Include async tests for async functions

## Documentation

### Docstring Format

Use Google-style docstrings:

```python
def function_name(param1: str, param2: int = 10) -> dict[str, Any]:
    """
    Brief description of function.
    
    Longer description if needed. Explain what the function does,
    why it exists, and any important details.
    
    Args:
        param1: Description of param1
        param2: Description of param2 (default: 10)
        
    Returns:
        Dictionary containing:
            - key1: Description
            - key2: Description
            
    Raises:
        ValueError: When something goes wrong
        TypeError: When type is incorrect
        
    Example:
        >>> result = function_name("test", 20)
        >>> print(result)
        {'key1': 'value'}
    """
```

### README Updates

Update README.md when:
- Adding new features
- Changing configuration options
- Modifying installation steps
- Adding new dependencies

## Pull Request Process

1. **Before Submitting**
   - Ensure all tests pass
   - Run code formatters and linters
   - Update documentation
   - Rebase on latest main branch

2. **PR Description**
   Include:
   - What changes were made
   - Why the changes were necessary
   - How to test the changes
   - Screenshots (if UI changes)
   - Related issues

   Template:
   ```markdown
   ## Description
   Brief description of changes

   ## Changes Made
   - Change 1
   - Change 2

   ## Testing
   How to test these changes

   ## Checklist
   - [ ] Tests pass
   - [ ] Code formatted
   - [ ] Documentation updated
   - [ ] Ethical guidelines followed
   ```

3. **Review Process**
   - Maintainers will review your PR
   - Address feedback promptly
   - Be open to suggestions
   - Make requested changes

4. **After Merge**
   - Delete your feature branch
   - Pull latest changes
   - Celebrate! 🎉

## Reporting Issues

### Bug Reports

Include:
- Python version
- OS and version
- Steps to reproduce
- Expected behavior
- Actual behavior
- Error messages/logs

Template:
```markdown
**Python Version:** 3.10.5
**OS:** Ubuntu 22.04

**Steps to Reproduce:**
1. Run command X
2. Provide input Y
3. See error

**Expected:** Should return result Z
**Actual:** Error message...

**Logs:**
```
[paste logs]
```
```

### Feature Requests

Include:
- Use case description
- Why this feature is needed
- How it should work
- Ethical considerations

## Ethical Guidelines for Contributors

### Do's ✅

- Respect privacy and legal boundaries
- Include rate limiting for network requests
- Validate and sanitize inputs
- Handle errors gracefully
- Document security implications
- Test with public data only
- Follow robots.txt rules
- Use clear user agent strings

### Don'ts ❌

- Add features that bypass security
- Access private/internal networks
- Include credential stealing capabilities
- Add features for malicious purposes
- Ignore rate limiting
- Hard-code sensitive data
- Add features without ethical review

### Review Criteria

All contributions are reviewed for:
1. **Functionality** - Does it work correctly?
2. **Code Quality** - Is it well-written and tested?
3. **Security** - Does it introduce vulnerabilities?
4. **Ethics** - Does it follow ethical OSINT principles?
5. **Documentation** - Is it well-documented?

## Questions?

- Open an issue for questions
- Tag maintainers if urgent
- Be patient and respectful

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Acknowledgments

Thank you for helping make OSINT MCP Server better! Your contributions are valued and appreciated.
