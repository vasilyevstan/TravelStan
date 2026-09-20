"""Baggage filtering, dedupe, sort, and ten-row cap."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from django.test import SimpleTestCase

from flights.domain import BaggageAllowance, BaggageSlot, BaggageState, LuggageChoice
from flights.results import build_results, deduplicate, sort_offers

from .factories import make_baggage, make_offer, make_query


class ResultsTests(SimpleTestCase):
    def test_checked_required_keeps_only_known_positive_included(self) -> None:
        offers = (
            make_offer("a", baggage=make_baggage(BaggageState.INCLUDED, 1)),
            make_offer("b", baggage=make_baggage(BaggageState.INCLUDED, 0)),
            make_offer("c", baggage=make_baggage(BaggageState.INCLUDED, None)),
            make_offer("d", baggage=make_baggage(BaggageState.UNKNOWN, None)),
            make_offer("e", baggage=make_baggage(BaggageState.NOT_INCLUDED, None)),
        )
        query = make_query(luggage=LuggageChoice.CHECKED_REQUIRED)
        kept = [offer.offer_id for offer in build_results(offers, query)]
        self.assertEqual(kept, ["a"])

    def test_no_checked_requirement_preserves_all_offers(self) -> None:
        offers = (
            make_offer(
                "a", amount="100.00", baggage=make_baggage(BaggageState.UNKNOWN, None)
            ),
            make_offer(
                "b", amount="110.00", baggage=make_baggage(BaggageState.NOT_INCLUDED)
            ),
            make_offer("c", amount="120.00", flight_number="ZQ1002"),
        )
        query = make_query(luggage=LuggageChoice.NO_CHECKED_REQUIREMENT)
        self.assertEqual(len(build_results(offers, query)), 3)

    def test_unknown_baggage_is_never_inferred(self) -> None:
        allowance = make_baggage(BaggageState.UNKNOWN, None).checked_bag
        self.assertFalse(allowance.has_known_positive_quantity)
        self.assertIsNone(allowance.quantity)

    def test_dedupe_is_first_wins_on_full_identity(self) -> None:
        first = make_offer("first")
        duplicate = make_offer("second")
        distinct = make_offer("third", flight_number="ZQ2002")
        unique = deduplicate((first, duplicate, distinct))
        self.assertEqual([offer.offer_id for offer in unique], ["first", "third"])

    def test_build_results_sorts_before_first_wins_dedupe(self) -> None:
        later_sort_key = make_offer("z-last")
        earlier_sort_key = make_offer("a-first")
        results = build_results((later_sort_key, earlier_sort_key), make_query())
        self.assertEqual([offer.offer_id for offer in results], ["a-first"])

    def test_binding_ancillary_and_weight_participate_in_identity(self) -> None:
        base = make_offer("base")
        priced_extra = BaggageAllowance(
            slot=BaggageSlot.EXTRA_PAID_BAG,
            state=BaggageState.NOT_INCLUDED,
            quantity=1,
            price_amount=Decimal("35.00"),
            price_currency="EUR",
            price_is_binding=True,
            price_scope="per bag",
            weight_amount=Decimal("23"),
            weight_unit="kg",
        )
        changed_extra = replace(priced_extra, price_amount=Decimal("45.00"))
        first = replace(
            base,
            baggage=replace(base.baggage, extra_paid_bag=priced_extra),
        )
        second = replace(
            base,
            offer_id="other",
            baggage=replace(base.baggage, extra_paid_bag=changed_extra),
        )
        self.assertNotEqual(first.identity(), second.identity())
        self.assertEqual(priced_extra.weight_label, "23 kg")

    def test_sort_by_amount_currency_duration_then_offer_id(self) -> None:
        offers = (
            make_offer("z", amount="120.00", minutes=100, flight_number="ZQ1"),
            make_offer("a", amount="120.00", minutes=100, flight_number="ZQ2"),
            make_offer("b", amount="120.00", minutes=90, flight_number="ZQ3"),
            make_offer("c", amount="99.00", minutes=500, flight_number="ZQ4"),
            make_offer(
                "d", amount="120.00", currency="AUD", minutes=100, flight_number="ZQ5"
            ),
        )
        order = [offer.offer_id for offer in sort_offers(offers)]
        self.assertEqual(order, ["c", "d", "b", "a", "z"])

    def test_results_capped_at_ten_rows(self) -> None:
        offers = tuple(
            make_offer(
                f"offer-{index:02d}",
                amount=f"{100 + index}.00",
                flight_number=f"ZQ{index}",
            )
            for index in range(25)
        )
        results = build_results(offers, make_query())
        self.assertEqual(len(results), 10)
        self.assertEqual(results[0].offer_id, "offer-00")

    def test_pipeline_is_deterministic(self) -> None:
        offers = tuple(
            make_offer(f"offer-{index}", amount="150.00", flight_number=f"ZQ{index}")
            for index in range(12)
        )
        query = make_query()
        self.assertEqual(build_results(offers, query), build_results(offers, query))
