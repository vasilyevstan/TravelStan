# Testing

Tests and CI use deterministic synthetic fixtures only. They must not make
real provider calls or require provider credentials.

## Commands

```bash
.venv/bin/python manage.py test          # full Django test suite
.venv/bin/python manage.py test flights.tests.test_planner  # one module
.venv/bin/python manage.py check
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

## Layout

| Module | Contract covered |
| --- | --- |
| `flights/tests/test_forms.py` | Distinct upper-case IATA codes, strictly future departure via the injected current date, blank return normalizing to one-way `None`, strictly later return, exact/flexible modes, flexibility `1..7`, the four cabin choices, the required explicit checked-luggage choice, single adult, and generic redacted messages. |
| `flights/tests/test_planner.py` | Exact offset `[0]`, canonical flexible `[0, -1, +1, ...]`, the 15-option pre-filter cap, joint departure/return shifting, one-way preservation, removal of shifts on or before the current date, and no Cartesian product or backfill. |
| `flights/tests/test_results.py` | Four-slot baggage with explicit state and no inference, checked-required filtering to known positive included allowances, first-wins full-itinerary dedupe, amount/currency/combined-duration/offer-ID sorting, and the ten-row cap. |
| `flights/tests/test_provider.py` | Normalized provider protocol, fictional offers with no seller/URL/bookable action, binding-only extra-bag prices, cabin filtering with `all_classes` as no filter, determinism, and no-network operation (sockets blocked plus a source scan for HTTP clients). |
| `flights/tests/test_views.py` | POST/CSRF flow, demo labelling, price disclaimer, `synthetic_demo` source, frozen table columns with retrieval/expiry, absent purchase links or CTAs, redacted form and provider failures, accessible semantics, no-JavaScript rendering, and no persistence/session/cache/log capture. |
| `flights/tests/test_presentation.py` | Responsive stacked-card CSS for narrow screens, viewport metadata, service-level result assembly, and zero database queries per search. |

Time is injected (`flights/clock.py`, `SearchForm(today=...)`,
`views.search(today_provider=..., now_provider=...)`), so no test depends on
the wall clock.
