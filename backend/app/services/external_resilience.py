from __future__ import annotations

from dataclasses import dataclass
import logging
import random
import socket
import threading
import time
from urllib import error as urllib_error

from app.settings import settings


logger = logging.getLogger(__name__)


class CircuitOpenError(RuntimeError):
    pass


@dataclass
class CircuitState:
    failures: int = 0
    opened_at: float | None = None


class ProviderCircuitBreaker:
    def __init__(self) -> None:
        self._states: dict[str, CircuitState] = {}
        self._lock = threading.Lock()

    def before_call(self, provider: str) -> None:
        with self._lock:
            state = self._states.setdefault(provider, CircuitState())
            if state.opened_at is None:
                return
            if time.monotonic() - state.opened_at >= settings.external_circuit_reset_seconds:
                state.failures = 0
                state.opened_at = None
                return
            raise CircuitOpenError(f"{provider} is temporarily unavailable")

    def success(self, provider: str) -> None:
        with self._lock:
            self._states[provider] = CircuitState()

    def failure(self, provider: str) -> None:
        with self._lock:
            state = self._states.setdefault(provider, CircuitState())
            state.failures += 1
            if state.failures >= settings.external_circuit_failure_threshold:
                state.opened_at = time.monotonic()


provider_circuits = ProviderCircuitBreaker()


def is_retryable_exception(exc: Exception) -> bool:
    if isinstance(exc, urllib_error.HTTPError):
        return exc.code in {408, 425, 429, 500, 502, 503, 504}
    return isinstance(exc, (urllib_error.URLError, TimeoutError, socket.timeout, ConnectionError))


def safe_provider_error(exc: Exception) -> str:
    if isinstance(exc, CircuitOpenError):
        return "provider_circuit_open"
    if isinstance(exc, urllib_error.HTTPError):
        return f"provider_http_{exc.code}"
    if isinstance(exc, (urllib_error.URLError, TimeoutError, socket.timeout, ConnectionError)):
        return "provider_unavailable"
    return type(exc).__name__


def external_call(provider: str, operation: str, action, *, retry_safe: bool = False):
    """Execute an external call without ever logging request URLs, payloads, or credentials."""
    attempts = max(1, settings.external_safe_retry_attempts if retry_safe else 1)
    provider_circuits.before_call(provider)
    for attempt in range(1, attempts + 1):
        try:
            result = action()
            provider_circuits.success(provider)
            return result
        except Exception as exc:
            retryable = retry_safe and is_retryable_exception(exc) and attempt < attempts
            logger.warning(
                "external_provider_failure provider=%s operation=%s category=%s attempt=%s retry=%s",
                provider,
                operation,
                safe_provider_error(exc),
                attempt,
                retryable,
            )
            if not retryable:
                provider_circuits.failure(provider)
                raise
            base = max(1, settings.external_retry_base_ms) / 1000
            delay = base * (2 ** (attempt - 1)) + random.uniform(0, base)
            time.sleep(delay)


def external_timeout_seconds() -> int:
    return max(settings.external_connect_timeout_seconds, settings.external_response_timeout_seconds)
