"""TUI Flight Offers adapter."""

from __future__ import annotations

import datetime as dt
from collections.abc import Mapping, Sequence
from typing import Any

import httpx

from ..domain import (
    SOURCE_TUI,
    BaggageAllowances,
    BaggageSlot,
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
    allowance_from_values,
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
    validated_endpoint,
)

DEFAULT_URL = "https://prod.api.tui/flightOffers/flightOffers_v1"
FRESHNESS = dt.timedelta(minutes=15)
ALLOWED_BOOKING_HOSTS = ("tui.co.uk", "tui.com", "firstchoice.co.uk")
ALLOWED_API_HOSTS = ("prod.api.tui", "pre-prod.api.tui", "nonprod.api.tui")


class TUIProvider:
    name = SOURCE_TUI
    display_name = "TUI"
    request_cost = 1

    def __init__(
        self,
        api_key: str,
        *,
        currency: str = "GBP",
        data_status: DataStatus = DataStatus.TRIAL,
        endpoint: str = DEFAULT_URL,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.api_key = api_key
        self.currency = currency
        self.data_status = data_status
        self.endpoint = validated_endpoint(endpoint, ALLOWED_API_HOSTS)
        self.transport = transport

    def search(
        self,
        query: SearchQuery,
        options: Sequence[DateOption],
        now: dt.datetime,
    ) -> ProviderSearchResult:
        payload = request_json(
            "GET",
            self.endpoint,
            headers={
                "x-api-key": self.api_key,
                "accept": "application/json;flightOffers;version=1.1",
            },
            params=self._params(query),
            transport=self.transport,
        )
        notices: list[ProviderNotice] = []
        if query.mode is SearchMode.FLEXIBLE:
            notices.append(
                ProviderNotice(
                    self.name,
                    "TUI was searched on the exact dates because its feed has no "
                    "bounded flexible-date request.",
                )
            )
        if query.cabin is CabinClass.ALL_CLASSES:
            notices.append(
                ProviderNotice(
                    self.name,
                    "TUI was searched in Economy because its feed accepts one cabin "
                    "per request.",
                )
            )
        return ProviderSearchResult(
            offers=self._map_payload(payload, now), notices=tuple(notices)
        )

    def _params(self, query: SearchQuery) -> Mapping[str, object]:
        cabin = {
            CabinClass.ECONOMY: "ECONOMY",
            CabinClass.PREMIUM_ECONOMY: "PREMIUMECONOMY",
            CabinClass.BUSINESS: "BUSINESS",
            CabinClass.ALL_CLASSES: "ECONOMY",
        }[query.cabin]
        params: dict[str, object] = {
            "searchMode": "RETURN" if query.return_date else "ONEWAY",
            "numOfAdults": query.adults,
            "currencyCode": self.currency,
            "originAirportCodes": query.origin,
            "destAirportCodes": query.destination,
            "depDate": query.departure_date.isoformat(),
            "directFlightInd": "false",
            "cabinClassCode": cabin,
        }
        if query.return_date:
            params["returnDate"] = query.return_date.isoformat()
        return params

    def _map_payload(
        self, payload: Mapping[str, Any], now: dt.datetime
    ) -> tuple[Offer, ...]:
        response = as_mapping(
            first_value(payload, "flightOffersResponse", "response") or payload
        )
        raw_offers = as_list(
            first_value(response, "flightOffers", "flightOffer", "offers")
        )
        mapped: list[Offer] = []
        for raw_offer in raw_offers:
            offer = as_mapping(raw_offer)
            outbound = self._map_journey(
                as_mapping(
                    first_value(
                        offer,
                        "outboundJourney",
                        "outboundFlight",
                        "outbound",
                    )
                )
            )
            inbound = self._map_journey(
                as_mapping(
                    first_value(
                        offer,
                        "inboundJourney",
                        "inboundFlight",
                        "inbound",
                    )
                )
            )
            price = decimal_value(
                first_value(
                    offer,
                    "price.totalPrice",
                    "pricing.totalPrice",
                    "pricingInfoSum.totalPriceAllPassengers",
                    "totalPrice",
                )
            )
            currency = (
                first_value(
                    offer, "price.currencyCode", "pricing.currencyCode", "currencyCode"
                )
                or self.currency
            )
            if outbound is None or price is None:
                continue
            cabin = cabin_from_value(first_value(offer, "cabinClass", "cabinClassCode"))
            fare_brand = str(
                first_value(offer, "fareType", "fareBrand")
                or cabin.value.replace("_", " ").title()
            )
            purchase_url = safe_purchase_url(
                first_value(
                    offer,
                    "bookingDeepLink",
                    "deeplink.href",
                    "booking.deepLink",
                ),
                ALLOWED_BOOKING_HOSTS,
            )
            external_id = first_value(offer, "id", "offerId")
            offer_id = (
                f"{self.name}-{external_id}"
                if external_id
                else stable_offer_id(
                    self.name, outbound.identity(), inbound, price, currency
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
                    baggage=self._map_baggage(offer),
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

    def _map_journey(self, journey: Mapping[str, Any]) -> Itinerary | None:
        if not journey:
            return None
        raw_segments = as_list(
            first_value(journey, "flightSegments", "flightSegment", "segments")
        ) or [journey]
        segments: list[Segment] = []
        for raw_segment in raw_segments:
            segment = as_mapping(raw_segment)
            departure_date = first_value(segment, "departure.date")
            departure_time = first_value(segment, "departure.time") or "00:00:00"
            arrival_date = first_value(segment, "arrival.date")
            arrival_time = first_value(segment, "arrival.time") or "00:00:00"
            departure = parse_datetime(
                first_value(segment, "departureDateTime")
                or f"{departure_date}T{departure_time}"
            )
            arrival = parse_datetime(
                first_value(segment, "arrivalDateTime")
                or f"{arrival_date}T{arrival_time}"
            )
            origin = first_value(segment, "departure.airportCode", "originAirportCode")
            destination = first_value(
                segment, "arrival.airportCode", "destinationAirportCode"
            )
            carrier = first_value(segment, "carrier.airlineCode", "airlineCode") or "BY"
            flight_number = first_value(segment, "flightNum", "flightNumber")
            if not all((departure, arrival, origin, destination, flight_number)):
                continue
            duration_hours = int_value(
                first_value(segment, "flightSegmentDuration.hours")
            )
            duration_minutes = int_value(
                first_value(segment, "flightSegmentDuration.minutes")
            )
            duration = (
                (duration_hours or 0) * 60 + (duration_minutes or 0)
                if duration_hours is not None or duration_minutes is not None
                else minutes_between(departure, arrival)
            )
            segments.append(
                Segment(
                    marketing_carrier=str(carrier),
                    marketing_carrier_name=str(
                        first_value(segment, "carrier.airlineName") or self.display_name
                    ),
                    operating_carrier=str(carrier),
                    operating_carrier_name=str(
                        first_value(segment, "carrier.airlineName") or self.display_name
                    ),
                    flight_number=str(flight_number),
                    origin=str(origin),
                    destination=str(destination),
                    departure=departure,
                    arrival=arrival,
                    duration_minutes=duration,
                )
            )
        return Itinerary(tuple(segments)) if segments else None

    def _map_baggage(self, offer: Mapping[str, Any]) -> BaggageAllowances:
        luggage = as_mapping(first_value(offer, "luggage", "baggage"))
        currency = first_value(offer, "currencyCode", "price.currencyCode")
        return BaggageAllowances(
            personal_item=allowance_from_values(BaggageSlot.PERSONAL_ITEM),
            carry_on=allowance_from_values(
                BaggageSlot.CARRY_ON,
                quantity=first_value(luggage, "carryOnAllowance"),
                weight=first_value(luggage, "carryOnWeight"),
                weight_unit=first_value(luggage, "carryOnWeightUnit"),
            ),
            checked_bag=allowance_from_values(
                BaggageSlot.CHECKED_BAG,
                quantity=first_value(luggage, "holdAllowance"),
                weight=first_value(luggage, "holdWeight"),
                weight_unit=first_value(luggage, "holdWeightUnit"),
            ),
            extra_paid_bag=allowance_from_values(
                BaggageSlot.EXTRA_PAID_BAG,
                explicitly_included=False
                if first_value(luggage, "extraHoldAllowance") is not None
                else None,
                quantity=first_value(luggage, "extraHoldAllowance"),
                price=first_value(luggage, "extraHoldAllowancePrice"),
                price_currency=currency,
                price_is_binding=first_value(luggage, "extraHoldAllowancePrice")
                is not None,
                price_scope="per bag",
            ),
        )
