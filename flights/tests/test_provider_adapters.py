"""Provider adapters normalize documented payloads without real network calls."""

from __future__ import annotations

from decimal import Decimal

import httpx
from django.test import SimpleTestCase

from flights.domain import BaggageState, CabinClass, DataStatus, SearchMode
from flights.planner import plan_date_options
from flights.providers.afkl import AirFranceKLMProvider
from flights.providers.base import ProviderError
from flights.providers.singapore import SingaporeAirlinesProvider
from flights.providers.tui import TUIProvider

from .factories import NOW, TODAY, make_query


def _segment(
    *,
    carrier: str = "KL",
    number: str = "1234",
    origin: str = "AAA",
    destination: str = "BBB",
) -> dict[str, object]:
    return {
        "departureDateTime": "2026-10-01T08:00:00+03:00",
        "arrivalDateTime": "2026-10-01T10:30:00+02:00",
        "origin": {"code": origin},
        "destination": {"code": destination},
        "marketingFlight": {
            "carrier": {"code": carrier, "name": "KLM"},
            "number": number,
        },
        "operatingFlight": {"carrier": {"code": carrier, "name": "KLM"}},
        "flightDuration": 210,
    }


class AirFranceKLMAdapterTests(SimpleTestCase):
    def test_maps_live_offer_and_uses_api_key_header(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(
                200,
                json={
                    "itineraries": [
                        {
                            "connections": [{"segments": [_segment()]}],
                            "flightProducts": [
                                {
                                    "id": "afkl-1",
                                    "commercialCabin": "ECONOMY",
                                    "fareFamily": {"name": "Light"},
                                    "price": {
                                        "totalPrice": "189.20",
                                        "currency": "EUR",
                                    },
                                    "deeplink": {
                                        "href": "https://www.klm.com/book/afkl-1"
                                    },
                                }
                            ],
                        }
                    ]
                },
            )

        provider = AirFranceKLMProvider(
            "secret-key", transport=httpx.MockTransport(handler)
        )
        query = make_query()
        result = provider.search(query, plan_date_options(query, TODAY), NOW)
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].headers["api-key"], "secret-key")
        self.assertNotIn("secret-key", str(requests[0].url))
        offer = result.offers[0]
        self.assertEqual(offer.total_amount, Decimal("189.20"))
        self.assertEqual(offer.data_status, DataStatus.TRIAL)
        self.assertEqual(offer.purchase_url, "https://www.klm.com/book/afkl-1")
        self.assertTrue(offer.is_bookable)
        self.assertEqual(offer.baggage.checked_bag.state, BaggageState.UNKNOWN)

    def test_rejects_untrusted_booking_link(self) -> None:
        provider = AirFranceKLMProvider("key")
        self.assertIsNone(
            provider._purchase_url(  # noqa: SLF001 - focused boundary test
                {"deeplink": {"href": "https://untrusted.example/book"}}
            )
        )


class SingaporeAdapterTests(SimpleTestCase):
    def test_maps_trial_offer_and_native_flexible_request(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(
                200,
                json={
                    "response": {
                        "currency": {"code": "EUR"},
                        "shallowReferralLink": "https://www.singaporeair.com/",
                        "recommendations": [
                            {
                                "recommendationID": 7,
                                "fareSummary": {"totalPrice": "640.00"},
                                "cabinClassName": "Premium Economy",
                                "fareFamily": "Lite",
                                "deepReferralLink": "/book/7",
                                "segmentBounds": [
                                    {
                                        "segments": [
                                            {
                                                "legs": [
                                                    {
                                                        "departureDateTime": (
                                                            "2026-10-01T08:00:00+03:00"
                                                        ),
                                                        "arrivalDateTime": (
                                                            "2026-10-01T20:00:00+08:00"
                                                        ),
                                                        "originAirportCode": "AAA",
                                                        "destinationAirportCode": "BBB",
                                                        "marketingAirlineCode": "SQ",
                                                        "operatingAirlineCode": "SQ",
                                                        "flightNumber": "321",
                                                        "flightDuration": 540,
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                ],
                            }
                        ],
                    }
                },
            )

        provider = SingaporeAirlinesProvider(
            "sq-key", transport=httpx.MockTransport(handler)
        )
        query = make_query(mode=SearchMode.FLEXIBLE, flexibility=3)
        result = provider.search(query, plan_date_options(query, TODAY), NOW)
        self.assertEqual(len(requests), 1)
        self.assertIn(b'"flexibleDates":true', requests[0].content)
        offer = result.offers[0]
        self.assertEqual(offer.data_status, DataStatus.TRIAL)
        self.assertEqual(offer.cabin.value, "premium_economy")
        self.assertEqual(offer.purchase_url, "https://www.singaporeair.com/book/7")


class TUIAdapterTests(SimpleTestCase):
    def test_maps_baggage_weight_paid_bag_and_exact_fallback(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(
                200,
                json={
                    "flightOffersResponse": {
                        "flightOffers": [
                            {
                                "offerId": "tui-1",
                                "totalPrice": "220.00",
                                "currencyCode": "GBP",
                                "cabinClass": "ECONOMY",
                                "fareType": "Standard",
                                "bookingDeepLink": "https://www.tui.co.uk/flight/book",
                                "outboundFlight": {
                                    "departure": {
                                        "airportCode": "AAA",
                                        "date": "2026-10-01",
                                        "time": "08:00:00",
                                    },
                                    "arrival": {
                                        "airportCode": "BBB",
                                        "date": "2026-10-01",
                                        "time": "10:30:00",
                                    },
                                    "carrier": {
                                        "airlineCode": "BY",
                                        "airlineName": "TUI Airways",
                                    },
                                    "flightNum": "BY1234",
                                    "flightSegmentDuration": {
                                        "hours": 2,
                                        "minutes": 30,
                                    },
                                },
                                "luggage": {
                                    "carryOnAllowance": 1,
                                    "carryOnWeight": 10,
                                    "carryOnWeightUnit": "KG",
                                    "holdAllowance": 1,
                                    "holdWeight": 23,
                                    "holdWeightUnit": "KG",
                                    "extraHoldAllowance": 1,
                                    "extraHoldAllowancePrice": "42.00",
                                },
                            }
                        ]
                    }
                },
            )

        provider = TUIProvider("tui-key", transport=httpx.MockTransport(handler))
        query = make_query(
            mode=SearchMode.FLEXIBLE,
            flexibility=7,
            cabin=CabinClass.ECONOMY,
        )
        result = provider.search(query, plan_date_options(query, TODAY), NOW)
        self.assertEqual(len(requests), 1)
        self.assertIn("depDate=2026-10-01", str(requests[0].url))
        self.assertEqual(len(result.notices), 1)
        offer = result.offers[0]
        self.assertEqual(offer.baggage.checked_bag.weight_label, "23 kg")
        extra = offer.baggage.extra_paid_bag
        self.assertEqual(extra.state, BaggageState.NOT_INCLUDED)
        self.assertEqual(extra.price_label, "42.00 GBP")
        self.assertTrue(extra.price_is_binding)

    def test_http_failure_is_not_retried(self) -> None:
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(503, json={"error": "unavailable"})

        provider = TUIProvider("key", transport=httpx.MockTransport(handler))
        query = make_query()
        with self.assertRaises(ProviderError):
            provider.search(query, plan_date_options(query, TODAY), NOW)
        self.assertEqual(calls, 1)
