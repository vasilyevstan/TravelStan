"""Request contract: locations, dates, modes, cabin, luggage, one adult."""

from __future__ import annotations

import datetime as dt

from django.test import SimpleTestCase

from flights.domain import CabinClass, LuggageChoice, SearchMode
from flights.forms import SearchForm

from .factories import TODAY


def payload(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "origin": "AAA",
        "destination": "BBB",
        "departure_date": "2026-10-01",
        "return_date": "",
        "cabin": "economy",
        "mode": "exact",
        "flexibility": "",
        "luggage": "no_checked_requirement",
    }
    data.update(overrides)
    return data


class SearchFormTests(SimpleTestCase):
    def test_valid_one_way_query(self) -> None:
        form = SearchForm(payload(), today=TODAY)
        self.assertTrue(form.is_valid(), form.errors)
        query = form.to_query()
        self.assertEqual(query.origin, "AAA")
        self.assertIsNone(query.return_date)
        self.assertTrue(query.is_one_way)
        self.assertEqual(query.adults, 1)
        self.assertEqual(query.flexibility, 0)

    def test_lowercase_input_normalizes_to_uppercase_iata(self) -> None:
        form = SearchForm(payload(origin=" aaa ", destination="bbb"), today=TODAY)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.to_query().origin, "AAA")
        self.assertEqual(form.to_query().destination, "BBB")

    def test_invalid_iata_rejected(self) -> None:
        for bad in ("A1A", "AA", "A-A"):
            with self.subTest(bad=bad):
                form = SearchForm(payload(origin=bad), today=TODAY)
                self.assertFalse(form.is_valid())
                self.assertIn("origin", form.errors)

    def test_selected_city_can_search_all_or_one_airport(self) -> None:
        form = SearchForm(
            payload(
                origin="New York — all airports",
                origin_id="/m/02_286",
                origin_airports="JFK,EWR,LGA",
                destination="Milan Malpensa Airport",
                destination_id="MXP",
                destination_airports="MXP",
            ),
            today=TODAY,
            allow_location_sets=True,
        )
        self.assertTrue(form.is_valid(), form.errors)
        query = form.to_query()
        self.assertEqual(query.origin, "/m/02_286")
        self.assertEqual(query.allowed_origin_airports, ("JFK", "EWR", "LGA"))
        self.assertEqual(query.origin_display, "New York — all airports")
        self.assertEqual(query.destination, "MXP")
        self.assertEqual(query.destination_display, "Milan Malpensa Airport")

    def test_city_text_requires_a_valid_selected_location(self) -> None:
        form = SearchForm(
            payload(origin="New York", origin_id=""),
            today=TODAY,
            allow_location_sets=True,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("origin", form.errors)

    def test_location_sets_are_not_accepted_without_provider_support(self) -> None:
        form = SearchForm(
            payload(origin="New York", origin_id="JFK,EWR,LGA"),
            today=TODAY,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("origin", form.errors)

    def test_identical_airports_rejected(self) -> None:
        form = SearchForm(payload(origin="AAA", destination="aaa"), today=TODAY)
        self.assertFalse(form.is_valid())
        self.assertIn("destination", form.errors)

    def test_overlapping_city_airports_are_rejected(self) -> None:
        form = SearchForm(
            payload(
                origin="New York — all airports",
                origin_id="/m/02_286",
                origin_airports="JFK,EWR,LGA",
                destination="Newark Liberty International Airport",
                destination_id="EWR",
                destination_airports="EWR",
            ),
            today=TODAY,
            allow_location_sets=True,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("destination", form.errors)

    def test_departure_must_be_strictly_future(self) -> None:
        for value in (TODAY, TODAY - dt.timedelta(days=1)):
            with self.subTest(value=value):
                form = SearchForm(
                    payload(departure_date=value.isoformat()), today=TODAY
                )
                self.assertFalse(form.is_valid())
                self.assertIn("departure_date", form.errors)

    def test_departure_tomorrow_allowed(self) -> None:
        tomorrow = TODAY + dt.timedelta(days=1)
        form = SearchForm(payload(departure_date=tomorrow.isoformat()), today=TODAY)
        self.assertTrue(form.is_valid(), form.errors)

    def test_blank_return_normalizes_to_none(self) -> None:
        form = SearchForm(payload(return_date="   "), today=TODAY)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.to_query().return_date)

    def test_return_must_be_strictly_after_departure(self) -> None:
        for value in ("2026-10-01", "2026-09-30"):
            with self.subTest(value=value):
                form = SearchForm(payload(return_date=value), today=TODAY)
                self.assertFalse(form.is_valid())
                self.assertIn("return_date", form.errors)

    def test_return_after_departure_accepted(self) -> None:
        form = SearchForm(payload(return_date="2026-10-05"), today=TODAY)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.to_query().return_date, dt.date(2026, 10, 5))

    def test_exact_mode_forces_zero_flexibility(self) -> None:
        form = SearchForm(payload(mode="exact", flexibility="5"), today=TODAY)
        self.assertTrue(form.is_valid(), form.errors)
        query = form.to_query()
        self.assertEqual(query.mode, SearchMode.EXACT)
        self.assertEqual(query.flexibility, 0)

    def test_flexible_mode_requires_flexibility(self) -> None:
        form = SearchForm(payload(mode="flexible", flexibility=""), today=TODAY)
        self.assertFalse(form.is_valid())
        self.assertIn("flexibility", form.errors)

    def test_flexibility_bounds(self) -> None:
        for bad in ("0", "8", "-1"):
            with self.subTest(bad=bad):
                form = SearchForm(
                    payload(mode="flexible", flexibility=bad), today=TODAY
                )
                self.assertFalse(form.is_valid())
                self.assertIn("flexibility", form.errors)
        for good in ("1", "7"):
            with self.subTest(good=good):
                form = SearchForm(
                    payload(mode="flexible", flexibility=good), today=TODAY
                )
                self.assertTrue(form.is_valid(), form.errors)

    def test_cabin_choices_are_exactly_four(self) -> None:
        form = SearchForm(payload(), today=TODAY)
        values = [value for value, _ in form.fields["cabin"].choices]
        self.assertEqual(
            values, ["economy", "premium_economy", "business", "all_classes"]
        )
        labels = dict(form.fields["cabin"].choices)
        self.assertEqual(labels["premium_economy"], "Economy+ / Premium Economy")

    def test_invalid_cabin_rejected(self) -> None:
        form = SearchForm(payload(cabin="first"), today=TODAY)
        self.assertFalse(form.is_valid())
        self.assertIn("cabin", form.errors)

    def test_all_classes_accepted(self) -> None:
        form = SearchForm(payload(cabin="all_classes"), today=TODAY)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.to_query().cabin, CabinClass.ALL_CLASSES)

    def test_luggage_choice_is_required_and_explicit(self) -> None:
        form = SearchForm(payload(luggage=""), today=TODAY)
        self.assertFalse(form.is_valid())
        self.assertIn("luggage", form.errors)
        self.assertIsNone(SearchForm(today=TODAY).fields["luggage"].initial)

    def test_luggage_required_choice_maps_to_domain(self) -> None:
        form = SearchForm(payload(luggage="checked_required"), today=TODAY)
        self.assertTrue(form.is_valid(), form.errors)
        query = form.to_query()
        self.assertEqual(query.luggage, LuggageChoice.CHECKED_REQUIRED)
        self.assertTrue(query.requires_checked_bag)

    def test_no_passenger_fields_beyond_single_adult(self) -> None:
        form = SearchForm(today=TODAY)
        for name in ("adults", "children", "infants", "passengers"):
            self.assertNotIn(name, form.fields)

    def test_error_messages_are_generic_and_do_not_echo_input(self) -> None:
        form = SearchForm(payload(origin="XX9"), today=TODAY)
        self.assertFalse(form.is_valid())
        self.assertNotIn("XX9", str(form.errors))
