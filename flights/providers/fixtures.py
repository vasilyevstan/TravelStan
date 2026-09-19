"""Deterministic fictional fixture data.

Every carrier, flight number, and fare brand below is invented for the demo.
Nothing here is a real airline, a real fare, or a real schedule, and no value
is retrieved from a network, file download, or credentialed source.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ..domain import BaggageState, CabinClass


@dataclass(frozen=True, slots=True)
class FixtureCarrier:
    code: str
    name: str


@dataclass(frozen=True, slots=True)
class FixtureBaggage:
    state: BaggageState
    quantity: int | None = None


@dataclass(frozen=True, slots=True)
class FixtureFare:
    key: str
    cabin: CabinClass
    fare_brand: str
    base_amount: Decimal
    currency: str
    stops: int
    outbound_minutes: int
    inbound_minutes: int
    departure_hour: int
    personal_item: FixtureBaggage
    carry_on: FixtureBaggage
    checked_bag: FixtureBaggage
    extra_paid_bag: FixtureBaggage
    extra_bag_amount: Decimal | None = None
    extra_bag_binding: bool = False


DEMO_CARRIERS: tuple[FixtureCarrier, ...] = (
    FixtureCarrier("ZQ", "Demo Air Zephyr (fictional)"),
    FixtureCarrier("QX", "Demo Nimbus Air (fictional)"),
    FixtureCarrier("VV", "Demo Vega Wings (fictional)"),
)

DEMO_OPERATORS: tuple[FixtureCarrier, ...] = (
    FixtureCarrier("ZQ", "Demo Air Zephyr (fictional)"),
    FixtureCarrier("YR", "Demo Regional Shuttle (fictional)"),
)

DEMO_FARES: tuple[FixtureFare, ...] = (
    FixtureFare(
        key="eco-basic",
        cabin=CabinClass.ECONOMY,
        fare_brand="Demo Basic",
        base_amount=Decimal("118.00"),
        currency="EUR",
        stops=0,
        outbound_minutes=145,
        inbound_minutes=150,
        departure_hour=7,
        personal_item=FixtureBaggage(BaggageState.INCLUDED, 1),
        carry_on=FixtureBaggage(BaggageState.NOT_INCLUDED),
        checked_bag=FixtureBaggage(BaggageState.NOT_INCLUDED),
        extra_paid_bag=FixtureBaggage(BaggageState.INCLUDED, 1),
        extra_bag_amount=Decimal("35.00"),
        extra_bag_binding=True,
    ),
    FixtureFare(
        key="eco-standard",
        cabin=CabinClass.ECONOMY,
        fare_brand="Demo Standard",
        base_amount=Decimal("164.50"),
        currency="EUR",
        stops=0,
        outbound_minutes=150,
        inbound_minutes=145,
        departure_hour=11,
        personal_item=FixtureBaggage(BaggageState.INCLUDED, 1),
        carry_on=FixtureBaggage(BaggageState.INCLUDED, 1),
        checked_bag=FixtureBaggage(BaggageState.INCLUDED, 1),
        extra_paid_bag=FixtureBaggage(BaggageState.UNKNOWN),
    ),
    FixtureFare(
        key="eco-unknown-bag",
        cabin=CabinClass.ECONOMY,
        fare_brand="Demo Partner",
        base_amount=Decimal("151.00"),
        currency="EUR",
        stops=1,
        outbound_minutes=305,
        inbound_minutes=300,
        departure_hour=15,
        personal_item=FixtureBaggage(BaggageState.INCLUDED, 1),
        carry_on=FixtureBaggage(BaggageState.UNKNOWN),
        checked_bag=FixtureBaggage(BaggageState.UNKNOWN),
        extra_paid_bag=FixtureBaggage(BaggageState.UNKNOWN),
        extra_bag_amount=Decimal("40.00"),
        extra_bag_binding=False,
    ),
    FixtureFare(
        key="premium-flex",
        cabin=CabinClass.PREMIUM_ECONOMY,
        fare_brand="Demo Premium Flex",
        base_amount=Decimal("284.00"),
        currency="EUR",
        stops=0,
        outbound_minutes=145,
        inbound_minutes=145,
        departure_hour=9,
        personal_item=FixtureBaggage(BaggageState.INCLUDED, 1),
        carry_on=FixtureBaggage(BaggageState.INCLUDED, 1),
        checked_bag=FixtureBaggage(BaggageState.INCLUDED, 2),
        extra_paid_bag=FixtureBaggage(BaggageState.INCLUDED, 1),
        extra_bag_amount=Decimal("55.00"),
        extra_bag_binding=True,
    ),
    FixtureFare(
        key="business-full",
        cabin=CabinClass.BUSINESS,
        fare_brand="Demo Business",
        base_amount=Decimal("612.00"),
        currency="EUR",
        stops=0,
        outbound_minutes=140,
        inbound_minutes=140,
        departure_hour=18,
        personal_item=FixtureBaggage(BaggageState.INCLUDED, 1),
        carry_on=FixtureBaggage(BaggageState.INCLUDED, 2),
        checked_bag=FixtureBaggage(BaggageState.INCLUDED, 2),
        extra_paid_bag=FixtureBaggage(BaggageState.NOT_INCLUDED),
    ),
)
