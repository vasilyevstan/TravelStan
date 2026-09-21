# Operations

## Offline default

No provider credential or network is required for the default mode:

```bash
export TRAVELSTAN_PROVIDERS=synthetic_demo
.venv/bin/python manage.py check
.venv/bin/python manage.py runserver
```

The search path performs no database or cache writes and uses no session or
authentication middleware.

## Experimental SerpApi provider

Create a SerpApi account separately, then export its key only in the server
process. Never put a populated key in the repository, browser, screenshots, or
chat.

```bash
export TRAVELSTAN_PROVIDERS=serpapi
export SERPAPI_API_KEY='...'
export SERPAPI_CURRENCY=EUR
.venv/bin/python manage.py check --fail-level WARNING
```

`TRAVELSTAN_COUNTRY=EE` and `TRAVELSTAN_LOCALE=en-EE` set the Google market
and language. SerpApi authentication requires its key as an upstream query
parameter; TravelStan never renders or logs the provider URL and removes HTTP
exception causes that could retain it.

## Failure and quota behavior

- One search makes zero upstream calls in synthetic mode.
- City/airport autocomplete uses separate SerpApi requests. It begins after
  two characters, is debounced by 550 ms, cancels superseded requests, reuses
  identical terms in page memory, allows provider caching, and stops after 12
  lookup calls per loaded page. The server additionally rejects lookups after
  20 calls per minute or 100 calls in one process lifetime; restart resets the
  process-lifetime counter.
- SerpApi exact one-way uses one request; exact round-trip uses at most four.
- Flexible mode is limited to `±1`; a round-trip uses at most six requests.
- All classes, checked-bag-required, and wider flexible searches make zero
  requests and return an explicit limitation notice.
- Calls use the shared timeout and no retry. Flexible searches keep successful
  independent date pairs when another pair has a transient provider failure
  and disclose the partial coverage. If every pair fails, the search produces
  one redacted error and never synthetic data.
- `no_cache=true` is sent for fare freshness, so successful flight calls count
  toward the plan. Autocomplete intentionally allows SerpApi's one-hour cache,
  where cached repeats are documented as free. Twenty maximum-budget flight
  searches use at most 120 flight calls, but operators must also account for
  uncached location lookups.
- No persistent monthly quota ledger exists. The browser and process limits
  prevent an accidental request loop but do not replace SerpApi dashboard
  monitoring. Disable automatic early renewal before increasing search scope.

HTTP 401/403 means the key or account is unusable. HTTP 429 means the provider
quota is exhausted. Neither condition is retried automatically.

## Credential validation checklist

Before relying on the experiment:

1. Run `manage.py check` with only `serpapi` selected.
2. Disable automatic early renewal in the SerpApi account.
3. Submit one exact one-way search and one exact round-trip search.
4. Confirm dates, itinerary, requested currency, and passenger scope against
   Google Flights or the eventual seller page.
5. Confirm the account dashboard counted no more than five calls for those two
   searches.
6. Verify that no API key, request URL, or raw provider payload appears in the
   rendered page or application logs.

Disable a provider immediately by removing it from `TRAVELSTAN_PROVIDERS`.
