# TravelStan

TravelStan is a small, server-rendered Django application for comparing flight
offers. It does not sell tickets, take payment, issue tickets, or service a
booking.

## Current status

The default configuration uses deterministic fictional data and performs no
network requests. Optional adapters are implemented for Air France–KLM Open
Data, Singapore Airlines Flight Search, and TUI Flight Offers. Each external
adapter remains disabled until it is explicitly selected and supplied with a
developer key.

The adapters have fixture-based contract coverage but have not been certified
against this installation with real credentials. Treat an adapter as trial
until its account, endpoint, response shape, quota, and booking link have been
verified with one real request.

## Development

Requirements: Python 3.13, Django 5.2, and `httpx`. Search uses server-rendered
templates and vanilla CSS; JavaScript is not required. SQLite is configured by
Django but search does not read or write it.

```bash
python3.13 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt

.venv/bin/ruff format --check .
.venv/bin/ruff check .
.venv/bin/python manage.py check
.venv/bin/python manage.py test
.venv/bin/python manage.py runserver
```

## Provider configuration

`TRAVELSTAN_PROVIDERS` is a comma-separated list. Synthetic results cannot be
mixed with external results.

```bash
# Credential-free default
export TRAVELSTAN_PROVIDERS=synthetic_demo

# External sources
export TRAVELSTAN_PROVIDERS=afkl,singapore,tui
export AFKL_API_KEY='...'
export SINGAPORE_API_KEY='...'
export TUI_API_KEY='...'
```

See [`.env.example`](.env.example) for all non-secret settings. TravelStan does
not load `.env` files itself; export variables through the shell or process
manager. `manage.py check` rejects unknown providers, missing selected-provider
keys, invalid data-status values, and mixed synthetic/external configuration.

| Provider | Default label | Flexible-date behavior | Notes |
| --- | --- | --- | --- |
| Air France–KLM | Trial | One interval request | Set `AFKL_DATA_STATUS=live` only after a production response is confirmed. Fare-bound baggage otherwise remains unknown. |
| Singapore Airlines | Trial | One native flexible request | Set `SINGAPORE_DATA_STATUS=live` only after production access is confirmed. |
| TUI | Trial | Exact requested dates | TUI currently returns GBP and primarily covers its own leisure inventory. |

Each configured provider makes at most one upstream request per submitted
search. Providers run concurrently, a partial failure does not discard other
results, and no adapter retries automatically. Synthetic data is never used as
a fallback for a failed external source.

## Privacy and booking links

Routes, dates, cabin, and passenger count are sent to each configured external
provider. TravelStan stores no queries, responses, IP addresses, or results in
the database, cache, session, or application logs.

Only HTTPS booking links on an adapter's allowlisted airline domains are
rendered. A real offer remains visible when no verified link is available.
Missing baggage fields remain `unknown`; route-level policy text is never
presented as proof that a fare includes a bag.

See [provider research](docs/provider-research.md),
[architecture](docs/architecture.md), and [operations](docs/operations.md) for
the evidence, boundaries, and activation procedure.
