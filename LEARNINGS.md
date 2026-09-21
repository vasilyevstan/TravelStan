# TravelStan learnings

Only verified TravelStan-specific lessons belong here. Do not copy findings,
data, credentials, source code, or domain rules from other projects.

- The default product mode is the deterministic, visibly synthetic
  `synthetic_demo` provider. A live provider is not activated without a
  documented first-party `GO` decision.
- The 2026-09-19 first-party provider synthesis found no `GO` source for a
  custom comparison-only table with proven airline-direct purchase links.
  Lufthansa Group remains conditional only and is disabled.
- Personal, low-volume use changes provider affordability but does not remove
  source-method, terms, privacy, baggage-proof, or seller-link requirements.
  SerpApi's free quota can cover exact searches only narrowly once return and
  booking-option calls are counted.
- SerpApi's `bags` parameter is carry-on-only; documented checked-bag values
  are free text and must remain unknown rather than drive the checked-required
  filter.
- Provider cost must be calculated from actual upstream calls, not submitted
  forms. Round-trip leg selection, flexible-date expansion, and per-offer
  booking enrichment can turn 20 user searches into hundreds of provider
  requests.
- A paid ancillary is not included in the quoted fare merely because it is
  available. `extra_paid_bag` must preserve fare inclusion separately from an
  exact binding ancillary price.
- Offer equivalence includes binding ancillary amount, currency, and scope.
  Sort deterministically before first-wins deduplication so provider response
  order cannot select a different representative.
- The provider boundary must retain supplied baggage weight and unit. Missing
  weight remains unknown; it is never reconstructed from cabin or fare brand.
- Private use reduces exposure and traffic but is not evidence of permission,
  licensing, seller identity, or provider-field completeness.
- The 2026-09-20 product revision accepts named partner links and visibly
  labeled trial/sandbox data. This makes first-party airline adapters useful
  without treating an absent purchase URL as proof of an airline-direct link.
- One-call provider designs avoid turning a small personal search volume into
  a large request bill. Providers without a bounded flexible-date operation
  search only the exact requested dates and disclose that limitation.
- External provider code can be fixture-tested before credentials exist, but
  it remains conditional until one authenticated response verifies the current
  endpoint, schema, quota, and booking-link behavior.
- Direct-airline APIs provide carrier-specific inventory slices, not neutral
  comparison coverage. Adding airlines one by one is not a maintainable path
  to broad personal flight comparison.
- For the explicitly approved SerpApi experiment, broad coverage is obtained
  by accepting a scraping intermediary. The adapter must remain visibly
  experimental, omit unproved checked-bag and airline-direct claims, use no
  synthetic fallback, and enforce a six-request per-search ceiling.
- Bounded flexible searches contain independent date pairs. A transient
  failure in one pair must not discard offers already obtained from another;
  disclose partial coverage, preserve the total request ceiling, and fail the
  whole search only when no date pair completed.
- SerpApi's official Google Flights Autocomplete API can provide the city to
  airport relationship without inventing a local location database. Preserve
  direct IATA fallback, use the documented city KGMID for an all-airports
  search, expose specific-airport choices, validate returned endpoints against
  the suggestion's airport set, allowlist the credential-bearing endpoint,
  enforce both browser and server lookup limits, and disclose that
  autocomplete adds provider requests and retention.
- A disclosure control must keep the same layout position when opened and
  closed. Let its content expand below a stable full-width summary instead of
  moving the summary between flex alignment states.
- Fixture tests exposed why provider samples must be matched exactly:
  Singapore's official total is under `fareSummary.fareTotal.totalAmount`, and
  TUI documents `prices.totalPrice` plus a multi-step booking-link flow.
