"""Responsive layout, no-persistence query behaviour, and service contract."""

from __future__ import annotations

import datetime as dt
import pathlib
from dataclasses import replace
from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse

from flights.domain import MAX_RESULT_ROWS, DataStatus, SearchMode
from flights.providers.base import ProviderNotice, ProviderSearchResult
from flights.services import run_search

from .factories import NOW, TODAY, make_offer, make_query

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
        self.assertIn("--page: #080b10", css)
        self.assertIn("--ink: #f2f5f9", css)
        self.assertIn("--focus: #ffd166", css)
        content = self.client.get(reverse("flights:search")).content.decode()
        self.assertIn('<meta name="theme-color" content="#080b10">', content)
        self.assertIn("app.css?v=20260921-lightweight", content)

    def test_css_is_mobile_first_with_offer_cards(self) -> None:
        css = CSS_PATH.read_text(encoding="utf-8")
        self.assertIn("@media", css)
        self.assertIn(".offer-card", css)
        self.assertIn("border-radius", css)
        self.assertIn(":focus-visible", css)
        self.assertNotIn("min-width: 321px", css)

    def test_advanced_options_control_has_stable_full_width_layout(self) -> None:
        css = CSS_PATH.read_text(encoding="utf-8")
        self.assertIn("flex: 1 0 100%", css)
        self.assertNotIn(".advanced[open] { width:", css)
        self.assertIn('.advanced[open] summary::before { content: "−"; }', css)
        self.assertIn(".location-options[hidden] { display: none; }", css)

    @override_settings(
        TRAVELSTAN_PROVIDERS=("serpapi",),
        SERPAPI_API_KEY="test",
    )
    def test_location_combobox_is_keyboard_and_screen_reader_addressable(
        self,
    ) -> None:
        content = self.client.get(reverse("flights:search")).content.decode()
        self.assertEqual(content.count('role="combobox"'), 2)
        self.assertIn('aria-autocomplete="list"', content)
        self.assertIn('role="listbox"', content)
        self.assertIn('aria-live="polite"', content)
        script = (
            pathlib.Path(__file__).resolve().parents[1]
            / "static"
            / "flights"
            / "js"
            / "location-search.js"
        ).read_text(encoding="utf-8")
        self.assertIn("choice.tabIndex = -1", script)
        self.assertIn("controller?.abort()", script)
        self.assertIn("generation !== requestGeneration", script)
        self.assertIn("controller !== requestController", script)

    def test_viewport_meta_and_card_labels_present(self) -> None:
        content = self.client.get(reverse("flights:search")).content.decode()
        self.assertIn('name="viewport"', content)
        results = self.client.post(reverse("flights:search"), _post_payload()).content
        self.assertIn('class="offer-card"', results.decode())


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

    def test_partial_provider_failure_keeps_successful_results(self) -> None:
        offer = replace(
            make_offer(),
            source="working",
            data_status=DataStatus.LIVE,
            is_fictional=False,
        )

        class WorkingProvider:
            name = "working"
            display_name = "Working Air"
            data_status = DataStatus.LIVE
            request_cost = 1

            def search(self, query, options, now):  # type: ignore[no-untyped-def]
                return ProviderSearchResult(
                    offers=(offer,),
                    notices=(ProviderNotice(self.name, "Limited inventory."),),
                    requests_made=4,
                )

        class FailedProvider:
            name = "failed"
            display_name = "Failed Air"
            data_status = DataStatus.LIVE
            request_cost = 1

            def search(self, query, options, now):  # type: ignore[no-untyped-def]
                raise RuntimeError("secret upstream detail")

        with mock.patch(
            "flights.services.get_providers",
            return_value=(WorkingProvider(), FailedProvider()),
        ):
            outcome = run_search(make_query(), today=TODAY, now=NOW)
        self.assertEqual(outcome.offers, (offer,))
        self.assertEqual(outcome.requests_made, 5)
        messages = [notice.message for notice in outcome.notices]
        self.assertIn("Limited inventory.", messages)
        self.assertIn("Failed Air is temporarily unavailable.", messages)
        self.assertNotIn("secret upstream detail", " ".join(messages))
