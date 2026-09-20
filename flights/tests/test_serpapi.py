"""Constrained SerpApi experiment contract; all responses are mocked."""

from __future__ import annotations

import datetime as dt

import httpx
from django.test import SimpleTestCase

from flights.domain import (
    BaggageState,
    CabinClass,
    DataStatus,
    LuggageChoice,
    SearchMode,
)
from flights.planner import plan_date_options
from flights.providers.base import ProviderError
from flights.providers.serpapi import MAX_REQUESTS_PER_SEARCH, SerpApiProvider

from .factories import NOW, TODAY, make_query


def _flight(
    *,
    origin: str,
    destination: str,
    departure: str,
    arrival: str,
    number: str,
    airline: str = "Example Air",
    travel_class: str = "Economy",
) -> dict[str, object]:
    return {
        "departure_airport": {
            "id": origin,
            "name": f"{origin} Airport",
            "time": departure,
        },
        "arrival_airport": {
            "id": destination,
            "name": f"{destination} Airport",
            "time": arrival,
        },
        "duration": 120,
        "airline": airline,
        "flight_number": number,
        "travel_class": travel_class,
    }


def _option(
    *,
    origin: str = "AAA",
    destination: str = "BBB",
    departure: str = "2026-10-01 08:00",
    arrival: str = "2026-10-01 10:00",
    number: str = "EA 101",
    price: int = 120,
    departure_token: str | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "flights": [
            _flight(
                origin=origin,
                destination=destination,
                departure=departure,
                arrival=arrival,
                number=number,
            )
        ],
        "total_duration": 120,
        "price": price,
        "type": "One way",
    }
    if departure_token is not None:
        result["departure_token"] = departure_token
    return result


class SerpApiProviderTests(SimpleTestCase):
    def test_exact_one_way_maps_live_source_without_booking_or_baggage_claims(
        self,
    ) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json={"best_flights": [_option()]})

        provider = SerpApiProvider(
            "private-key", transport=httpx.MockTransport(handler)
        )
        query = make_query(cabin=CabinClass.ECONOMY)
        result = provider.search(query, plan_date_options(query, TODAY), NOW)

        self.assertEqual(result.requests_made, 1)
        self.assertEqual(len(requests), 1)
        params = requests[0].url.params
        self.assertEqual(params["engine"], "google_flights")
        self.assertEqual(params["api_key"], "private-key")
        self.assertEqual(params["no_cache"], "true")
        self.assertEqual(params["type"], "2")

        offer = result.offers[0]
        self.assertEqual(offer.data_status, DataStatus.EXPERIMENTAL)
        self.assertFalse(offer.is_fictional)
        self.assertIsNone(offer.purchase_url)
        self.assertFalse(offer.is_bookable)
        self.assertEqual(offer.seller_name, "SerpApi / Google Flights")
        self.assertEqual(offer.baggage.checked_bag.state, BaggageState.UNKNOWN)
        self.assertEqual(offer.expires_at, NOW)

    def test_rejects_partial_disconnected_and_wrong_route_itineraries(self) -> None:
        valid_first = _flight(
            origin="AAA",
            destination="XXX",
            departure="2026-10-01 08:00",
            arrival="2026-10-01 09:00",
            number="EA 101",
        )
        malformed_second = _flight(
            origin="XXX",
            destination="BBB",
            departure="2026-10-01 10:00",
            arrival="2026-10-01 11:00",
            number="EA 102",
        )
        malformed_second.pop("airline")
        invalid_flights = (
            [valid_first, malformed_second],
            [
                valid_first,
                _flight(
                    origin="YYY",
                    destination="BBB",
                    departure="2026-10-01 10:00",
                    arrival="2026-10-01 11:00",
                    number="EA 102",
                ),
            ],
            [valid_first],
        )

        for flights in invalid_flights:
            with self.subTest(flights=flights):

                def handler(
                    request: httpx.Request,
                    flights: list[dict[str, object]] = flights,
                ) -> httpx.Response:
                    return httpx.Response(
                        200,
                        json={
                            "best_flights": [
                                {
                                    "flights": flights,
                                    "total_duration": 180,
                                    "price": 120,
                                }
                            ]
                        },
                    )

                provider = SerpApiProvider(
                    "key",
                    transport=httpx.MockTransport(handler),
                )
                query = make_query(cabin=CabinClass.ECONOMY)
                result = provider.search(
                    query,
                    plan_date_options(query, TODAY),
                    NOW,
                )
                self.assertFalse(result.offers)

    def test_exact_round_trip_follows_three_bounded_outbound_branches(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            token = request.url.params.get("departure_token")
            if token:
                suffix = token[-1]
                return httpx.Response(
                    200,
                    json={
                        "best_flights": [
                            _option(
                                origin="BBB",
                                destination="AAA",
                                departure="2026-10-08 12:00",
                                arrival="2026-10-08 14:00",
                                number=f"EA 20{suffix}",
                                price=200 + int(suffix),
                            )
                        ]
                    },
                )
            return httpx.Response(
                200,
                json={
                    "best_flights": [_option(number="EA 099", price=99)]
                    + [
                        _option(
                            number=f"EA 10{index}", departure_token=f"token-{index}"
                        )
                        for index in range(1, 5)
                    ]
                },
            )

        provider = SerpApiProvider("key", transport=httpx.MockTransport(handler))
        query = make_query(
            cabin=CabinClass.ECONOMY,
            return_date=dt.date(2026, 10, 8),
        )
        result = provider.search(query, plan_date_options(query, TODAY), NOW)

        self.assertEqual(result.requests_made, 4)
        self.assertEqual(len(requests), 4)
        self.assertEqual(len(result.offers), 3)
        self.assertTrue(all(offer.inbound is not None for offer in result.offers))
        self.assertEqual(
            {offer.outbound.segments[0].flight_number for offer in result.offers},
            {"EA101", "EA102", "EA103"},
        )

    def test_flexible_round_trip_uses_six_request_hard_budget(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            outbound_date = request.url.params["outbound_date"]
            return_date = request.url.params["return_date"]
            if request.url.params.get("departure_token"):
                return httpx.Response(
                    200,
                    json={
                        "best_flights": [
                            _option(
                                origin="BBB",
                                destination="AAA",
                                departure=f"{return_date} 12:00",
                                arrival=f"{return_date} 14:00",
                                number="EA 202",
                                price=220,
                            )
                        ]
                    },
                )
            return httpx.Response(
                200,
                json={
                    "best_flights": [
                        _option(
                            departure=f"{outbound_date} 08:00",
                            arrival=f"{outbound_date} 10:00",
                            departure_token=f"token-{outbound_date}",
                        )
                    ]
                },
            )

        provider = SerpApiProvider("key", transport=httpx.MockTransport(handler))
        query = make_query(
            cabin=CabinClass.ECONOMY,
            mode=SearchMode.FLEXIBLE,
            flexibility=1,
            return_date=dt.date(2026, 10, 8),
        )
        result = provider.search(query, plan_date_options(query, TODAY), NOW)

        self.assertEqual(result.requests_made, MAX_REQUESTS_PER_SEARCH)
        self.assertEqual(len(requests), MAX_REQUESTS_PER_SEARCH)
        self.assertEqual(len(result.offers), 3)
        self.assertEqual(
            {offer.outbound.departure.date() for offer in result.offers},
            {
                dt.date(2026, 9, 30),
                dt.date(2026, 10, 1),
                dt.date(2026, 10, 2),
            },
        )

    def test_unsupported_queries_fail_closed_without_network(self) -> None:
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(200, json={})

        provider = SerpApiProvider("key", transport=httpx.MockTransport(handler))
        queries = (
            make_query(cabin=CabinClass.ALL_CLASSES),
            make_query(
                cabin=CabinClass.ECONOMY,
                mode=SearchMode.FLEXIBLE,
                flexibility=2,
            ),
            make_query(
                cabin=CabinClass.ECONOMY,
                luggage=LuggageChoice.CHECKED_REQUIRED,
            ),
        )
        for query in queries:
            result = provider.search(query, plan_date_options(query, TODAY), NOW)
            self.assertEqual(result.requests_made, 0)
            self.assertFalse(result.offers)
            self.assertTrue(result.notices)
        self.assertEqual(calls, 0)

    def test_http_failure_is_redacted_and_not_retried(self) -> None:
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(429, json={"error": "quota"})

        provider = SerpApiProvider(
            "do-not-disclose", transport=httpx.MockTransport(handler)
        )
        query = make_query(cabin=CabinClass.ECONOMY)
        with self.assertRaises(ProviderError) as captured:
            provider.search(query, plan_date_options(query, TODAY), NOW)
        self.assertEqual(calls, 1)
        self.assertNotIn("do-not-disclose", str(captured.exception))
