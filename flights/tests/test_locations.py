"""SerpApi city and airport lookup normalization."""

from __future__ import annotations

from unittest import mock

from django.test import SimpleTestCase

from flights.locations import search_locations
from flights.providers.base import ProviderError


class LocationSearchTests(SimpleTestCase):
    @mock.patch("flights.locations.request_json")
    def test_city_returns_all_airports_then_specific_airports(
        self,
        request_json: mock.Mock,
    ) -> None:
        request_json.return_value = {
            "suggestions": [
                {
                    "name": "New York",
                    "type": "city",
                    "description": "City in New York State",
                    "id": "/m/02_286",
                    "airports": [
                        {
                            "name": "John F. Kennedy International Airport",
                            "id": "JFK",
                            "city": "New York",
                            "distance": "12 mi",
                        },
                        {
                            "name": "Newark Liberty International Airport",
                            "id": "EWR",
                            "city": "New York",
                            "distance": "11 mi",
                        },
                        {
                            "name": "LaGuardia Airport",
                            "id": "LGA",
                            "city": "New York",
                            "distance": "8 mi",
                        },
                        {
                            "name": "Penn Station",
                            "id": "ZYP",
                            "city": "New York",
                            "distance": "0 mi",
                        },
                    ],
                }
            ]
        }

        suggestions = search_locations(
            "New York",
            api_key="private",
            endpoint="https://serpapi.com/search.json",
            country="EE",
            locale="en-EE",
        )

        self.assertEqual(
            [suggestion.value for suggestion in suggestions],
            ["JFK,EWR,LGA", "JFK", "EWR", "LGA"],
        )
        self.assertEqual(suggestions[0].label, "New York — all airports")
        self.assertEqual(suggestions[0].kind, "city")
        self.assertIn("JFK", suggestions[1].detail)
        params = request_json.call_args.kwargs["params"]
        self.assertEqual(params["engine"], "google_flights_autocomplete")
        self.assertEqual(params["q"], "New York")
        self.assertEqual(params["exclude_regions"], "true")
        self.assertEqual(params["api_key"], "private")
        self.assertNotIn("no_cache", params)

    @mock.patch("flights.locations.request_json")
    def test_duplicate_airports_are_removed(self, request_json: mock.Mock) -> None:
        airport = {"name": "Milan Malpensa Airport", "id": "MXP", "city": "Milan"}
        request_json.return_value = {
            "suggestions": [
                {"name": "Milan", "airports": [airport]},
                {"name": "Malpensa", "airports": [airport]},
            ]
        }
        suggestions = search_locations(
            "Milan",
            api_key="private",
            endpoint="https://serpapi.com/search.json",
            country="EE",
            locale="en-EE",
        )
        self.assertEqual([suggestion.value for suggestion in suggestions], ["MXP"])

    @mock.patch("flights.locations.request_json")
    def test_provider_error_is_redacted(self, request_json: mock.Mock) -> None:
        request_json.return_value = {"error": "secret upstream detail"}
        with self.assertRaisesRegex(ProviderError, "Location provider returned"):
            search_locations(
                "Milan",
                api_key="private",
                endpoint="https://serpapi.com/search.json",
                country="EE",
                locale="en-EE",
            )

    @mock.patch("flights.locations.request_json")
    def test_short_query_makes_no_request(self, request_json: mock.Mock) -> None:
        self.assertFalse(
            search_locations(
                "M",
                api_key="private",
                endpoint="https://serpapi.com/search.json",
                country="EE",
                locale="en-EE",
            )
        )
        request_json.assert_not_called()
