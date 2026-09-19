"""Canonical planning contract."""

from __future__ import annotations

import datetime as dt

from django.test import SimpleTestCase

from flights.domain import MAX_DATE_OPTIONS, SearchMode
from flights.planner import canonical_offsets, plan_date_options

from .factories import TODAY, make_query


class PlannerTests(SimpleTestCase):
    def test_exact_mode_uses_single_offset(self) -> None:
        self.assertEqual(canonical_offsets(SearchMode.EXACT, 0), (0,))
        self.assertEqual(canonical_offsets(SearchMode.EXACT, 5), (0,))

    def test_flexible_offsets_are_canonically_ordered(self) -> None:
        self.assertEqual(canonical_offsets(SearchMode.FLEXIBLE, 1), (0, -1, 1))
        self.assertEqual(
            canonical_offsets(SearchMode.FLEXIBLE, 3), (0, -1, 1, -2, 2, -3, 3)
        )

    def test_flexible_offsets_capped_at_fifteen(self) -> None:
        offsets = canonical_offsets(SearchMode.FLEXIBLE, 7)
        self.assertEqual(len(offsets), MAX_DATE_OPTIONS)
        self.assertEqual(offsets[0], 0)
        self.assertEqual(offsets[-1], 7)

    def test_exact_plan_is_one_option(self) -> None:
        query = make_query()
        options = plan_date_options(query, TODAY)
        self.assertEqual(len(options), 1)
        self.assertEqual(options[0].departure_date, query.departure_date)
        self.assertIsNone(options[0].return_date)

    def test_one_way_stays_one_way(self) -> None:
        query = make_query(mode=SearchMode.FLEXIBLE, flexibility=3)
        for option in plan_date_options(query, TODAY):
            self.assertIsNone(option.return_date)

    def test_departure_and_return_shift_together(self) -> None:
        query = make_query(
            mode=SearchMode.FLEXIBLE,
            flexibility=2,
            return_date=dt.date(2026, 10, 8),
        )
        for option in plan_date_options(query, TODAY):
            delta = option.departure_date - query.departure_date
            self.assertEqual(option.return_date - query.return_date, delta)
            self.assertGreater(option.return_date, option.departure_date)

    def test_no_cartesian_product(self) -> None:
        query = make_query(
            mode=SearchMode.FLEXIBLE,
            flexibility=7,
            return_date=dt.date(2026, 10, 8),
        )
        options = plan_date_options(query, TODAY)
        self.assertEqual(len(options), MAX_DATE_OPTIONS)

    def test_shifts_on_or_before_today_are_dropped_without_backfill(self) -> None:
        query = make_query(
            departure_date=TODAY + dt.timedelta(days=2),
            mode=SearchMode.FLEXIBLE,
            flexibility=3,
        )
        options = plan_date_options(query, TODAY)
        departures = [option.departure_date for option in options]
        self.assertTrue(all(day > TODAY for day in departures))
        # 0, -1, +1, -2(dropped: == today), +2, -3(dropped), +3
        self.assertEqual(len(options), 5)

    def test_plan_preserves_canonical_order(self) -> None:
        query = make_query(mode=SearchMode.FLEXIBLE, flexibility=2)
        offsets = [option.offset_days for option in plan_date_options(query, TODAY)]
        self.assertEqual(offsets, [0, -1, 1, -2, 2])
