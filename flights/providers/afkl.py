"""Air France-KLM Open Data Offers adapter."""

from __future__ import annotations

import datetime as dt
from collections.abc import Mapping, Sequence
from typing import Any

import httpx

from ..domain import (
    SOURCE_AFKL,
    BaggageAllowances,
    CabinClass,
    DataStatus,
    DateOption,
    Itinerary,
    Offer,
    SearchMode,
    SearchQuery,
    Segment,
)
from .base import ProviderNotice, ProviderSearchResult
from .http import request_json
from .normalization import (
    as_list,
    as_mapping,
    cabin_from_value,
    decimal_value,
    first_value,
    int_value,
    minutes_between,
    parse_datetime,
    safe_purchase_url,
    stable_offer_id,
    unknown_baggage,
)

BASE_URL = "https://api.airfranceklm.com/opendata/offers/v1"
FRESHNESS = dt.timedelta(minutes=15)
ALLOWED_BOOKING_HOSTS = ("klm.com", "airfrance.com", "airfranceklm.com")


class AirFranceKLMProvider:
    name = SOURCE_AFKL
    display_name = "Air France–KLM"
    request_cost = 1

    def __init__(
        self,
        api_key: str,
        *,
        host: str = "KL",
        country: str = "EE",
        locale: str = "en-EE",
        data_status: DataStatus = DataStatus.TRIAL,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.api_key = api_key
        self.host = host
        self.country = country
        self.locale = locale
        self.data_status = data_status
        self.transport = transport

    def search(
        self,
        query: SearchQuery,
        options: Sequence[DateOption],
        now: dt.datetime,
    ) -> ProviderSearchResult:
        body = self._request_body(query)
        headers = {
            "api-key": self.api_key,
            "accept": "application/hal+json",
            "accept-language": self.locale,
            "afkl-travel-country": self.country,
            "afkl-travel-host": self.host,
            "content-type": "application/json",
        }
        notices: list[ProviderNotice] = []
        if query.mode is SearchMode.FLEXIBLE:
            dates = [option.departure_date for option in options]
            url = f"{BASE_URL}/lowest-fare-offers"
            params: Mapping[str, object] = {
                "dateInterval": f"{min(dates)}/{max(dates)}",
                "expand-suggested-flights": "true",
            }
        else:
            suffix = (
                "/available-offers/all" if query.return_date else "/available-offers"
            )
            url = f"{BASE_URL}{suffix}"
            params = {}
        payload = request_json(
            "POST",
            url,
            headers=headers,
            params=params,
            json=body,
            transport=self.transport,
        )
        offers = self._map_payload(payload, now)
        if query.mode is SearchMode.FLEXIBLE and not offers:
            notices.append(
                ProviderNotice(
                    self.name,
                    "Air France–KLM returned calendar prices without complete "
                    "itineraries.",
                )
            )
        return ProviderSearchResult(offers=offers, notices=tuple(notices))

    def _request_body(self, query: SearchQuery) -> Mapping[str, object]:
        cabin = {
            CabinClass.ECONOMY: ["ECONOMY"],
            CabinClass.PREMIUM_ECONOMY: ["PREMIUM"],
            CabinClass.BUSINESS: ["BUSINESS"],
            CabinClass.ALL_CLASSES: ["ECONOMY", "PREMIUM", "BUSINESS"],
        }[query.cabin]
        connections: list[Mapping[str, object]] = [
            {
                "origin": {"airport": {"code": query.origin}},
                "destination": {"airport": {"code": query.destination}},
                "departureDate": query.departure_date.isoformat(),
            }
        ]
        if query.return_date:
            connections.append(
                {
                    "origin": {"airport": {"code": query.destination}},
                    "destination": {"airport": {"code": query.origin}},
                    "departureDate": query.return_date.isoformat(),
                }
            )
        return {
            "bookingFlow": "LEISURE",
            "commercialCabins": cabin,
            "passengerCount": {"ADT": query.adults},
            "requestedConnections": connections,
        }

    def _map_payload(
        self, payload: Mapping[str, Any], now: dt.datetime
    ) -> tuple[Offer, ...]:
        itineraries = as_list(
            first_value(payload, "itineraries", "availableOffers", "offers")
        )
        mapped: list[Offer] = []
        for raw_itinerary in itineraries:
            itinerary = as_mapping(raw_itinerary)
            connections = as_list(
                first_value(itinerary, "connections", "requestedConnections")
            )
            legs = tuple(
                leg
                for connection in connections
                if (leg := self._map_connection(as_mapping(connection))) is not None
            )
            if not legs:
                continue
            products = as_list(
                first_value(itinerary, "flightProducts", "products", "offers")
            ) or [itinerary]
            for raw_product in products:
                product = as_mapping(raw_product)
                price = decimal_value(
                    first_value(
                        product, "price.totalPrice", "totalPrice", "price.amount"
                    )
                )
                currency = first_value(product, "price.currency", "currency")
                if price is None or not currency:
                    continue
                outbound = legs[0]
                inbound = legs[1] if len(legs) > 1 else None
                cabin = cabin_from_value(
                    first_value(
                        product,
                        "commercialCabin",
                        "connections.0.commercialCabin",
                    )
                )
                fare_brand = str(
                    first_value(
                        product,
                        "fareFamily.name",
                        "fareFamily.code",
                        "connections.0.fareFamily.name",
                        "connections.0.fareFamily.code",
                    )
                    or cabin_from_value(cabin).value.replace("_", " ").title()
                )
                purchase_url = self._purchase_url(product)
                external_id = first_value(product, "id", "offerId")
                offer_id = (
                    f"{self.name}-{external_id}"
                    if external_id
                    else stable_offer_id(
                        self.name,
                        outbound.identity(),
                        inbound,
                        price,
                        currency,
                        fare_brand,
                    )
                )
                mapped.append(
                    Offer(
                        offer_id=offer_id,
                        outbound=outbound,
                        inbound=inbound,
                        cabin=cabin,
                        fare_brand=fare_brand,
                        total_amount=price,
                        currency=str(currency),
                        baggage=self._baggage(product),
                        source=self.name,
                        retrieved_at=now,
                        expires_at=now + FRESHNESS,
                        data_status=self.data_status,
                        seller_name=self.display_name,
                        purchase_url=purchase_url,
                        is_bookable=purchase_url is not None,
                        is_fictional=False,
                    )
                )
        return tuple(mapped)

    def _map_connection(self, connection: Mapping[str, Any]) -> Itinerary | None:
        segments: list[Segment] = []
        for raw_segment in as_list(first_value(connection, "segments", "flights")):
            segment = as_mapping(raw_segment)
            departure = parse_datetime(
                first_value(segment, "departureDateTime", "departure.dateTime")
            )
            arrival = parse_datetime(
                first_value(segment, "arrivalDateTime", "arrival.dateTime")
            )
            origin = first_value(segment, "origin.code", "origin.airport.code")
            destination = first_value(
                segment, "destination.code", "destination.airport.code"
            )
            marketing = first_value(
                segment,
                "marketingFlight.carrier.code",
                "marketingCarrier.code",
                "carrier.code",
            )
            operating = (
                first_value(
                    segment, "operatingFlight.carrier.code", "operatingCarrier.code"
                )
                or marketing
            )
            number = first_value(
                segment, "marketingFlight.number", "flightNumber", "number"
            )
            if not all((departure, arrival, origin, destination, marketing, number)):
                continue
            duration = int_value(
                first_value(segment, "flightDuration", "duration")
            ) or minutes_between(departure, arrival)
            segments.append(
                Segment(
                    marketing_carrier=str(marketing),
                    marketing_carrier_name=str(
                        first_value(segment, "marketingFlight.carrier.name")
                        or marketing
                    ),
                    operating_carrier=str(operating),
                    operating_carrier_name=str(
                        first_value(segment, "operatingFlight.carrier.name")
                        or operating
                    ),
                    flight_number=f"{marketing}{number}",
                    origin=str(origin),
                    destination=str(destination),
                    departure=departure,
                    arrival=arrival,
                    duration_minutes=duration,
                )
            )
        return Itinerary(tuple(segments)) if segments else None

    def _purchase_url(self, product: Mapping[str, Any]) -> str | None:
        value = first_value(
            product,
            "deeplink.href",
            "booking.href",
            "_links.deeplink.href",
            "_links.booking.href",
        )
        return safe_purchase_url(value, ALLOWED_BOOKING_HOSTS)

    def _baggage(self, product: Mapping[str, Any]) -> BaggageAllowances:
        # The Offers feed does not consistently bind policy baggage to a fare.
        # Keep it unknown unless a future documented fare-level mapping is added.
        return unknown_baggage()
