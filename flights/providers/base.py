"""Normalized provider protocol and redacted provider outcomes."""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ..domain import DataStatus, DateOption, Offer, SearchQuery


class ProviderError(Exception):
    """Internal provider failure; surfaced to users only as a generic error."""


class ProviderConfigurationError(ProviderError):
    """A selected provider is missing safe, usable configuration."""


@dataclass(frozen=True, slots=True)
class ProviderNotice:
    source: str
    message: str


@dataclass(frozen=True, slots=True)
class ProviderSearchResult:
    offers: tuple[Offer, ...]
    notices: tuple[ProviderNotice, ...] = ()
    requests_made: int = 1


@runtime_checkable
class FlightProvider(Protocol):
    name: str
    display_name: str
    data_status: DataStatus
    request_cost: int

    def search(
        self,
        query: SearchQuery,
        options: Sequence[DateOption],
        now: dt.datetime,
    ) -> ProviderSearchResult: ...
