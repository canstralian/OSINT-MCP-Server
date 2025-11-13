"""Error handling utilities for OSINT MCP Server."""
import logging
from typing import Any

logger = logging.getLogger(__name__)


class OSINTError(Exception):
    """Base exception for OSINT MCP Server."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class RateLimitError(OSINTError):
    """Raised when rate limit is exceeded."""
    pass


class EthicalViolationError(OSINTError):
    """Raised when an operation violates ethical guardrails."""
    pass


class InvalidInputError(OSINTError):
    """Raised when input validation fails."""
    pass


class NetworkError(OSINTError):
    """Raised when network operations fail."""
    pass


class DataNotFoundError(OSINTError):
    """Raised when requested data is not available."""
    pass


def handle_error(error: Exception, context: str = "") -> dict[str, Any]:
    """
    Handle and format errors consistently.
    
    Args:
        error: The exception that occurred
        context: Additional context about where the error occurred
        
    Returns:
        Formatted error dictionary
    """
    error_msg = f"{context}: {str(error)}" if context else str(error)

    if isinstance(error, OSINTError):
        logger.warning(f"OSINT Error - {error_msg}", extra=error.details)
        return {
            "success": False,
            "error": error.message,
            "error_type": error.__class__.__name__,
            "details": error.details,
        }
    else:
        logger.error(f"Unexpected error - {error_msg}", exc_info=True)
        return {
            "success": False,
            "error": str(error),
            "error_type": type(error).__name__,
        }


def validate_result(result: Any, expected_fields: list[str] | None = None) -> bool:
    """
    Validate that a result has expected structure.
    
    Args:
        result: The result to validate
        expected_fields: List of required fields
        
    Returns:
        True if validation passes
        
    Raises:
        InvalidInputError: If validation fails
    """
    if result is None:
        raise InvalidInputError("Result is None")

    if expected_fields and isinstance(result, dict):
        missing = [field for field in expected_fields if field not in result]
        if missing:
            raise InvalidInputError(
                f"Missing required fields: {', '.join(missing)}"
            )

    return True
