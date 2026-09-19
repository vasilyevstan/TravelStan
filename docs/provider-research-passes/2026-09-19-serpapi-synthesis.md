# SerpApi reassessment synthesis

**Date:** 2026-09-19  
**Model:** `gpt-5.6-terra`  
**Inputs:** sealed `gpt-6-astra`, `claude-opus-5`, and `grok-4.6` passes  
**Status:** `NO_GO` unchanged; `CONDITIONAL` for a deliberately revised private
experiment

The synthesis resolved that:

- SerpApi explicitly provides Google Flights scraping rather than a licensed
  airline or Google partner feed.
- Free pricing is 250 successful searches per month and 50 per hour.
- Exact enriched usage at 20 round-trip searches is approximately 240 calls;
  paired flexible ±1 is approximately 320 and ±7 approximately 800.
- `bags` is carry-on-only; checked-bag evidence is free text and cannot drive
  TravelStan's proof-required filter.
- seller metadata and Google redirects/phone actions are not proved
  airline-direct URLs.
- ordinary cache/archive retention applies and free accounts lack ZeroTrace.

No definitive legal adjudication was assumed. The result is a product-policy,
contract, privacy, and data-quality decision. See the normative matrix and
required revisions in [`../provider-research.md`](../provider-research.md).
