"""Shared deterministic test helpers; no network, no credentials."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from flights.domain import (
    SOURCE_SYNTHETIC_DEMO,
    BaggageAllowance,
    BaggageAllowances,
    BaggageSlot,
    BaggageState,
    CabinClass,
    Itinerary,
    LuggageChoice,
    Offer,
    SearchMode,
    SearchQuery,
    Segment,
)

TODAY = dt.date(2026, 9, 19)
NOW = dt.datetime(2026, 9, 19, 12, 0, tzinfo=dt.UTC)


def make_query(**overrides: object) -> SearchQuery:
    data: dict[str, object] = {
        "origin": "AAA",
        "destination": "BBB",
        "departure_date": dt.date(2026, 10, 1),
        "return_date": None,
        "cabin": CabinClass.ALL_CLASSES,
        "mode": SearchMode.EXACT,
        "flexibility": 0,
        "luggage": LuggageChoice.NO_CHECKED_REQUIREMENT,
    }
    data.update(overrides)
    return SearchQuery(**data)  # type: ignore[arg-type]


def make_baggage(
    checked_state: BaggageState = BaggageState.INCLUDED,
    checked_quantity: int | None = 1,
) -> BaggageAllowances:
    return BaggageAllowances(
        personal_item=BaggageAllowance(
            BaggageSlot.PERSONAL_ITEM, BaggageState.INCLUDED, 1
        ),
        carry_on=BaggageAllowance(BaggageSlot.CARRY_ON, BaggageState.UNKNOWN),
        checked_bag=BaggageAllowance(
            BaggageSlot.CHECKED_BAG, checked_state, checked_quantity
        ),
        extra_paid_bag=BaggageAllowance(
            BaggageSlot.EXTRA_PAID_BAG, BaggageState.UNKNOWN
        ),
    )


def make_itinerary(
    origin: str = "AAA",
    destination: str = "BBB",
    departure: dt.datetime | None = None,
    minutes: int = 120,
    flight_number: str = "ZQ1001",
) -> Itinerary:
    start = departure or dt.datetime(2026, 10, 1, 8, 0, tzinfo=dt.UTC)
    return Itinerary(
        segments=(
            Segment(
                marketing_carrier="ZQ",
                marketing_carrier_name="Demo Air Zephyr (fictional)",
                operating_carrier="ZQ",
                operating_carrier_name="Demo Air Zephyr (fictional)",
                flight_number=flight_number,
                origin=origin,
                destination=destination,
                departure=start,
                arrival=start + dt.timedelta(minutes=minutes),
                duration_minutes=minutes,
            ),
        )
    )


def make_offer(
    offer_id: str = "demo-1",
    amount: str = "100.00",
    currency: str = "EUR",
    minutes: int = 120,
    baggage: BaggageAllowances | None = None,
    inbound: Itinerary | None = None,
    flight_number: str = "ZQ1001",
) -> Offer:
    return Offer(
        offer_id=offer_id,
        outbound=make_itinerary(minutes=minutes, flight_number=flight_number),
        inbound=inbound,
        cabin=CabinClass.ECONOMY,
        fare_brand="Demo Basic",
        total_amount=Decimal(amount),
        currency=currency,
        baggage=baggage or make_baggage(),
        source=SOURCE_SYNTHETIC_DEMO,
        retrieved_at=NOW,
        expires_at=NOW + dt.timedelta(minutes=30),
    )
