from __future__ import annotations

import time
from collections.abc import Callable
from typing import cast

import httpx
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

_RETRYABLE_STATUS_CODES = frozenset({429, 502, 503, 504})


class _RetryableResponse(Exception):
    def __init__(self, response: httpx.Response) -> None:
        self.response = response


def _is_rate_limited(response: httpx.Response) -> bool:
    if response.status_code == 429:
        return True
    return (
        response.status_code == 403
        and response.headers.get("X-RateLimit-Remaining") == "0"
    )


def _is_retryable(response: httpx.Response) -> bool:
    return response.status_code in _RETRYABLE_STATUS_CODES or _is_rate_limited(response)


def _parse_retry_after(response: httpx.Response) -> float | None:
    retry_after = response.headers.get("Retry-After")
    if retry_after is not None:
        try:
            return float(retry_after)
        except ValueError:
            return None

    reset = response.headers.get("X-RateLimit-Reset")
    if reset is not None:
        try:
            wait = float(reset) - time.time()
            return max(wait, 0.0)
        except ValueError:
            return None

    return None


def _rate_limit_aware_wait(
    base_wait: float,
) -> Callable[[RetryCallState], float]:
    def _wait(retry_state: RetryCallState) -> float:
        exc = retry_state.outcome.exception() if retry_state.outcome else None
        if isinstance(exc, _RetryableResponse):
            server_wait = _parse_retry_after(exc.response)
            if server_wait is not None:
                return server_wait

        exp_wait = wait_exponential(multiplier=base_wait)
        return float(exp_wait(retry_state))

    return _wait


class RetryTransport(httpx.BaseTransport):
    def __init__(
        self,
        transport: httpx.BaseTransport | None = None,
        *,
        max_retries: int = 3,
        backoff_base: float = 1.0,
    ) -> None:
        self._transport = transport or httpx.HTTPTransport()
        self._max_retries = max_retries
        self._backoff_base = backoff_base

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        last_response: httpx.Response | None = None

        @retry(  # type: ignore[misc]
            retry=retry_if_exception_type((_RetryableResponse, httpx.TransportError)),
            stop=stop_after_attempt(self._max_retries + 1),
            wait=_rate_limit_aware_wait(self._backoff_base),
            reraise=True,
        )
        def _send() -> httpx.Response:
            nonlocal last_response
            response = self._transport.handle_request(request)
            if _is_retryable(response):
                last_response = response
                raise _RetryableResponse(response)
            return response

        try:
            return cast(httpx.Response, _send())
        except _RetryableResponse:
            assert last_response is not None
            return last_response

    def close(self) -> None:
        self._transport.close()
