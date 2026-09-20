# Provider research gate

## 2026-09-20 personal-use reassessment

**Status:** `CONDITIONAL_GO` for fail-closed adapters; `synthetic_demo` remains
the default until the user supplies and validates credentials.

The product now permits a named airline or partner booking link and may show a
real fare without a verified purchase URL. Trial and sandbox feeds are allowed
when visibly labeled. This explicitly relaxes the 2026-09-19 requirement that
every result prove an airline-controlled purchase link; it does not relax the
rules for honest data status, baggage proof, credential handling, provider
terms, or source method.

| Candidate | Status | Implementation decision |
| --- | --- | --- |
| Air France–KLM Open Data | `CONDITIONAL_GO` | Implemented behind `AFKL_API_KEY`. Official Offers documentation describes future bookable schedules and total fares; fare baggage stays unknown unless bound in the offer response. |
| Singapore Airlines Flight Search | `CONDITIONAL_GO` | Implemented behind `SINGAPORE_API_KEY`; defaults to `trial` and uses the official native flexible-date request. |
| TUI Flight Offers | `CONDITIONAL_GO` | Implemented behind `TUI_API_KEY`; defaults to `trial`, maps documented luggage/deeplink fields, and uses exact dates for flexible searches. |
| Lufthansa OpenAPI | `BLOCKED` | Registration is on hold, so no new personal account can currently activate it. |
| Transavia | `BLOCKED` | Public evidence is from a 2018 sample and the current portal/schema could not be verified. |
| Turkish Airlines | `BLOCKED` | An application review is required and public quota, response, and link details remain insufficient. |
| Skyscanner | `BLOCKED` | Partnership review and booking-generation expectations do not provide a self-service personal free tier. |
| Travelpayouts Search API | `NO_GO` | Its rules prohibit combining its results with other metasearch APIs and impose booking conversion requirements. |
| SerpApi / scraped sources | `NO_GO` | The project continues to reject API-wrapped scraping. |

Current first-party evidence:

- [Air France–KLM Offers API](https://klmprod.mashery.com/docs/opendata/offers/)
  and [API-key setup](https://klmprod.mashery.com/docs/read/opendata/Get_Started)
- [Singapore Airlines Flight Search](https://developer.singaporeair.com/docs/flight_search/flightavailability)
- [TUI Flight Offers](https://developer.tui/api-catalog/flight-offers/api-description)
- [Lufthansa registration hold](https://developer.lufthansa.com/)
- [Skyscanner authentication](https://developers.skyscanner.net/docs/getting-started/authentication)
  and [usage guidelines](https://developers.skyscanner.net/docs/getting-started/usage-guidelines)
- [Travelpayouts Search API rules](https://support.travelpayouts.com/hc/en-us/articles/34788165535250-Search-API-usage-rules)

No provider was contacted with a real credential during implementation.
Fixture-tested support is not proof that an account has production access.

## 2026-09-19 baseline decision (historical)

**Status at that time:** `NO_GO` for every live provider under the stricter
airline-direct-link contract.

## Method

Three sealed, independent research passes evaluated the same frozen product
requirements without access to one another's conclusions. A separate synthesis
compared those reports and discarded claims not supported by current
first-party evidence. The passes used distinct available model families:
`gpt-5.4`, `claude-sonnet-5`, and `gemini-3.8-flash`; the Claude research
runtime did not expose a more specific model identifier. The synthesis used
`grok-4.6`. All sources below were accessed on 2026-09-19.

The frozen bar requires a lawful, realistically obtainable source that permits
a custom comparison-only table, supplies current bookable totals and bounded
date searching, preserves required baggage semantics, and proves an
airline-direct seller before that label can be rendered. A missing field or
partner-gated document is not evidence of permission.

## Final provider matrix

| Candidate | Status | Decision |
| --- | --- | --- |
| Travelpayouts White Label | `NO_GO` | Hosted/widget model and agency/brand redirects do not provide a custom table or proven airline-direct seller. |
| Travelpayouts Flight Search API | `NO_GO` | Its user-initiated, full-result, Book-conversion, no-combination rules conflict with comparison-only use; links may be agency or airline and published baggage fields are insufficiently granular. |
| Travelpayouts Data API | `NO_GO` | Seven-day cached search history is not a current bookable quote. |
| Skyscanner Flights Live Prices | `NO_GO` | Partner booking-generation requirement, no guaranteed airline-direct seller, and partner-gated baggage attributes do not meet the frozen bar. |
| Skyscanner indicative products/widgets | `NO_GO` | Indicative/hosted products are not a lawful live custom offer table. |
| Lufthansa Group Partner Offers | `CONDITIONAL` | Official airline-domain deeplinks and total fares exist only after partner registration and for Lufthansa Group inventory; production terms and four-way baggage proof remain incomplete. Not enabled. |
| Duffel | `NO_GO` | Offer-to-order flow, metasearch-unfit look-to-book terms, and no airline-direct purchase URL conflict with a comparison-only product. |
| Amadeus | `NO_GO` | No current free self-service path or native proven airline-direct consumer URL for this use case. |
| Google Flights partner access | `NO_GO` | NDA and invite-only, not a public comparison API. |
| Kiwi/Tequila | `NO_GO` | New partnerships are invitation-only and no qualifying public self-service documentation was found. |
| Direct airline NDC programs | `NO_GO` | Per-carrier commercial/onboarding contracts are not a broadly obtainable free comparison source. |
| US DOT datasets and flight-status APIs | control only | Historical/status data does not provide current bookable inventory or seller links. |

## First-party evidence

- [Travelpayouts White Label](https://support.travelpayouts.com/hc/en-us/articles/203955753-What-is-White-Label-Web-by-Travelpayouts):
  booking completes on an external agency or brand site.
- [Travelpayouts Flight Search usage rules](https://support.travelpayouts.com/hc/en-us/articles/34788165535250-Search-API-usage-rules)
  and [API guide](https://support.travelpayouts.com/hc/en-us/articles/30565016140434-Aviasales-Flight-Search-API-real-time-and-multi-city-search):
  user-initiated/full-display/Book rules, conversion floors, server-side
  headers, 15-minute link validity, and agency-or-airline destination.
- [Travelpayouts Data API](https://support.travelpayouts.com/hc/en-us/articles/203956163-Aviasales-Data-API):
  cache-based data retained for seven days.
- [Skyscanner authentication](https://developers.skyscanner.net/docs/getting-started/authentication),
  [FAQ](https://developers.skyscanner.net/docs/faqs), and
  [Live Prices overview](https://developers.skyscanner.net/docs/flights-live-prices/overview):
  partnership application, booking-generation requirement, booking deeplinks,
  and gated/deprecated baggage attributes.
- [Lufthansa product plans](https://developer.lufthansa.com/product),
  [Partner APIs](https://developer.lufthansa.com/partner_apis),
  [fare response](https://developer.lufthansa.com/docs/api_partner/offers/Fare_Response),
  and [shopping deeplinks](https://developer.lufthansa.com/docs/read/api_partner/customer_deeplinks/Shopping_Links_Search):
  Partner registration, fare/tax fields, and named airline-domain links.
- [Duffel flight guide](https://duffel.com/docs/guides/getting-started-with-flights),
  [extra bags](https://duffel.com/docs/guides/adding-extra-bags), and
  [look-to-book limit](https://help.duffel.com/hc/en-gb/articles/360019684099-Is-there-any-limit-to-how-many-searches-I-can-make):
  booking/order model and comparison-search limitation.
- [Google Flights partner access](https://developers.google.com/travel/flights):
  NDA, invite-only integration.
- [Kiwi partnership update](https://media.kiwi.com/articles-and-interviews/better-for-business-kiwi-com-takes-a-new-approach-to-partnerships/):
  invitation-only new partnerships.

## Rejected claims and unresolved gaps

The synthesis rejected numeric Travelpayouts/Skyscanner audience thresholds,
Skyscanner 10-minute TTL and airline-agent flag claims, Lufthansa four-way
baggage claims, an Amadeus self-service decommission date, and Kiwi total
shutdown claims because current first-party confirmation was absent or
conflicted. Partner-gated production terms, schemas, quotas, retention, and
flexible-date permissions remain unresolved; they are not approval.

## Recommendation

No lawful free provider currently supports the required custom table and
proven airline-direct links. The closest partial option, Lufthansa Group, is
not a `GO` and must remain disabled. The initial release uses the deterministic
and visibly labelled `synthetic_demo` provider only. It sends no user data to
a provider, makes no network request, and must not imply real prices, booking,
or airline-direct purchase.

The sealed reports and synthesis receipts are retained in
[`docs/provider-research-passes/`](provider-research-passes/).

## Private low-volume SerpApi reassessment

**Reassessment date:** 2026-09-19
**Scenario:** one local user, not publicly deployed, fewer than 20 submitted
searches per month.

Three new sealed passes used requested advanced model families
`gpt-6-astra`, `claude-opus-5`, and `grok-4.6`; a separate synthesis used
`gpt-5.6-terra`. Runtime model identity was not independently verifiable for
every pass, so model names are execution receipts rather than evidence.

### Decision

SerpApi Google Flights remains `NO_GO` under the unchanged requirements.
SerpApi explicitly describes the product as scraping Google Flights. Private
use and low volume improve affordability but do not satisfy the original
prohibition on scraping services.

SerpApi is at most `CONDITIONAL` for a deliberately revised personal
experiment. That would require explicit acceptance of a scraping intermediary,
removal of unproved checked-bag filtering and airline-direct claims, provider
retention disclosure, strict call caps, and a new architecture/review gate.

### Resolved facts

- [SerpApi Google Flights](https://serpapi.com/google-flights-api) describes
  its product as scraping Google Flights.
- [Pricing](https://serpapi.com/pricing) currently lists a free allowance of
  250 successful searches per month and 50 per hour.
- Parameter-identical results can be cached for one hour. The
  [Search Archive API](https://serpapi.com/search-archive-api) can retain
  completed search output for up to 31 days.
- [ZeroTrace](https://serpapi.com/zero-trace-mode) is not available on the
  free plan.
- The `bags` parameter concerns carry-on bags, not checked bags. Checked-bag
  evidence in documented responses is free text and cannot safely drive
  TravelStan's proof-required checked-bag filter.
- [Booking options](https://serpapi.com/google-flights-booking-options) can
  identify a reported seller, but documented actions use Google redirects,
  POST data, or telephone booking. They are not proved airline-controlled
  purchase URLs.

### Realistic call budget

Assuming 20 round-trip user searches, no cache benefit, current paired-date
planning, and booking-option enrichment for ten displayed rows:

| Mode | Estimated monthly calls | Free 250 |
| --- | ---: | --- |
| Exact | 240 | Fits narrowly |
| Flexible ±1 | 320 | Does not fit |
| Flexible ±7 | 800 | Does not fit |

Exact one-way searches with ten enrichments use approximately 220 calls per
month. These estimates leave little or no capacity for testing, failures, or
additional alternatives.

### Minimum changes for a personal experiment

1. Explicitly waive the no-scraping-services rule for SerpApi.
2. Disable live `checked_required` unless structured fare-specific proof is
   available; free text remains `unknown`.
3. Do not label Google redirects, phone numbers, or `airline: true` metadata
   as airline-direct purchase links.
4. Disclose that route/date/cabin inputs leave the device and that normal
   provider cache/archive retention applies.
5. Keep failures explicit and never fall back to synthetic offers.
6. Keep the API key server-side and out of URLs, HTML, logs, screenshots, and
   the repository.
7. Default to exact dates and enforce monthly/hourly call budgets.

No SerpApi credential or implementation is authorized by this reassessment.
