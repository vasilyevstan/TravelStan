# Testing

Tests and CI use deterministic synthetic and provider-response fixtures. They
must not make real provider calls or require provider credentials.

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
| `flights/tests/test_results.py` | Four-slot baggage, checked-required filtering, ancillary/weight identity, sort-before-dedupe, and the ten-card cap. |
| `flights/tests/test_provider.py` | Synthetic determinism, no-network operation, provider registry configuration, key requirements, and synthetic/live separation. |
| `flights/tests/test_provider_adapters.py` | Mocked AF–KLM, Singapore, and TUI request/response contracts, one-call budgets, status labels, safe links, baggage mapping, and no retry. |
| `flights/tests/test_views.py` | POST/CSRF flow, honest source labelling, accessible offer cards, redacted failures, no-JavaScript rendering, and no persistence/session/cache/log capture. |
| `flights/tests/test_presentation.py` | Light responsive card CSS, viewport metadata, service-level result assembly, and zero database queries per search. |

Time is injected (`flights/clock.py`, `SearchForm(today=...)`,
`views.search(today_provider=..., now_provider=...)`), so no test depends on
the wall clock.

## Provider regression rules

Regression tests prove:

- a separately paid extra bag is not labelled as included in the displayed
  fare;
- baggage weight and unit survive normalized provider mapping;
- binding ancillary amount, currency, and scope participate in offer identity;
- offers are sorted before first-wins deduplication; and
- user-facing cabin wording remains `Economy+ / Premium Economy` while the
  normalized value remains `premium_economy`.

Provider-adapter tests count actual upstream calls for return-leg selection and
flexible-date handling. Submitted form count is not a valid quota proxy.
