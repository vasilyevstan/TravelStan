"""Search orchestration: plan dates, call the synthetic provider, build rows.

Nothing is stored, cached, or logged; failures are redacted into one generic
message.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from .domain import Offer, SearchQuery
from .planner import plan_date_options
from .providers import get_provider
from .results import build_results

GENERIC_FAILURE = "Demo search is unavailable right now. Please try again."


@dataclass(frozen=True, slots=True)
class SearchOutcome:
    offers: tuple[Offer, ...]
    retrieved_at: dt.datetime
    expires_at: dt.datetime | None
    source: str


class SearchUnavailable(Exception):
    """Raised with a generic, redacted message only."""


def run_search(query: SearchQuery, today: dt.date, now: dt.datetime) -> SearchOutcome:
    provider = get_provider()
    options = plan_date_options(query, today)
    try:
        raw_offers = provider.search(query, options, now)
    except Exception as exc:  # noqa: BLE001 - details are intentionally dropped
        raise SearchUnavailable(GENERIC_FAILURE) from exc
    offers = build_results(raw_offers, query)
    return SearchOutcome(
        offers=offers,
        retrieved_at=now,
        expires_at=offers[0].expires_at if offers else None,
        source=provider.name,
    )
