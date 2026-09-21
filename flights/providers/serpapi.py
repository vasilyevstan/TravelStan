"""Constrained personal-use SerpApi Google Flights experiment."""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any

import httpx

from ..domain import (
    SOURCE_SERPAPI,
    CabinClass,
    DataStatus,
    DateOption,
    Itinerary,
    LuggageChoice,
    Offer,
    SearchMode,
    SearchQuery,
    Segment,
)
from .base import ProviderError, ProviderNotice, ProviderSearchResult
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
    stable_offer_id,
    unknown_baggage,
    validated_endpoint,
)

DEFAULT_URL = "https://serpapi.com/search.json"
ALLOWED_API_HOSTS = ("serpapi.com",)
MAX_REQUESTS_PER_SEARCH = 6
MAX_EXACT_OUTBOUND_BRANCHES = 3
MAX_RETURN_OPTIONS = 3


class SerpApiProvider:
    name = SOURCE_SERPAPI
    display_name = "SerpApi / Google Flights"
    data_status = DataStatus.EXPERIMENTAL
    request_cost = 1

    def __init__(
        self,
        api_key: str,
        *,
        country: str = "EE",
        locale: str = "en-EE",
        currency: str = "EUR",
        endpoint: str = DEFAULT_URL,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.api_key = api_key
        self.country = country
        self.locale = locale
        self.currency = currency
        self.endpoint = validated_endpoint(endpoint, ALLOWED_API_HOSTS)
        self.transport = transport

    def search(
        self,
        query: SearchQuery,
        options: Sequence[DateOption],
        now: dt.datetime,
    ) -> ProviderSearchResult:
        limitation = self._limitation(query)
        if limitation is not None:
            return ProviderSearchResult(
                offers=(),
                notices=(ProviderNotice(self.name, limitation),),
                requests_made=0,
            )

        requests_made = 0

        def fetch(params: Mapping[str, object]) -> Mapping[str, Any]:
            nonlocal requests_made
            if requests_made >= MAX_REQUESTS_PER_SEARCH:
                raise ProviderError("Provider request budget exceeded.")
            requests_made += 1
            payload = request_json(
                "GET",
                self.endpoint,
                headers={"accept": "application/json"},
                params={**params, "api_key": self.api_key},
                transport=self.transport,
            )
            if first_value(payload, "error"):
                raise ProviderError("Provider returned an error.")
            return payload

        offers: list[Offer] = []
        selected_options = (
            options[:3] if query.mode is SearchMode.FLEXIBLE else options[:1]
        )
        for option in selected_options:
            params = self._params(query, option)
            outbound_payload = fetch(params)
            outbound_options = self._flight_options(outbound_payload)
            if query.is_one_way:
                offers.extend(
                    offer
                    for raw in outbound_options
                    if (offer := self._map_one_way(raw, query, now)) is not None
                )
                continue

            branch_limit = (
                1 if query.mode is SearchMode.FLEXIBLE else MAX_EXACT_OUTBOUND_BRANCHES
            )
            selectable_outbounds = tuple(
                raw for raw in outbound_options if first_value(raw, "departure_token")
            )
            for raw_outbound in selectable_outbounds[:branch_limit]:
                departure_token = first_value(raw_outbound, "departure_token")
                return_payload = fetch(
                    {**params, "departure_token": str(departure_token)}
                )
                for raw_inbound in self._flight_options(return_payload)[
                    :MAX_RETURN_OPTIONS
                ]:
                    offer = self._map_round_trip(raw_outbound, raw_inbound, query, now)
                    if offer is not None:
                        offers.append(offer)

        notices = [
            ProviderNotice(
                self.name,
                "Experimental source: SerpApi scrapes Google Flights. Searches "
                "leave this server, ordinary provider retention can apply, and "
                "prices must be confirmed with the seller.",
            ),
            ProviderNotice(
                self.name,
                "Checked baggage and airline-direct booking links are not claimed; "
                "booking actions are intentionally omitted.",
            ),
        ]
        if query.mode is SearchMode.FLEXIBLE:
            notices.append(
                ProviderNotice(
                    self.name,
                    "The experiment searched only the requested ±1 joint date "
                    "window and followed one outbound branch per date pair.",
                )
            )
        return ProviderSearchResult(
            offers=tuple(offers),
            notices=tuple(notices),
            requests_made=requests_made,
        )

    def _limitation(self, query: SearchQuery) -> str | None:
        if query.luggage is LuggageChoice.CHECKED_REQUIRED:
            return (
                "SerpApi cannot prove fare-bound checked-bag inclusion, so no "
                "experimental request was made."
            )
        if query.cabin is CabinClass.ALL_CLASSES:
            return (
                "Choose Economy, Economy+ / Premium Economy, or Business for the "
                "SerpApi experiment."
            )
        if query.mode is SearchMode.FLEXIBLE and query.flexibility > 1:
            return (
                "The SerpApi experiment supports exact dates or a maximum ±1-day "
                "window to protect the request budget."
            )
        return None

    def _params(self, query: SearchQuery, option: DateOption) -> Mapping[str, object]:
        travel_class = {
            CabinClass.ECONOMY: 1,
            CabinClass.PREMIUM_ECONOMY: 2,
            CabinClass.BUSINESS: 3,
        }[query.cabin]
        params: dict[str, object] = {
            "engine": "google_flights",
            "departure_id": query.origin,
            "arrival_id": query.destination,
            "outbound_date": option.departure_date.isoformat(),
            "type": 2 if query.is_one_way else 1,
            "travel_class": travel_class,
            "adults": query.adults,
            "currency": self.currency,
            "gl": self.country.lower(),
            "hl": self.locale.split("-", maxsplit=1)[0].lower(),
            "sort_by": 2,
            "no_cache": "true",
            "output": "json",
        }
        if option.return_date is not None:
            params["return_date"] = option.return_date.isoformat()
        return params

    def _flight_options(
        self, payload: Mapping[str, Any]
    ) -> tuple[Mapping[str, Any], ...]:
        options = [
            as_mapping(raw)
            for raw in (
                as_list(payload.get("best_flights"))
                + as_list(payload.get("other_flights"))
            )
            if as_mapping(raw)
        ]
        return tuple(
            sorted(
                options,
                key=lambda raw: (
                    decimal_value(raw.get("price")) or Decimal("Infinity"),
                    str(first_value(raw, "flights.0.flight_number") or ""),
                ),
            )
        )

    def _map_one_way(
        self,
        raw: Mapping[str, Any],
        query: SearchQuery,
        now: dt.datetime,
    ) -> Offer | None:
        outbound = self._map_itinerary(
            raw,
            query.allowed_origin_airports,
            query.allowed_destination_airports,
        )
        return self._offer(raw, outbound, None, query, now)

    def _map_round_trip(
        self,
        raw_outbound: Mapping[str, Any],
        raw_inbound: Mapping[str, Any],
        query: SearchQuery,
        now: dt.datetime,
    ) -> Offer | None:
        outbound = self._map_itinerary(
            raw_outbound,
            query.allowed_origin_airports,
            query.allowed_destination_airports,
        )
        inbound = self._map_itinerary(
            raw_inbound,
            query.allowed_destination_airports,
            query.allowed_origin_airports,
        )
        return self._offer(raw_inbound, outbound, inbound, query, now)

    def _offer(
        self,
        raw: Mapping[str, Any],
        outbound: Itinerary | None,
        inbound: Itinerary | None,
        query: SearchQuery,
        now: dt.datetime,
    ) -> Offer | None:
        price = decimal_value(raw.get("price"))
        if (
            outbound is None
            or (not query.is_one_way and inbound is None)
            or price is None
        ):
            return None
        first_flight = as_mapping(first_value(raw, "flights.0"))
        travel_class = first_value(first_flight, "travel_class")
        cabin = cabin_from_value(travel_class) if travel_class else query.cabin
        offer_id = stable_offer_id(
            self.name,
            outbound.identity(),
            inbound.identity() if inbound else None,
            price,
            self.currency,
        )
        return Offer(
            offer_id=offer_id,
            outbound=outbound,
            inbound=inbound,
            cabin=cabin,
            fare_brand="Fare details unavailable",
            total_amount=price,
            currency=self.currency,
            baggage=unknown_baggage(),
            source=self.name,
            retrieved_at=now,
            expires_at=now,
            data_status=self.data_status,
            seller_name=None,
            purchase_url=None,
            is_bookable=False,
            is_fictional=False,
        )

    def _map_itinerary(
        self,
        raw: Mapping[str, Any],
        expected_origins: tuple[str, ...],
        expected_destinations: tuple[str, ...],
    ) -> Itinerary | None:
        raw_flights = as_list(raw.get("flights"))
        if not raw_flights:
            return None
        segments: list[Segment] = []
        for raw_flight in raw_flights:
            flight = as_mapping(raw_flight)
            departure = as_mapping(flight.get("departure_airport"))
            arrival = as_mapping(flight.get("arrival_airport"))
            departure_time = parse_datetime(departure.get("time"))
            arrival_time = parse_datetime(arrival.get("time"))
            origin = departure.get("id")
            destination = arrival.get("id")
            number = str(flight.get("flight_number") or "").replace(" ", "")
            code_match = re.match(r"^([A-Z0-9]{2})", number.upper())
            airline = str(flight.get("airline") or "")
            if not all(
                (
                    departure_time,
                    arrival_time,
                    origin,
                    destination,
                    number,
                    code_match,
                    airline,
                )
            ):
                return None
            duration = int_value(flight.get("duration")) or minutes_between(
                departure_time, arrival_time
            )
            carrier = code_match.group(1)
            segments.append(
                Segment(
                    marketing_carrier=carrier,
                    marketing_carrier_name=airline,
                    operating_carrier=carrier,
                    operating_carrier_name=airline,
                    flight_number=number,
                    origin=str(origin),
                    destination=str(destination),
                    departure=departure_time,
                    arrival=arrival_time,
                    duration_minutes=duration,
                )
            )
        if (
            segments[0].origin not in expected_origins
            or segments[-1].destination not in expected_destinations
            or any(
                current.destination != following.origin
                for current, following in zip(segments, segments[1:], strict=False)
            )
        ):
            return None
        return Itinerary(
            tuple(segments),
            reported_duration_minutes=int_value(raw.get("total_duration")),
        )
