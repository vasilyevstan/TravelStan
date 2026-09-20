"""Synthetic provider and fail-closed registry contracts."""

from __future__ import annotations

import datetime as dt
import socket

from django.test import SimpleTestCase, override_settings

from flights.domain import (
    SOURCE_SYNTHETIC_DEMO,
    BaggageState,
    CabinClass,
    DataStatus,
    SearchMode,
)
from flights.planner import plan_date_options
from flights.providers import (
    AirFranceKLMProvider,
    FlightProvider,
    SingaporeAirlinesProvider,
    SyntheticDemoProvider,
    TUIProvider,
    configuration_errors,
    get_providers,
)

from .factories import NOW, TODAY, make_query


class NetworkBlocked(AssertionError):
    pass


def _block(*args: object, **kwargs: object) -> None:
    raise NetworkBlocked("network access attempted")


class SyntheticProviderTests(SimpleTestCase):
    def setUp(self) -> None:
        self.provider = get_providers()[0]

    def _search(self, query):  # type: ignore[no-untyped-def]
        return self.provider.search(query, plan_date_options(query, TODAY), NOW).offers

    def test_provider_implements_normalized_protocol(self) -> None:
        self.assertIsInstance(self.provider, SyntheticDemoProvider)
        self.assertIsInstance(self.provider, FlightProvider)
        self.assertEqual(self.provider.name, SOURCE_SYNTHETIC_DEMO)
        self.assertEqual(self.provider.data_status, DataStatus.SYNTHETIC)

    def test_offers_are_normalized_demo_values(self) -> None:
        offers = self._search(make_query())
        self.assertTrue(offers)
        for offer in offers:
            self.assertEqual(offer.source, SOURCE_SYNTHETIC_DEMO)
            self.assertTrue(offer.is_fictional)
            self.assertFalse(offer.is_bookable)
            self.assertIsNone(offer.seller_name)
            self.assertIsNone(offer.purchase_url)
            self.assertEqual(offer.retrieved_at, NOW)
            self.assertGreater(offer.expires_at, offer.retrieved_at)

    def test_four_baggage_slots_always_present_with_explicit_state(self) -> None:
        for offer in self._search(make_query()):
            rows = offer.baggage.as_rows()
            self.assertEqual(len(rows), 4)
            self.assertEqual(
                [str(row.slot) for row in rows],
                ["personal_item", "carry_on", "checked_bag", "extra_paid_bag"],
            )
            for row in rows:
                self.assertIn(row.state, set(BaggageState))

    def test_extra_bag_price_shown_only_when_binding(self) -> None:
        offers = self._search(make_query())
        for offer in offers:
            extra = offer.baggage.extra_paid_bag
            if extra.price_amount is not None and not extra.price_is_binding:
                self.assertFalse(extra.displays_price)
                self.assertIsNone(extra.price_label)
            if extra.displays_price:
                self.assertIsNot(extra.state, BaggageState.INCLUDED)

    def test_cabin_filter_applies_and_all_classes_does_not(self) -> None:
        economy = self._search(make_query(cabin=CabinClass.ECONOMY))
        self.assertTrue(economy)
        self.assertTrue(all(o.cabin is CabinClass.ECONOMY for o in economy))
        all_classes = self._search(make_query(cabin=CabinClass.ALL_CLASSES))
        self.assertGreater(len({offer.cabin for offer in all_classes}), 1)

    def test_round_trip_offers_include_inbound(self) -> None:
        query = make_query(return_date=dt.date(2026, 10, 8))
        for offer in self._search(query):
            self.assertIsNotNone(offer.inbound)
            self.assertEqual(offer.inbound.origin, query.destination)
            self.assertEqual(offer.inbound.destination, query.origin)

    def test_results_are_deterministic(self) -> None:
        query = make_query(mode=SearchMode.FLEXIBLE, flexibility=3)
        self.assertEqual(self._search(query), self._search(query))

    def test_no_network_access(self) -> None:
        original_socket = socket.socket
        original_create = socket.create_connection
        socket.socket = _block  # type: ignore[assignment]
        socket.create_connection = _block  # type: ignore[assignment]
        try:
            offers = self._search(make_query(mode=SearchMode.FLEXIBLE, flexibility=7))
        finally:
            socket.socket = original_socket  # type: ignore[assignment]
            socket.create_connection = original_create  # type: ignore[assignment]
        self.assertTrue(offers)


class ProviderRegistryTests(SimpleTestCase):
    @override_settings(
        TRAVELSTAN_PROVIDERS=("afkl", "singapore", "tui"),
        AFKL_API_KEY="afkl-test",
        SINGAPORE_API_KEY="sq-test",
        TUI_API_KEY="tui-test",
    )
    def test_all_supported_external_providers_can_be_configured(self) -> None:
        providers = get_providers()
        self.assertEqual(
            [type(provider) for provider in providers],
            [AirFranceKLMProvider, SingaporeAirlinesProvider, TUIProvider],
        )

    @override_settings(
        TRAVELSTAN_PROVIDERS=("synthetic_demo", "afkl"), AFKL_API_KEY="test"
    )
    def test_synthetic_cannot_mix_with_external_results(self) -> None:
        self.assertIn(
            "Synthetic and external providers cannot be enabled together.",
            configuration_errors(),
        )

    @override_settings(TRAVELSTAN_PROVIDERS=("afkl",), AFKL_API_KEY="")
    def test_external_provider_fails_closed_without_key(self) -> None:
        self.assertIn(
            "AFKL_API_KEY is required when afkl is enabled.",
            configuration_errors(),
        )

    @override_settings(TRAVELSTAN_PROVIDERS=("synthetic_demo", "synthetic_demo"))
    def test_duplicate_provider_configuration_is_rejected(self) -> None:
        self.assertIn(
            "TRAVELSTAN_PROVIDERS cannot contain duplicate providers.",
            configuration_errors(),
        )
