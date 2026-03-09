"""Retry utilities for API calls."""

import asyncio
import functools
from typing import Callable, Type, Any
from dataclasses import dataclass

import httpx


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay_ms: int = 1000
    max_delay_ms: int = 30000
    rate_limit_delay_ms: int = 60000


class RetryExhaustedError(Exception):
    """Raised when all retry attempts are exhausted."""
    def __init__(self, message: str, last_error: Exception):
        super().__init__(message)
        self.last_error = last_error


class NotFoundError(Exception):
    """Raised when a resource is not found (404)."""
    pass


# Default retry config
DEFAULT_RETRY_CONFIG = RetryConfig()


def retry_async(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable_errors: tuple[Type[Exception], ...] = (
        httpx.TimeoutException,
        httpx.NetworkError,
    ),
    on_retry: Callable[[int, float, Exception], None] | None = None,
):
    """
    Decorator for async functions with exponential backoff retry.

    Args:
        max_attempts: Maximum number of attempts
        base_delay: Base delay in seconds (exponential backoff)
        max_delay: Maximum delay in seconds
        retryable_errors: Tuple of exception types to retry
        on_retry: Optional callback(attempt, delay, error) called before retry
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_error = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_errors as e:
                    last_error = e
                    if attempt < max_attempts:
                        delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                        if on_retry:
                            on_retry(attempt, delay, e)
                        await asyncio.sleep(delay)
                    else:
                        raise RetryExhaustedError(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}",
                            e
                        )
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 404:
                        raise NotFoundError(f"Resource not found: {e.request.url}")
                    if e.response.status_code == 403:
                        # Rate limit - use longer delay
                        last_error = e
                        if attempt < max_attempts:
                            retry_after = e.response.headers.get("Retry-After")
                            delay = float(retry_after) if retry_after else 60.0
                            if on_retry:
                                on_retry(attempt, delay, e)
                            await asyncio.sleep(delay)
                        else:
                            raise RetryExhaustedError(
                                f"{func.__name__} rate limited after {max_attempts} attempts",
                                e
                            )
                    elif 500 <= e.response.status_code < 600:
                        # Server error - retry
                        last_error = e
                        if attempt < max_attempts:
                            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                            if on_retry:
                                on_retry(attempt, delay, e)
                            await asyncio.sleep(delay)
                        else:
                            raise RetryExhaustedError(
                                f"{func.__name__} failed after {max_attempts} attempts: {e}",
                                e
                            )
                    else:
                        # Other HTTP errors - don't retry
                        raise
            # Should not reach here, but just in case
            raise RetryExhaustedError(
                f"{func.__name__} failed unexpectedly",
                last_error or RuntimeError("Unknown error")
            )
        return wrapper
    return decorator
