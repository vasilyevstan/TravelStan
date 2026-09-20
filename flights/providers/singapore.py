"""Singapore Airlines Flight Search adapter."""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urljoin

import httpx

from ..domain import (
    SOURCE_SINGAPORE,
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
    validated_endpoint,
)

DEFAULT_URL = (
    "https://apigw.singaporeair.com/api/uat/v1/commercial/flightavailability/get"
)
FRESHNESS = dt.timedelta(minutes=15)
ALLOWED_BOOKING_HOSTS = ("singaporeair.com",)
ALLOWED_API_HOSTS = ("apigw.singaporeair.com",)


class SingaporeAirlinesProvider:
    name = SOURCE_SINGAPORE
    display_name = "Singapore Airlines"
    request_cost = 1

    def __init__(
        self,
        api_key: str,
        *,
        country: str = "EE",
        locale: str = "en_UK",
        data_status: DataStatus = DataStatus.TRIAL,
        endpoint: str = DEFAULT_URL,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.api_key = api_key
        self.country = country
        self.locale = locale
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
            "POST",
            self.endpoint,
            headers={"apikey": self.api_key, "content-type": "application/json"},
            json=self._request_body(query),
            transport=self.transport,
        )
        offers = self._map_payload(payload, now)
        notices: list[ProviderNotice] = []
        if query.mode is SearchMode.FLEXIBLE and not offers:
            notices.append(
                ProviderNotice(
                    self.name,
                    "Singapore Airlines returned calendar prices without complete "
                    "itineraries.",
                )
            )
        if query.cabin is CabinClass.ALL_CLASSES:
            notices.append(
                ProviderNotice(
                    self.name,
                    "Singapore Airlines was searched in Economy because its feed "
                    "accepts one cabin per request.",
                )
            )
        return ProviderSearchResult(offers=offers, notices=tuple(notices))

    def _request_body(self, query: SearchQuery) -> Mapping[str, object]:
        cabin = {
            CabinClass.ECONOMY: "Y",
            CabinClass.PREMIUM_ECONOMY: "S",
            CabinClass.BUSINESS: "J",
            CabinClass.ALL_CLASSES: "Y",
        }[query.cabin]
        itinerary: dict[str, object] = {
            "originAirportCode": query.origin,
            "destinationAirportCode": query.destination,
            "departureDate": query.departure_date.isoformat(),
        }
        if query.return_date:
            itinerary["returnDate"] = query.return_date.isoformat()
        return {
            "clientUUID": str(uuid.uuid4()),
            "request": {
                "itineraryDetails": [itinerary],
                "cabinClass": cabin,
                "adultCount": query.adults,
                "childCount": 0,
                "infantCount": 0,
                "flexibleDates": query.mode is SearchMode.FLEXIBLE,
                "dateRange": query.flexibility
                if query.mode is SearchMode.FLEXIBLE
                else 0,
                "locale": self.locale,
                "country": self.country,
            },
        }

    def _map_payload(
        self, payload: Mapping[str, Any], now: dt.datetime
    ) -> tuple[Offer, ...]:
        response = as_mapping(first_value(payload, "response"))
        currency = first_value(response, "currency.code")
        shallow = first_value(response, "shallowReferralLink")
        mapped: list[Offer] = []
        for raw_recommendation in as_list(response.get("recommendations")):
            recommendation = as_mapping(raw_recommendation)
            bounds = as_list(recommendation.get("segmentBounds"))
            legs = tuple(
                leg
                for bound in bounds
                if (leg := self._map_bound(as_mapping(bound))) is not None
            )
            price = decimal_value(
                first_value(
                    recommendation,
                    "fareSummary.totalPrice",
                    "fareSummary.totalFare",
                    "totalPrice",
                )
            )
            offer_currency = (
                first_value(recommendation, "fareSummary.currency.code") or currency
            )
            if not legs or price is None or not offer_currency:
                continue
            cabin = cabin_from_value(
                first_value(
                    recommendation,
                    "cabinClassName",
                    "cabinClass",
                    "segmentBounds.0.segments.0.cabinClass",
                )
            )
            deep = first_value(recommendation, "deepReferralLink")
            if deep is None and len(bounds) == 1:
                deep = first_value(as_mapping(bounds[0]), "deepReferralLink")
            link_value = (
                urljoin(str(shallow), str(deep))
                if shallow and deep
                else deep or shallow
            )
            purchase_url = safe_purchase_url(link_value, ALLOWED_BOOKING_HOSTS)
            fare_brand = str(
                first_value(recommendation, "fareFamily", "fareFamilyName")
                or cabin.value.replace("_", " ").title()
            )
            external_id = first_value(recommendation, "recommendationID", "id")
            offer_id = (
                str(external_id)
                if external_id is not None
                else stable_offer_id(
                    self.name, legs[0].identity(), price, offer_currency, fare_brand
                )
            )
            mapped.append(
                Offer(
                    offer_id=f"sq-{offer_id}",
                    outbound=legs[0],
                    inbound=legs[1] if len(legs) > 1 else None,
                    cabin=cabin,
                    fare_brand=fare_brand,
                    total_amount=price,
                    currency=str(offer_currency),
                    baggage=unknown_baggage(),
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

    def _map_bound(self, bound: Mapping[str, Any]) -> Itinerary | None:
        segments: list[Segment] = []
        raw_segments = as_list(bound.get("segments"))
        for raw_segment in raw_segments:
            segment = as_mapping(raw_segment)
            raw_legs = as_list(segment.get("legs")) or [segment]
            for raw_leg in raw_legs:
                leg = as_mapping(raw_leg)
                departure = parse_datetime(
                    first_value(leg, "departureDateTime", "departure.dateTime")
                )
                arrival = parse_datetime(
                    first_value(leg, "arrivalDateTime", "arrival.dateTime")
                )
                origin = first_value(leg, "originAirportCode", "origin.code")
                destination = first_value(
                    leg, "destinationAirportCode", "destination.code"
                )
                marketing = (
                    first_value(leg, "marketingAirlineCode", "marketingCarrier.code")
                    or "SQ"
                )
                operating = (
                    first_value(leg, "operatingAirlineCode", "operatingCarrier.code")
                    or marketing
                )
                number = first_value(leg, "flightNumber", "number")
                if not all((departure, arrival, origin, destination, number)):
                    continue
                duration = int_value(first_value(leg, "flightDuration", "duration"))
                segments.append(
                    Segment(
                        marketing_carrier=str(marketing),
                        marketing_carrier_name=str(
                            first_value(leg, "marketingAirlineName")
                            or self.display_name
                        ),
                        operating_carrier=str(operating),
                        operating_carrier_name=str(
                            first_value(leg, "operatingAirlineName") or operating
                        ),
                        flight_number=f"{marketing}{number}",
                        origin=str(origin),
                        destination=str(destination),
                        departure=departure,
                        arrival=arrival,
                        duration_minutes=duration
                        if duration is not None
                        else minutes_between(departure, arrival),
                    )
                )
        return Itinerary(tuple(segments)) if segments else None
