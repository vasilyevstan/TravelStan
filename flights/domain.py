"""Typed, frozen domain types for the synthetic-demo search slice.

Nothing here touches the database, the network, or any provider credential.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

SOURCE_SYNTHETIC_DEMO = "synthetic_demo"

IATA_PATTERN = r"^[A-Z]{3}$"

MAX_RESULT_ROWS = 10
MAX_DATE_OPTIONS = 15
MIN_FLEXIBILITY = 1
MAX_FLEXIBILITY = 7


class CabinClass(StrEnum):
    ECONOMY = "economy"
    PREMIUM_ECONOMY = "premium_economy"
    BUSINESS = "business"
    ALL_CLASSES = "all_classes"


class SearchMode(StrEnum):
    EXACT = "exact"
    FLEXIBLE = "flexible"


class LuggageChoice(StrEnum):
    """Explicit checked-luggage requirement; never a checkbox default."""

    CHECKED_REQUIRED = "checked_required"
    NO_CHECKED_REQUIREMENT = "no_checked_requirement"


class BaggageState(StrEnum):
    INCLUDED = "included"
    NOT_INCLUDED = "not_included"
    UNKNOWN = "unknown"


class BaggageSlot(StrEnum):
    PERSONAL_ITEM = "personal_item"
    CARRY_ON = "carry_on"
    CHECKED_BAG = "checked_bag"
    EXTRA_PAID_BAG = "extra_paid_bag"


@dataclass(frozen=True, slots=True)
class BaggageAllowance:
    """One named baggage slot with an explicit state and no inference."""

    slot: BaggageSlot
    state: BaggageState
    quantity: int | None = None
    price_amount: Decimal | None = None
    price_currency: str | None = None
    price_is_binding: bool = False

    @property
    def has_known_positive_quantity(self) -> bool:
        return (
            self.state is BaggageState.INCLUDED
            and self.quantity is not None
            and self.quantity > 0
        )

    @property
    def slot_label(self) -> str:
        return {
            BaggageSlot.PERSONAL_ITEM: "Personal item",
            BaggageSlot.CARRY_ON: "Carry-on bag",
            BaggageSlot.CHECKED_BAG: "Checked bag",
            BaggageSlot.EXTRA_PAID_BAG: "Extra paid bag",
        }[self.slot]

    @property
    def state_label(self) -> str:
        base = {
            BaggageState.INCLUDED: "Included",
            BaggageState.NOT_INCLUDED: "Not included",
            BaggageState.UNKNOWN: "Unknown",
        }[self.state]
        if self.state is BaggageState.INCLUDED and self.quantity is not None:
            return f"{base} ({self.quantity})"
        return base

    @property
    def price_label(self) -> str | None:
        if not self.displays_price:
            return None
        return f"{self.price_amount} {self.price_currency}"

    @property
    def displays_price(self) -> bool:
        """Extra-bag price is shown only when binding and exact."""
        return (
            self.price_is_binding
            and self.price_amount is not None
            and self.price_currency is not None
        )


@dataclass(frozen=True, slots=True)
class BaggageAllowances:
    personal_item: BaggageAllowance
    carry_on: BaggageAllowance
    checked_bag: BaggageAllowance
    extra_paid_bag: BaggageAllowance

    def as_rows(self) -> tuple[BaggageAllowance, ...]:
        return (
            self.personal_item,
            self.carry_on,
            self.checked_bag,
            self.extra_paid_bag,
        )

    def identity(self) -> tuple[tuple[str, str, int | None], ...]:
        return tuple(
            (str(row.slot), str(row.state), row.quantity) for row in self.as_rows()
        )


@dataclass(frozen=True, slots=True)
class Segment:
    marketing_carrier: str
    marketing_carrier_name: str
    operating_carrier: str
    operating_carrier_name: str
    flight_number: str
    origin: str
    destination: str
    departure: dt.datetime
    arrival: dt.datetime
    duration_minutes: int

    @property
    def operated_by_other(self) -> bool:
        return self.operating_carrier != self.marketing_carrier

    def identity(self) -> tuple[str, ...]:
        return (
            self.marketing_carrier,
            self.operating_carrier,
            self.flight_number,
            self.origin,
            self.destination,
            self.departure.isoformat(),
            self.arrival.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class Itinerary:
    segments: tuple[Segment, ...]

    @property
    def origin(self) -> str:
        return self.segments[0].origin

    @property
    def destination(self) -> str:
        return self.segments[-1].destination

    @property
    def departure(self) -> dt.datetime:
        return self.segments[0].departure

    @property
    def arrival(self) -> dt.datetime:
        return self.segments[-1].arrival

    @property
    def stops(self) -> int:
        return len(self.segments) - 1

    @property
    def duration_minutes(self) -> int:
        return int((self.arrival - self.departure).total_seconds() // 60)

    def identity(self) -> tuple[tuple[str, ...], ...]:
        return tuple(segment.identity() for segment in self.segments)


@dataclass(frozen=True, slots=True)
class Offer:
    offer_id: str
    outbound: Itinerary
    inbound: Itinerary | None
    cabin: CabinClass
    fare_brand: str
    total_amount: Decimal
    currency: str
    baggage: BaggageAllowances
    source: str
    retrieved_at: dt.datetime
    expires_at: dt.datetime
    seller_name: None = None
    purchase_url: None = None
    is_bookable: bool = False
    is_fictional: bool = True

    @property
    def combined_duration_minutes(self) -> int:
        inbound = self.inbound.duration_minutes if self.inbound else 0
        return self.outbound.duration_minutes + inbound

    @property
    def is_round_trip(self) -> bool:
        return self.inbound is not None

    def identity(self) -> tuple[object, ...]:
        """Stable full-itinerary/baggage/price identity."""
        return (
            self.outbound.identity(),
            self.inbound.identity() if self.inbound else None,
            str(self.cabin),
            self.fare_brand,
            str(self.total_amount),
            self.currency,
            self.baggage.identity(),
        )

    def sort_key(self) -> tuple[Decimal, str, int, str]:
        return (
            self.total_amount,
            self.currency,
            self.combined_duration_minutes,
            self.offer_id,
        )


@dataclass(frozen=True, slots=True)
class SearchQuery:
    origin: str
    destination: str
    departure_date: dt.date
    return_date: dt.date | None
    cabin: CabinClass
    mode: SearchMode
    flexibility: int
    luggage: LuggageChoice
    adults: int = 1

    @property
    def is_one_way(self) -> bool:
        return self.return_date is None

    @property
    def requires_checked_bag(self) -> bool:
        return self.luggage is LuggageChoice.CHECKED_REQUIRED


@dataclass(frozen=True, slots=True)
class DateOption:
    departure_date: dt.date
    return_date: dt.date | None
    offset_days: int
