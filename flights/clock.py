"""Injectable clock.

Views and forms never call `date.today()` directly, so tests can inject a
deterministic current date without patching global state.
"""

from __future__ import annotations

import datetime as dt


def current_datetime() -> dt.datetime:
    return dt.datetime.now(tz=dt.UTC)


def current_date() -> dt.date:
    return current_datetime().date()
