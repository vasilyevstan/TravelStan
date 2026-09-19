"""Normalized provider protocol.

A provider returns normalized `Offer` values only. Raw provider or fixture
payloads never leave a provider implementation.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from ..domain import DateOption, Offer, SearchQuery


class ProviderError(Exception):
    """Internal provider failure; surfaced to users only as a generic error."""


@runtime_checkable
class FlightProvider(Protocol):
    name: str

    def search(
        self,
        query: SearchQuery,
        options: Sequence[DateOption],
        now: dt.datetime,
    ) -> tuple[Offer, ...]: ...
