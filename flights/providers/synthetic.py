"""In-process deterministic synthetic demo provider.

It performs zero network access, reads no credentials, and produces fictional
offers with no seller, no URL, and no bookable action. Given the same query,
date options, and clock it always returns the same normalized offers.
"""

from __future__ import annotations

import datetime as dt
import hashlib
from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal

from ..domain import (
    SOURCE_SYNTHETIC_DEMO,
    BaggageAllowance,
    BaggageAllowances,
    BaggageSlot,
    CabinClass,
    DateOption,
    Itinerary,
    Offer,
    SearchQuery,
    Segment,
)
from .fixtures import (
    DEMO_CARRIERS,
    DEMO_FARES,
    DEMO_OPERATORS,
    FixtureBaggage,
    FixtureFare,
)

RESULT_FRESHNESS = dt.timedelta(minutes=30)
_CENT = Decimal("0.01")


def _seed(*parts: str) -> int:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def _allowance(
    slot: BaggageSlot, fixture: FixtureBaggage, fare: FixtureFare
) -> BaggageAllowance:
    if slot is BaggageSlot.EXTRA_PAID_BAG and fare.extra_bag_amount is not None:
        return BaggageAllowance(
            slot=slot,
            state=fixture.state,
            quantity=fixture.quantity,
            price_amount=fare.extra_bag_amount,
            price_currency=fare.currency,
            price_is_binding=fare.extra_bag_binding,
        )
    return BaggageAllowance(slot=slot, state=fixture.state, quantity=fixture.quantity)


def _baggage(fare: FixtureFare) -> BaggageAllowances:
    return BaggageAllowances(
        personal_item=_allowance(BaggageSlot.PERSONAL_ITEM, fare.personal_item, fare),
        carry_on=_allowance(BaggageSlot.CARRY_ON, fare.carry_on, fare),
        checked_bag=_allowance(BaggageSlot.CHECKED_BAG, fare.checked_bag, fare),
        extra_paid_bag=_allowance(
            BaggageSlot.EXTRA_PAID_BAG, fare.extra_paid_bag, fare
        ),
    )


def _itinerary(
    origin: str,
    destination: str,
    day: dt.date,
    fare: FixtureFare,
    minutes: int,
    seed: int,
) -> Itinerary:
    carrier = DEMO_CARRIERS[seed % len(DEMO_CARRIERS)]
    operator = DEMO_OPERATORS[(seed // 7) % len(DEMO_OPERATORS)]
    start = dt.datetime.combine(
        day, dt.time(hour=fare.departure_hour, minute=(seed % 4) * 15), tzinfo=dt.UTC
    )
    if fare.stops == 0:
        return Itinerary(
            segments=(
                Segment(
                    marketing_carrier=carrier.code,
                    marketing_carrier_name=carrier.name,
                    operating_carrier=operator.code,
                    operating_carrier_name=operator.name,
                    flight_number=f"{carrier.code}{1000 + seed % 900}",
                    origin=origin,
                    destination=destination,
                    departure=start,
                    arrival=start + dt.timedelta(minutes=minutes),
                    duration_minutes=minutes,
                ),
            )
        )
    first_leg = minutes // 2 - 30
    layover = 60
    second_leg = minutes - first_leg - layover
    stopover = "DMO"
    first_arrival = start + dt.timedelta(minutes=first_leg)
    second_departure = first_arrival + dt.timedelta(minutes=layover)
    return Itinerary(
        segments=(
            Segment(
                marketing_carrier=carrier.code,
                marketing_carrier_name=carrier.name,
                operating_carrier=carrier.code,
                operating_carrier_name=carrier.name,
                flight_number=f"{carrier.code}{2000 + seed % 800}",
                origin=origin,
                destination=stopover,
                departure=start,
                arrival=first_arrival,
                duration_minutes=first_leg,
            ),
            Segment(
                marketing_carrier=carrier.code,
                marketing_carrier_name=carrier.name,
                operating_carrier=operator.code,
                operating_carrier_name=operator.name,
                flight_number=f"{carrier.code}{3000 + seed % 700}",
                origin=stopover,
                destination=destination,
                departure=second_departure,
                arrival=second_departure + dt.timedelta(minutes=second_leg),
                duration_minutes=second_leg,
            ),
        )
    )


def _amount(
    fare: FixtureFare, option: DateOption, seed: int, round_trip: bool
) -> Decimal:
    variation = Decimal(seed % 60) - Decimal(30)
    offset_penalty = Decimal(abs(option.offset_days)) * Decimal("4.5")
    amount = fare.base_amount + variation + offset_penalty
    if round_trip:
        amount = amount * Decimal("1.85")
    return amount.quantize(_CENT, rounding=ROUND_HALF_UP)


class SyntheticDemoProvider:
    """The only provider implementing the normalized protocol."""

    name = SOURCE_SYNTHETIC_DEMO

    def search(
        self,
        query: SearchQuery,
        options: Sequence[DateOption],
        now: dt.datetime,
    ) -> tuple[Offer, ...]:
        offers: list[Offer] = []
        expires_at = now + RESULT_FRESHNESS
        for option in options:
            for fare in DEMO_FARES:
                if (
                    query.cabin is not CabinClass.ALL_CLASSES
                    and fare.cabin is not query.cabin
                ):
                    continue
                seed = _seed(
                    query.origin,
                    query.destination,
                    option.departure_date.isoformat(),
                    str(option.return_date),
                    fare.key,
                )
                outbound = _itinerary(
                    query.origin,
                    query.destination,
                    option.departure_date,
                    fare,
                    fare.outbound_minutes,
                    seed,
                )
                inbound = (
                    _itinerary(
                        query.destination,
                        query.origin,
                        option.return_date,
                        fare,
                        fare.inbound_minutes,
                        seed // 3,
                    )
                    if option.return_date is not None
                    else None
                )
                offer_id = "demo-{}".format(
                    hashlib.sha256(
                        f"{seed}|{fare.key}|{option.departure_date}|{option.return_date}".encode()
                    ).hexdigest()[:12]
                )
                offers.append(
                    Offer(
                        offer_id=offer_id,
                        outbound=outbound,
                        inbound=inbound,
                        cabin=fare.cabin,
                        fare_brand=fare.fare_brand,
                        total_amount=_amount(
                            fare, option, seed, option.return_date is not None
                        ),
                        currency=fare.currency,
                        baggage=_baggage(fare),
                        source=SOURCE_SYNTHETIC_DEMO,
                        retrieved_at=now,
                        expires_at=expires_at,
                    )
                )
        return tuple(offers)


def get_provider() -> SyntheticDemoProvider:
    """Return the only available provider; no live mode can be selected."""
    return SyntheticDemoProvider()
