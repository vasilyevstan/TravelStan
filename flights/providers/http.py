"""Small HTTP boundary shared by live providers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from .base import ProviderError

REQUEST_TIMEOUT = httpx.Timeout(8.0, connect=4.0)
MAX_RESPONSE_BYTES = 5 * 1024 * 1024


def request_json(
    method: str,
    url: str,
    *,
    headers: Mapping[str, str],
    params: Mapping[str, object] | None = None,
    json: Mapping[str, object] | None = None,
    transport: httpx.BaseTransport | None = None,
) -> Mapping[str, Any]:
    """Make one request, with no retries, and return an object-shaped payload."""
    try:
        with httpx.Client(
            timeout=REQUEST_TIMEOUT,
            follow_redirects=False,
            transport=transport,
        ) as client:
            response = client.request(
                method,
                url,
                headers=dict(headers),
                params=params,
                json=json,
            )
            response.raise_for_status()
            if len(response.content) > MAX_RESPONSE_BYTES:
                raise ProviderError("Provider response exceeded the safe size limit.")
            payload = response.json()
    except ProviderError:
        raise
    except (httpx.HTTPError, ValueError):
        # HTTP exceptions can retain request URLs containing provider secrets.
        raise ProviderError("Provider request failed.") from None
    if not isinstance(payload, dict):
        raise ProviderError("Provider returned an unsupported response.")
    return payload
