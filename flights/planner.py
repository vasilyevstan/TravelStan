"""Canonical date planning.

Exact mode plans a single offset. Flexible mode plans the canonical
`[0, -1, +1, ... -N, +N]` sequence, capped at 15 offsets before filtering.
Departure and return shift together, one-way stays one-way, and shifts on or
before the injected current date are removed. No Cartesian product, backfill,
retry, or background work happens here.
"""

from __future__ import annotations

import datetime as dt

from .domain import MAX_DATE_OPTIONS, DateOption, SearchMode, SearchQuery


def canonical_offsets(mode: SearchMode, flexibility: int) -> tuple[int, ...]:
    if mode is SearchMode.EXACT or flexibility <= 0:
        return (0,)
    offsets: list[int] = [0]
    for day in range(1, flexibility + 1):
        offsets.append(-day)
        offsets.append(day)
    return tuple(offsets[:MAX_DATE_OPTIONS])


def plan_date_options(query: SearchQuery, today: dt.date) -> tuple[DateOption, ...]:
    options: list[DateOption] = []
    for offset in canonical_offsets(query.mode, query.flexibility):
        departure = query.departure_date + dt.timedelta(days=offset)
        if departure <= today:
            continue
        return_date = (
            query.return_date + dt.timedelta(days=offset)
            if query.return_date is not None
            else None
        )
        options.append(
            DateOption(
                departure_date=departure,
                return_date=return_date,
                offset_days=offset,
            )
        )
    return tuple(options)
