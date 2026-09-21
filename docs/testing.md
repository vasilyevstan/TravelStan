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
| `flights/tests/test_forms.py` | Direct upper-case IATA codes, selected city airport sets, individual-airport selection, overlap rejection, strictly future dates, one-way normalization, exact/flexible modes, cabin/luggage choices, single adult, and generic redacted messages. |
| `flights/tests/test_locations.py` | Mocked SerpApi autocomplete parameters, KGMID all-airports and individual-airport normalization, rail exclusion, endpoint allowlisting, process/minute budgets, deduplication, short-query zero-call behavior, provider-cache eligibility, and redacted errors. |
| `flights/tests/test_planner.py` | Exact offset `[0]`, canonical flexible `[0, -1, +1, ...]`, the 15-option pre-filter cap, joint departure/return shifting, one-way preservation, removal of shifts on or before the current date, and no Cartesian product or backfill. |
| `flights/tests/test_results.py` | Four-slot baggage, checked-required filtering, ancillary/weight identity, sort-before-dedupe, and the ten-card cap. |
| `flights/tests/test_provider.py` | Synthetic determinism, no-network operation, SerpApi registry configuration, key requirements, synthetic/external separation, and rejection of unverified direct adapters. |
| `flights/tests/test_provider_adapters.py` | Offline prototype fixtures for AF–KLM, Singapore, and TUI. Passing fixtures do not establish compatibility with current official schemas. |
| `flights/tests/test_serpapi.py` | Mocked exact and `±1` flows, city airport-set routing, request caps, route integrity, unknown baggage, omitted booking links, zero-call limitations, and secret-safe errors. |
| `flights/tests/test_views.py` | Search and location-lookup CSRF, honest source labelling, normalized location JSON, city labels, accessible offer cards, redacted failures, and no persistence/session/cache/log capture. |
| `flights/tests/test_presentation.py` | Lightweight responsive CSS, stable advanced-options layout, accessible location combobox markup, viewport metadata, result assembly, and zero database queries per search. |

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

SerpApi CI tests use `httpx.MockTransport`; no API key or live Google Flights
request is permitted.
