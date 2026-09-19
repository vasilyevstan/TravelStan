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
