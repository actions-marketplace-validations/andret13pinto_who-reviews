from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from who_reviews.http_retry import RetryTransport


class _FakeTransport(httpx.BaseTransport):
    def __init__(self, responses: list[httpx.Response]) -> None:
        self._responses = list(responses)
        self.request_count = 0

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.request_count += 1
        return self._responses.pop(0)


class _ErrorThenSuccessTransport(httpx.BaseTransport):
    def __init__(self, error_count: int) -> None:
        self._error_count = error_count
        self.request_count = 0

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.request_count += 1
        if self.request_count <= self._error_count:
            raise httpx.ConnectError("connection refused")
        return httpx.Response(200, json={"ok": True})


@pytest.fixture()
def http_request() -> httpx.Request:
    return httpx.Request("GET", "https://api.github.com/test")


@pytest.mark.parametrize("status_code", [502, 503, 504])
def test_retries_transient_server_errors(
    http_request: httpx.Request, status_code: int
) -> None:
    inner = _FakeTransport(
        [
            httpx.Response(status_code),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    transport = RetryTransport(inner, max_retries=3, backoff_base=0.0)

    response = transport.handle_request(http_request)

    assert response.status_code == 200
    assert inner.request_count == 2


def test_retries_429_with_retry_after_header(request: httpx.Request) -> None:
    inner = _FakeTransport(
        [
            httpx.Response(429, headers={"Retry-After": "0"}),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    transport = RetryTransport(inner, max_retries=3, backoff_base=0.0)

    response = transport.handle_request(http_request)

    assert response.status_code == 200
    assert inner.request_count == 2


def test_retries_403_rate_limit(request: httpx.Request) -> None:
    inner = _FakeTransport(
        [
            httpx.Response(
                403,
                headers={
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": "0",
                },
            ),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    transport = RetryTransport(inner, max_retries=3, backoff_base=0.0)

    with patch("who_reviews.http_retry.time") as mock_time:
        mock_time.time.return_value = 0.0
        response = transport.handle_request(http_request)

    assert response.status_code == 200
    assert inner.request_count == 2


@pytest.mark.parametrize("status_code", [400, 401, 404, 422])
def test_non_retryable_passes_through(
    http_request: httpx.Request, status_code: int
) -> None:
    inner = _FakeTransport([httpx.Response(status_code)])
    transport = RetryTransport(inner, max_retries=3, backoff_base=0.0)

    response = transport.handle_request(http_request)

    assert response.status_code == status_code
    assert inner.request_count == 1


def test_403_without_rate_limit_headers_not_retried(
    http_request: httpx.Request,
) -> None:
    inner = _FakeTransport([httpx.Response(403)])
    transport = RetryTransport(inner, max_retries=3, backoff_base=0.0)

    response = transport.handle_request(http_request)

    assert response.status_code == 403
    assert inner.request_count == 1


def test_max_retries_exhausted_returns_last_response(
    http_request: httpx.Request,
) -> None:
    inner = _FakeTransport(
        [
            httpx.Response(502),
            httpx.Response(503),
            httpx.Response(504),
            httpx.Response(502),
        ]
    )
    transport = RetryTransport(inner, max_retries=3, backoff_base=0.0)

    response = transport.handle_request(http_request)

    assert response.status_code == 502
    assert inner.request_count == 4  # 1 initial + 3 retries


def test_retries_network_errors(request: httpx.Request) -> None:
    inner = _ErrorThenSuccessTransport(error_count=2)
    transport = RetryTransport(inner, max_retries=3, backoff_base=0.0)

    response = transport.handle_request(http_request)

    assert response.status_code == 200
    assert inner.request_count == 3


def test_network_error_exhausted_raises(request: httpx.Request) -> None:
    inner = _ErrorThenSuccessTransport(error_count=10)
    transport = RetryTransport(inner, max_retries=2, backoff_base=0.0)

    with pytest.raises(httpx.ConnectError):
        transport.handle_request(http_request)


def test_retry_after_header_is_respected(request: httpx.Request) -> None:
    inner = _FakeTransport(
        [
            httpx.Response(429, headers={"Retry-After": "5"}),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    transport = RetryTransport(inner, max_retries=3, backoff_base=0.0)

    with patch("tenacity.nap.time") as mock_sleep:
        response = transport.handle_request(http_request)
        if mock_sleep.sleep.called:
            wait_time = mock_sleep.sleep.call_args[0][0]
            assert wait_time == pytest.approx(5.0, abs=0.1)

    assert response.status_code == 200
