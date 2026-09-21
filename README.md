# TravelStan

TravelStan is a small, server-rendered Django application for comparing flight
offers. It does not sell tickets, take payment, issue tickets, or service a
booking.

## Current status

The default configuration uses deterministic fictional data and performs no
network requests. A constrained personal-use adapter for SerpApi Google
Flights can be selected explicitly with a server-side API key.

SerpApi is an **experimental scraping intermediary**, not an airline or
licensed Google Flights partner API. It is included because direct-airline
APIs expose carrier-specific slices rather than the broad comparison coverage
TravelStan needs. Air France–KLM, Singapore, and TUI prototype adapters remain
in the source tree for fixture research but are not runtime-selectable.

## Development

Requirements: Python 3.13, Django 5.2, and `httpx`. Search uses server-rendered
templates, vanilla CSS, and a small optional vanilla-JavaScript city/airport
combobox. Direct three-letter airport codes continue to work without
JavaScript. SQLite is configured by Django but search does not read or write
it.

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

# Experimental broad comparison
export TRAVELSTAN_PROVIDERS=serpapi
export SERPAPI_API_KEY='...'
```

See [`.env.example`](.env.example) for all non-secret settings. TravelStan does
not load `.env` files itself; export variables through the shell or process
manager. `manage.py check` rejects unknown providers, a missing SerpApi key, and mixed
synthetic/external configuration.

The SerpApi experiment:

- accepts direct IATA codes or provider-backed city/airport suggestions;
- lets a city search choose all returned city airports or one specific airport;
- supports Economy, Economy+ / Premium Economy, and Business;
- supports exact dates and at most a `±1` joint date window;
- makes at most six upstream requests per submitted search;
- sends `no_cache=true` for fresh retrieval;
- does not request booking options or render purchase links;
- keeps all baggage categories `unknown`; and
- refuses checked-bag-required and All classes searches without making a
  provider request.

Synthetic data is never used as fallback after a SerpApi failure.

## Privacy and booking links

Location text, selected airport codes, dates, cabin, passenger count, market,
and currency are sent to SerpApi, which uses them to scrape Google Flights.
The city/airport combobox waits for two characters, debounces requests, cancels
superseded lookups, reuses results only in page memory, and allows at most 12
lookup calls per loaded page. SerpApi documents ordinary search archive access
for up to 31 days; its free plan does not include ZeroTrace. TravelStan stores
no queries, responses, IP addresses, or results in its own database, cache,
session, or application logs.

No booking link is rendered by this experiment. Missing baggage fields remain
`unknown`; SerpApi's `bags` parameter means carry-on and is not used as proof
that checked baggage is included.

See [provider research](docs/provider-research.md),
[architecture](docs/architecture.md), and [operations](docs/operations.md) for
the evidence, boundaries, and activation procedure.
