# Architecture

## Accepted contract

**Revised:** 2026-09-20

TravelStan is a Python 3.13/Django 5.2 modular monolith with server-rendered
templates, vanilla CSS, and no required JavaScript. The default
`synthetic_demo` mode is deterministic and offline. External providers are
explicitly selected through configuration; synthetic and external results can
never be mixed or used as fallback for one another.

## Search and provider boundary

- One adult; upper-case three-character IATA airport codes; one-way or return.
- Exact dates or joint outbound/return flexibility of one to seven days.
- Economy, Economy+ / Premium Economy, Business, or all supported classes.
- An explicit checked-bag requirement keeps only offers with a known positive,
  fare-bound included allowance.
- `FlightProvider.search()` returns normalized offers, safe provider notices,
  and the upstream request count. Raw payloads never reach templates.
- Air France–KLM and Singapore use one native bounded-date request. TUI uses
  the exact requested dates and emits a limitation notice. Every adapter makes
  at most one request, uses an eight-second timeout, and performs no retry.
- Multiple external providers run concurrently. A partial failure is reported
  generically while successful results remain available; total failure returns
  one redacted error.

## Normalized results

Every offer records source, `live`/`trial`/`sandbox`/`synthetic` status,
retrieval and expiry times, complete segment identity, fare total, seller, and
an optional validated purchase URL. HTTPS URLs must belong to the source
adapter's explicit airline-domain allowlist. An offer without a safe URL is
shown with booking unavailable.

Baggage separates personal item, carry-on, checked bag, and extra paid bag.
Each retains `included`, `not_included`, or `unknown`, plus supplied quantity,
weight/unit, and binding ancillary price/scope. A purchasable extra bag is not
part of the fare. Missing data is never reconstructed from cabin, fare family,
or route policy.

Results are filtered, sorted by total amount/currency/duration/offer ID,
first-wins deduplicated on full itinerary/fare/baggage identity, and capped at
ten cards.

## Privacy, security, and UI

Search values and provider data are never written to the database, cache,
session, or logs. Credentials are server-side environment variables and travel
only in provider authentication headers. CSRF, template autoescaping, redacted
errors, URL allowlists, response-size bounds, and safe external-link attributes
remain enforced.

The interface uses a light editorial layout, native labelled controls, a
compact advanced-options disclosure, accessible errors and status messages,
and responsive offer cards down to 320px. It works without JavaScript.

Tests and CI use deterministic fixtures and `httpx.MockTransport`; they never
contact provider endpoints or require credentials.
