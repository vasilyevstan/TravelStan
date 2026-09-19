"""Deterministic result assembly: baggage filter, dedupe, sort, row cap."""

from __future__ import annotations

from collections.abc import Iterable

from .domain import MAX_RESULT_ROWS, Offer, SearchQuery


def filter_by_luggage(offers: Iterable[Offer], query: SearchQuery) -> tuple[Offer, ...]:
    """Checked-required keeps only known positive included checked allowances.

    No checked requirement preserves every offer; missing data is never
    inferred into a decision.
    """
    if not query.requires_checked_bag:
        return tuple(offers)
    return tuple(
        offer
        for offer in offers
        if offer.baggage.checked_bag.has_known_positive_quantity
    )


def deduplicate(offers: Iterable[Offer]) -> tuple[Offer, ...]:
    """First-wins dedupe on the stable full-itinerary identity."""
    seen: set[object] = set()
    unique: list[Offer] = []
    for offer in offers:
        key = offer.identity()
        if key in seen:
            continue
        seen.add(key)
        unique.append(offer)
    return tuple(unique)


def sort_offers(offers: Iterable[Offer]) -> tuple[Offer, ...]:
    return tuple(sorted(offers, key=lambda offer: offer.sort_key()))


def build_results(offers: Iterable[Offer], query: SearchQuery) -> tuple[Offer, ...]:
    filtered = filter_by_luggage(offers, query)
    return sort_offers(deduplicate(filtered))[:MAX_RESULT_ROWS]
