"""
Circuit Breaker pattern.
Stops calling a failing operation after N consecutive failures,
then allows a retry after a recovery timeout.
"""
import logging
import time
import threading
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """
    Thread-safe circuit breaker for protecting external service calls.

    Args:
        name: Identifier for this breaker (used in logs).
        failure_threshold: Consecutive failures before opening.
        recovery_timeout: Seconds to wait before trying half-open.
        fallback: Optional callable invoked when circuit is open.
    """

    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 3,
        recovery_timeout: float = 60.0,
        fallback: Optional[Callable] = None,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.fallback = fallback

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._total_calls = 0
        self._total_failures = 0
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    @property
    def stats(self) -> dict:
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "total_calls": self._total_calls,
            "total_failures": self._total_failures,
            "failure_threshold": self.failure_threshold,
        }

    def _try_half_open(self):
        """Transition to HALF_OPEN if recovery timeout has elapsed."""
        if self._state == CircuitState.OPEN:
            elapsed = time.time() - self._last_failure_time
            if elapsed >= self.recovery_timeout:
                logger.info(
                    "Circuit '%s' recovery timeout elapsed (%.1fs), "
                    "transitioning to HALF_OPEN",
                    self.name, elapsed,
                )
                self._state = CircuitState.HALF_OPEN

    def call(self, func: Callable, *args, **kwargs):
        """
        Execute `func` through the circuit breaker.

        - CLOSED: execute normally; increment failure count on exception.
        - OPEN: skip execution; call fallback if provided; raise CircuitBreakerOpenError.
        - HALF_OPEN: allow one call; success -> CLOSED, failure -> OPEN.
        """
        with self._lock:
            self._try_half_open()

            if self._state == CircuitState.OPEN:
                self._total_calls += 1
                if self.fallback:
                    return self.fallback(*args, **kwargs)
                raise CircuitBreakerOpenError(
                    f"Circuit '{self.name}' is OPEN. "
                    f"Retry in {self.recovery_timeout - (time.time() - self._last_failure_time):.0f}s"
                )

            was_half_open = self._state == CircuitState.HALF_OPEN

        try:
            result = func(*args, **kwargs)
        except Exception as e:
            with self._lock:
                self._total_calls += 1
                self._total_failures += 1
                self._failure_count += 1
                self._last_failure_time = time.time()
                if self._failure_count >= self.failure_threshold:
                    self._state = CircuitState.OPEN
                    logger.warning(
                        "Circuit '%s' OPEN after %d failures: %s",
                        self.name, self._failure_count, e,
                    )
                if was_half_open:
                    logger.info(
                        "Circuit '%s' HALF_OPEN call failed -> OPEN", self.name
                    )
                    self._state = CircuitState.OPEN
            raise e
        else:
            with self._lock:
                self._total_calls += 1
                if was_half_open:
                    logger.info(
                        "Circuit '%s' HALF_OPEN call succeeded -> CLOSED", self.name
                    )
                    self._state = CircuitState.CLOSED
                self._failure_count = 0
            return result

    def reset(self):
        """Manually reset breaker to CLOSED state."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            logger.info("Circuit '%s' manually reset to CLOSED", self.name)


class CircuitBreakerOpenError(Exception):
    """Raised when a call is blocked by an open circuit."""
    pass
