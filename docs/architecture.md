# Architecture

## Accepted contract

**Revised:** 2026-09-20

TravelStan is a Python 3.13/Django 5.2 modular monolith with server-rendered
templates, vanilla CSS, and a small progressive-enhancement script for
provider-backed city/airport selection. Direct IATA entry and the complete
search flow remain server-rendered. The default `synthetic_demo` mode is
deterministic and offline. The only selectable external provider is the
explicitly approved personal SerpApi experiment. Synthetic and external
results can never be mixed or used as fallback for one another.

## Search and provider boundary

- One adult; direct upper-case three-character IATA codes or a selected
  SerpApi city/airport suggestion; one-way or return.
- A city suggestion expands to the returned IATA airport set. The user may
  search that complete set or select one listed airport. Overlapping origin
  and destination sets are rejected.
- Exact dates or joint outbound/return flexibility of one to seven days.
- Economy, Economy+ / Premium Economy, Business, or all supported classes.
- An explicit checked-bag requirement keeps only offers with a known positive,
  fare-bound included allowance.
- `FlightProvider.search()` returns normalized offers, safe provider notices,
  and the actual upstream request count. Raw payloads never reach templates.
- SerpApi exact one-way search uses one request. Exact round-trip follows at
  most three outbound branches for a maximum of four requests. Flexible mode
  is limited to `±1` joint date shifts and follows one outbound branch per date
  pair, for a maximum of six requests.
- All classes, flexibility above `±1`, and checked-bag-required requests fail
  closed with a clear provider notice and zero upstream calls.
- The adapter requests fresh data with `no_cache=true`, performs no retry, and
  does not retrieve booking options. A provider failure returns one redacted
  error and never synthetic data.

## Normalized results

Every offer records source,
`live`/`experimental`/`trial`/`sandbox`/`synthetic` status,
retrieval and expiry times, complete segment identity, fare total, seller, and
an optional validated purchase URL. The SerpApi experiment deliberately supplies no purchase URL because its
documented booking actions are Google/intermediary redirects rather than
proved airline-controlled URLs.

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
session, or logs. Credentials remain in server-side environment variables.
SerpApi requires its key in an HTTPS query parameter, so TravelStan never logs
provider URLs and suppresses HTTP exception causes that could retain them.
Other adapters use provider authentication headers. CSRF, template
autoescaping, redacted errors, URL allowlists, response-size bounds, and safe
external-link attributes remain enforced.

The location lookup is a CSRF-protected POST so location text is not placed in
application URLs. It requires two characters, returns at most ten normalized
options, and relies on SerpApi's one-hour provider cache rather than retaining
queries locally. The browser debounces requests, cancels superseded work,
keeps only page-memory results, and caps each loaded page at 12 lookups.

The interface uses a lightweight dark layout, native labelled controls, an
advanced-options disclosure whose position does not change when expanded,
accessible combobox keyboard controls and status messages, and responsive
offer cards down to 320px. Without JavaScript, direct IATA entry remains
available.

Tests and CI use deterministic fixtures and `httpx.MockTransport`; they never
contact provider endpoints or require credentials.

The AF–KLM, Singapore, and TUI files are retained only as offline research
prototypes. They are excluded from the runtime registry after first-party
schema review found unresolved or confirmed mapping and workflow mismatches.
