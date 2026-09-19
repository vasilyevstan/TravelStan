# Architecture

## Accepted contract

**Accepted:** 2026-09-19
**Architecture base:** `4fe61bdec12ffd6c6a5dc5c77fa79564fae372bc`
**Validation:** three sealed model-family passes and separate synthesis:
`gpt-5.4`, `claude-sonnet-5`, `gemini-3.8-flash`, then `grok-4.6`.
The synthesis is `SIMPLIFICATION_READY`.

TravelStan is a Python 3.13/Django 5.2 modular monolith with server-rendered
templates, SQLite for local development, vanilla CSS, and optional minimal
vanilla JavaScript. It is a deterministic, in-process, no-network
`synthetic_demo` release only. No setting, credential, registry hook, or
fallback enables live providers. A live activation requires fresh first-party
`GO` evidence plus renewed architecture and implementation review.

## Request and planning contract

- One adult only; no passenger, child, or infant controls.
- Origin and destination are distinct upper-case IATA codes matching
  `^[A-Z]{3}$`; no city lookup is claimed.
- Departure is strictly after the injected current date. A blank return form
  value normalizes to `None` and means one-way; a supplied return is strictly
  after departure.
- Cabin choices are Economy, Premium Economy, Business, and All classes.
  `all_classes` means no cabin filter.
- Exact mode has flexibility `0` and offset `[0]`. Flexible mode is `1..7`
  with offsets `[0, -1, +1, ... -N, +N]`, at most 15 before filtering.
  Departure and return shift together; one-way preserves `None`; shifts on or
  before the injected current date are removed. No Cartesian product,
  backfill, retries, or background work is permitted.

## Provider and result contract

Only the synthetic provider implements the normalized provider protocol.
Templates receive normalized offers, never fixture/raw-provider payloads.
Searches, results, query values, IP addresses, and provider data are never
stored in the database, cache, session, or logs.

Every offer separates `personal_item`, `carry_on`, `checked_bag`, and
`extra_paid_bag`. Each has `included`, `not_included`, or `unknown`; missing
data is never inferred. Checked-bag-required results retain only offers with a
known positive included checked allowance. Extra-bag price is shown only if it
is binding and exact.

Results use a stable full-itinerary/baggage/price identity, sort by total
amount, currency, combined duration, and offer ID, deduplicate first-wins,
and display no more than ten rows. The table shows carrier and operating
carrier where different, route/schedule/duration/stops, cabin/fare brand, all
four baggage states, price/currency, source/freshness, and seller/purchase
state. Demo offers have no seller, URL, or clickable purchase action and are
persistently labelled fictional, non-live, and non-bookable.

## Security, accessibility, and quality

Form errors and provider failures are generic and redacted. CSRF and template
autoescaping remain enabled. The interface uses labelled native controls,
fieldsets, accessible errors and alert summary, semantic table/caption/headers,
visible focus, textual status, a 320px card/stacked layout, and works without
JavaScript.

CI must run Python 3.13 Django tests, lint, format, Django checks, and
synthetic-only/no-network verification, alongside governance checks. Work
flows feature branch → `dev` PR → `master` release PR.
