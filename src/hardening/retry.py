import asyncio
import functools
import logging
import random
import time
from typing import Callable, Tuple, Type

logger = logging.getLogger(__name__)


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    jitter: float = 0.5,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """
    Decorator that retries a sync function with exponential backoff + jitter.

    Args:
        max_attempts: Max retry attempts (including the first try).
        delay: Base delay in seconds.
        backoff: Multiplier applied to delay after each attempt.
        jitter: Max random seconds added to delay (uniform).
        exceptions: Tuple of exception types that trigger a retry.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            current_delay = delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt < max_attempts:
                        sleep_time = current_delay + random.uniform(0, jitter)
                        logger.warning(
                            "%s attempt %d/%d failed: %s. Retrying in %.2fs...",
                            func.__name__, attempt, max_attempts, e, sleep_time,
                        )
                        time.sleep(sleep_time)
                        current_delay *= backoff
                    else:
                        logger.error(
                            "%s failed after %d attempts: %s",
                            func.__name__, max_attempts, e,
                        )
            raise last_exc
        return wrapper
    return decorator


def retry_async(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    jitter: float = 0.5,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """
    Decorator that retries an async function with exponential backoff + jitter.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exc = None
            current_delay = delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt < max_attempts:
                        sleep_time = current_delay + random.uniform(0, jitter)
                        logger.warning(
                            "%s attempt %d/%d failed: %s. Retrying in %.2fs...",
                            func.__name__, attempt, max_attempts, e, sleep_time,
                        )
                        await asyncio.sleep(sleep_time)
                        current_delay *= backoff
                    else:
                        logger.error(
                            "%s failed after %d attempts: %s",
                            func.__name__, max_attempts, e,
                        )
            raise last_exc
        return wrapper
    return decorator
