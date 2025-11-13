"""Rate limiting and throttling utilities."""
import asyncio
import logging
import time
from collections import defaultdict

from ..config import config
from .errors import RateLimitError

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter for API calls."""

    def __init__(self, rate_per_minute: int | None = None):
        """
        Initialize rate limiter.
        
        Args:
            rate_per_minute: Maximum requests per minute (defaults to config value)
        """
        self.rate_per_minute = rate_per_minute or config.ethical_guardrails.rate_limit_per_minute
        self.requests: defaultdict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def acquire(self, key: str = "default") -> None:
        """
        Acquire permission to make a request.
        
        Args:
            key: Identifier for the rate limit bucket (e.g., API endpoint or domain)
            
        Raises:
            RateLimitError: If rate limit would be exceeded
        """
        async with self._lock:
            current_time = time.time()
            cutoff_time = current_time - 60  # 1 minute ago

            # Remove old requests
            self.requests[key] = [
                req_time for req_time in self.requests[key]
                if req_time > cutoff_time
            ]

            # Check if we're at the limit
            if len(self.requests[key]) >= self.rate_per_minute:
                oldest_request = self.requests[key][0]
                wait_time = 60 - (current_time - oldest_request)

                logger.warning(
                    f"Rate limit reached for '{key}'. "
                    f"Would need to wait {wait_time:.1f}s"
                )

                raise RateLimitError(
                    f"Rate limit exceeded for '{key}'. Try again later.",
                    details={
                        "key": key,
                        "limit": self.rate_per_minute,
                        "wait_seconds": wait_time,
                    }
                )

            # Record this request
            self.requests[key].append(current_time)
            logger.debug(
                f"Rate limiter: {len(self.requests[key])}/{self.rate_per_minute} "
                f"requests used for '{key}'"
            )

    def get_remaining(self, key: str = "default") -> int:
        """
        Get remaining requests available in current window.
        
        Args:
            key: Identifier for the rate limit bucket
            
        Returns:
            Number of requests remaining
        """
        current_time = time.time()
        cutoff_time = current_time - 60

        recent_requests = [
            req_time for req_time in self.requests.get(key, [])
            if req_time > cutoff_time
        ]

        return max(0, self.rate_per_minute - len(recent_requests))


# Global rate limiter instance
rate_limiter = RateLimiter()
