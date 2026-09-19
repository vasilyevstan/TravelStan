"""Responsive layout, no-persistence query behaviour, and service contract."""

from __future__ import annotations

import datetime as dt
import pathlib

from django.test import TestCase
from django.urls import reverse

from flights.domain import MAX_RESULT_ROWS, SearchMode
from flights.services import run_search

from .factories import NOW, TODAY, make_query

CSS_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "static"
    / "flights"
    / "css"
    / "app.css"
)


def _post_payload() -> dict[str, str]:
    departure = dt.date.today() + dt.timedelta(days=30)
    return {
        "origin": "AAA",
        "destination": "BBB",
        "departure_date": departure.isoformat(),
        "return_date": "",
        "cabin": "all_classes",
        "mode": "exact",
        "flexibility": "",
        "luggage": "no_checked_requirement",
    }


class ResponsiveCssTests(TestCase):
    def test_default_theme_is_dark(self) -> None:
        css = CSS_PATH.read_text(encoding="utf-8")
        self.assertIn("color-scheme: dark", css)
        self.assertIn("--bg: #080d18", css)
        self.assertIn("--ink: #e7edf7", css)
        self.assertIn("--focus: #fbbf24", css)
        content = self.client.get(reverse("flights:search")).content.decode()
        self.assertIn('<meta name="theme-color" content="#080d18">', content)

    def test_css_is_mobile_first_with_stacked_cards(self) -> None:
        css = CSS_PATH.read_text(encoding="utf-8")
        self.assertIn("@media", css)
        self.assertIn("data-label", css)
        self.assertIn("border-radius", css)
        self.assertIn(":focus-visible", css)
        self.assertNotIn("min-width: 321px", css)

    def test_viewport_meta_and_card_labels_present(self) -> None:
        content = self.client.get(reverse("flights:search")).content.decode()
        self.assertIn('name="viewport"', content)
        results = self.client.post(reverse("flights:search"), _post_payload()).content
        self.assertIn('data-label="Price"', results.decode())


class ServiceTests(TestCase):
    def test_run_search_returns_capped_sorted_demo_offers(self) -> None:
        query = make_query(mode=SearchMode.FLEXIBLE, flexibility=7)
        outcome = run_search(query, today=TODAY, now=NOW)
        self.assertEqual(outcome.source, "synthetic_demo")
        self.assertEqual(len(outcome.offers), MAX_RESULT_ROWS)
        amounts = [offer.total_amount for offer in outcome.offers]
        self.assertEqual(amounts, sorted(amounts))
        self.assertEqual(outcome.retrieved_at, NOW)

    def test_search_performs_no_database_queries(self) -> None:
        with self.assertNumQueries(0):
            self.client.post(reverse("flights:search"), _post_payload())
