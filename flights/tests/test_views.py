"""End-to-end server-rendered view contract."""

from __future__ import annotations

import datetime as dt
import logging
import socket
from dataclasses import replace
from unittest import mock

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from flights import views
from flights.domain import DataStatus
from flights.services import GENERIC_FAILURE, SearchOutcome, SearchUnavailable

from .factories import NOW, TODAY, make_offer


def valid_post(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "origin": "aaa",
        "destination": "BBB",
        "departure_date": "2026-10-01",
        "return_date": "",
        "cabin": "all_classes",
        "mode": "exact",
        "flexibility": "",
        "luggage": "no_checked_requirement",
    }
    data.update(overrides)
    return data


class ViewTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.url = reverse("flights:search")
        patcher_today = mock.patch("flights.views.current_date", return_value=TODAY)
        patcher_now = mock.patch("flights.views.current_datetime", return_value=NOW)
        self.addCleanup(patcher_today.stop)
        self.addCleanup(patcher_now.stop)
        patcher_today.start()
        patcher_now.start()

    def test_get_renders_form_with_csrf_and_post_method(self) -> None:
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('method="post"', content)
        self.assertIn("csrfmiddlewaretoken", content)

    def test_get_shows_fixed_single_adult(self) -> None:
        content = self.client.get(self.url).content.decode()
        self.assertIn("1 adult", content)
        self.assertIn('<details class="advanced" open>', content)

    def test_csrf_is_enforced(self) -> None:
        enforcing = Client(enforce_csrf_checks=True)
        response = enforcing.post(self.url, valid_post())
        self.assertEqual(response.status_code, 403)

    def test_post_renders_demo_results_with_required_labels(self) -> None:
        response = self.client.post(self.url, valid_post())
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("Sample results", content)
        self.assertIn("Prices are generated and cannot be booked", content)
        self.assertIn("Generated itinerary", content)
        self.assertIn("data-badge--synthetic", content)
        self.assertIn("Booking link unavailable", content)

    def test_results_use_compact_offer_cards(self) -> None:
        content = self.client.post(self.url, valid_post()).content.decode()
        self.assertIn('class="offer-card"', content)
        self.assertIn('aria-label="Outbound flight"', content)
        self.assertIn('aria-label="Price and booking"', content)
        self.assertIn("Total for 1 adult", content)
        self.assertIn("Baggage details", content)

    def test_results_show_four_baggage_slots(self) -> None:
        content = self.client.post(self.url, valid_post()).content.decode()
        for label in ("Personal item", "Carry-on bag", "Checked bag", "Extra paid bag"):
            self.assertIn(label, content)

    def test_no_seller_link_or_purchase_cta(self) -> None:
        content = self.client.post(self.url, valid_post()).content.decode()
        self.assertNotIn("http://", content)
        self.assertNotIn("https://", content)
        self.assertNotIn('class="booking-button"', content)

    @override_settings(TRAVELSTAN_PROVIDERS=("afkl",), AFKL_API_KEY="test")
    def test_safe_live_booking_link_is_rendered_as_external_action(self) -> None:
        offer = replace(
            make_offer(),
            source="afkl",
            data_status=DataStatus.LIVE,
            seller_name="Air France–KLM",
            purchase_url="https://www.klm.com/book/test",
            is_bookable=True,
            is_fictional=False,
        )
        outcome = SearchOutcome(
            offers=(offer,),
            retrieved_at=NOW,
            expires_at=offer.expires_at,
            sources=("afkl",),
            notices=(),
            requests_made=1,
        )
        with mock.patch("flights.views.run_search", return_value=outcome):
            content = self.client.post(self.url, valid_post()).content.decode()
        self.assertIn('href="https://www.klm.com/book/test"', content)
        self.assertIn('target="_blank" rel="noopener noreferrer"', content)
        self.assertIn("Continue to Air France–KLM", content)

    def test_results_capped_at_ten_rows(self) -> None:
        response = self.client.post(
            self.url, valid_post(mode="flexible", flexibility="7")
        )
        content = response.content.decode()
        self.assertLessEqual(content.count('<article class="offer-card">'), 10)
        self.assertEqual(len(response.context["offers"]), 10)

    def test_checked_bag_requirement_filters_results(self) -> None:
        response = self.client.post(self.url, valid_post(luggage="checked_required"))
        offers = response.context["offers"]
        self.assertTrue(offers)
        for offer in offers:
            self.assertTrue(offer.baggage.checked_bag.has_known_positive_quantity)

    def test_invalid_submission_shows_generic_redacted_error(self) -> None:
        response = self.client.post(self.url, valid_post(origin="ZZ9"))
        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn('role="alert"', content)
        self.assertIn("Check the highlighted fields and try again.", content)
        self.assertNotIn("ZZ9", str(response.context["form"].errors))
        self.assertIn("Enter a three-letter airport code.", content)
        self.assertIsNone(response.context["outcome"])

    def test_provider_failure_is_redacted(self) -> None:
        with mock.patch(
            "flights.views.run_search", side_effect=SearchUnavailable(GENERIC_FAILURE)
        ):
            response = self.client.post(self.url, valid_post())
        content = response.content.decode()
        self.assertIn(GENERIC_FAILURE, content)
        self.assertNotIn("Traceback", content)

    def test_one_way_and_round_trip_render(self) -> None:
        one_way = self.client.post(self.url, valid_post()).content.decode()
        self.assertNotIn('aria-label="Return flight"', one_way)
        round_trip = self.client.post(
            self.url, valid_post(return_date="2026-10-08")
        ).content.decode()
        self.assertIn('aria-label="Return flight"', round_trip)

    def test_injected_today_controls_departure_validation(self) -> None:
        with mock.patch(
            "flights.views.current_date", return_value=dt.date(2026, 10, 1)
        ):
            response = self.client.post(self.url, valid_post())
        self.assertIn(
            "Departure date must be later than today.", response.content.decode()
        )

    def test_search_does_not_touch_network(self) -> None:
        original_socket = socket.socket
        socket.socket = mock.Mock(side_effect=AssertionError("network attempted"))
        try:
            response = self.client.post(self.url, valid_post())
        finally:
            socket.socket = original_socket
        self.assertEqual(response.status_code, 200)

    def test_accessible_semantics(self) -> None:
        content = self.client.post(self.url, valid_post()).content.decode()
        self.assertIn("<fieldset", content)
        self.assertIn("<legend", content)
        self.assertIn("<article", content)
        self.assertIn('aria-label="Outbound flight"', content)
        self.assertIn('role="status"', content)
        self.assertIn('<html lang="en">', content)
        self.assertIn("<label ", content)

    def test_page_works_without_javascript(self) -> None:
        content = self.client.post(self.url, valid_post()).content.decode()
        self.assertNotIn("<script", content)
        self.assertNotIn("onclick=", content)

    def test_no_search_data_is_logged(self) -> None:
        with self.assertLogs(level=logging.DEBUG) as captured:
            logging.getLogger("flights.probe").debug("probe")
            self.client.post(self.url, valid_post())
        joined = "\n".join(captured.output)
        self.assertNotIn("AAA", joined)
        self.assertNotIn("BBB", joined)

    @override_settings(DEBUG=False)
    def test_templates_autoescape_user_input(self) -> None:
        response = self.client.post(self.url, valid_post(origin="<b>x</b>"))
        content = response.content.decode()
        self.assertNotIn("<b>x</b>", content)


class NoPersistenceTests(TestCase):
    def test_flights_app_defines_no_models(self) -> None:
        from django.apps import apps

        self.assertEqual(list(apps.get_app_config("flights").get_models()), [])

    def test_no_session_or_auth_middleware_persists_search(self) -> None:
        from django.conf import settings

        self.assertNotIn(
            "django.contrib.sessions.middleware.SessionMiddleware", settings.MIDDLEWARE
        )
        self.assertNotIn("django.contrib.sessions", settings.INSTALLED_APPS)

    def test_cache_backend_is_dummy(self) -> None:
        from django.core.cache import cache

        cache.set("probe", "value")
        self.assertIsNone(cache.get("probe"))

    def test_response_sets_no_search_cookie(self) -> None:
        with mock.patch("flights.views.current_date", return_value=TODAY):
            response = Client().post(reverse("flights:search"), valid_post())
        self.assertNotIn("sessionid", response.cookies)


class ViewInjectionTests(TestCase):
    def test_view_accepts_injected_clock_callables(self) -> None:
        from django.test import RequestFactory

        request = RequestFactory().get("/")
        response = views.search(
            request,
            today_provider=lambda: TODAY,
            now_provider=lambda: NOW,
        )
        self.assertEqual(response.status_code, 200)
