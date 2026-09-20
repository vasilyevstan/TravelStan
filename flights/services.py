"""Search orchestration across configured providers."""

from __future__ import annotations

import datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from .domain import Offer, SearchQuery
from .planner import plan_date_options
from .providers import ProviderNotice, get_providers
from .providers.base import FlightProvider, ProviderSearchResult
from .results import build_results

GENERIC_FAILURE = "Flight search is unavailable right now. Please try again."


@dataclass(frozen=True, slots=True)
class SearchOutcome:
    offers: tuple[Offer, ...]
    retrieved_at: dt.datetime
    expires_at: dt.datetime | None
    sources: tuple[str, ...]
    notices: tuple[ProviderNotice, ...]
    requests_made: int

    @property
    def source(self) -> str:
        return ", ".join(self.sources)


class SearchUnavailable(Exception):
    """Raised with a generic, redacted message only."""


def run_search(query: SearchQuery, today: dt.date, now: dt.datetime) -> SearchOutcome:
    try:
        providers = get_providers()
    except Exception as exc:  # noqa: BLE001 - details are intentionally dropped
        raise SearchUnavailable(GENERIC_FAILURE) from exc
    options = plan_date_options(query, today)
    completed: dict[str, ProviderSearchResult] = {}
    failed: set[str] = set()

    def invoke(provider: FlightProvider) -> ProviderSearchResult:
        return provider.search(query, options, now)

    if len(providers) == 1:
        provider = providers[0]
        try:
            completed[provider.name] = invoke(provider)
        except Exception as exc:  # noqa: BLE001 - details are intentionally dropped
            raise SearchUnavailable(GENERIC_FAILURE) from exc
    else:
        with ThreadPoolExecutor(max_workers=len(providers)) as executor:
            futures = {
                executor.submit(invoke, provider): provider for provider in providers
            }
            for future in as_completed(futures):
                provider = futures[future]
                try:
                    completed[provider.name] = future.result()
                except Exception:  # noqa: BLE001 - details are intentionally dropped
                    failed.add(provider.name)
    if not completed:
        raise SearchUnavailable(GENERIC_FAILURE)

    raw_offers: list[Offer] = []
    notices: list[ProviderNotice] = []
    requests_made = sum(provider.request_cost for provider in providers)
    sources: list[str] = []
    for provider in providers:
        result = completed.get(provider.name)
        if result is not None:
            sources.append(provider.name)
            raw_offers.extend(result.offers)
            notices.extend(result.notices)
        elif provider.name in failed:
            notices.append(
                ProviderNotice(
                    provider.name,
                    f"{provider.display_name} is temporarily unavailable.",
                )
            )
    offers = build_results(raw_offers, query)
    return SearchOutcome(
        offers=offers,
        retrieved_at=now,
        expires_at=min((offer.expires_at for offer in offers), default=None),
        sources=tuple(sources),
        notices=tuple(notices),
        requests_made=requests_made,
    )
