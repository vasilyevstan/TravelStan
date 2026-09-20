# Released application review

## Resolution

All five findings were corrected on 2026-09-20 as part of the provider and UI
slice: paid extra bags are separate from fare inclusion, baggage retains
weight/unit, ancillary details participate in identity, sorting precedes
first-wins deduplication, and the cabin label is now “Economy+ / Premium
Economy.” The original review below is retained as the release record.

**Reviewed:** 2026-09-19  
**Release:** `2f9826c6286aba7102eab0c93745f272bb34cd61`

## Outcome

The released application is a working, accessible, dark-themed
`synthetic_demo` implementation of the approved non-live slice. It validates
routes and dates, supports one-way and round-trip searches, bounds flexible
dates, filters proven checked baggage, sorts and caps results, makes no
network request, and does not expose a seller, purchase link, credential,
booking, or payment flow.

Validation repeated during this review:

- Ruff lint and format checks passed.
- All 72 Django tests passed.
- The local application returned HTTP 200.
- A flexible `TLL` to `LHR` checked-bag-required request rendered ten
  synthetic rows with no seller.

## Findings

### 1. Extra paid bag is presented as included

Some synthetic fixtures model `extra_paid_bag` as `included` while also
showing a binding additional price. The UI can therefore render wording such
as “Extra paid bag: Included — 35 EUR,” although that price is not part of the
displayed fare total. This conflates a fare inclusion with a separately paid
ancillary.

**Required correction:** represent a separately paid bag as not included in
the fare while retaining its exact binding ancillary price, or introduce a
separate availability concept without weakening the three-state inclusion
contract.

### 2. The normalized baggage contract cannot retain weight

`BaggageAllowance` preserves state, quantity, and optional price, but has no
weight or weight-unit field. A future provider result containing a checked-bag
allowance such as 23 kg could not be normalized or displayed, despite the
original requirement to show weight when supplied.

**Required correction before live integration:** add an optional normalized
weight and unit with no inference from missing data.

### 3. Offer identity omits ancillary price details

The baggage portion of `Offer.identity()` includes slot, state, and quantity,
but omits ancillary amount, currency, and binding status. Two otherwise
identical offers with different exact extra-bag prices currently deduplicate
as equivalent.

**Required correction before paid baggage data:** include all binding
ancillary-price fields in the identity.

### 4. Deduplication precedes sorting

The accepted architecture called for deterministic sorting followed by
first-wins deduplication. The current pipeline deduplicates provider order
before sorting. Synthetic provider order is deterministic, so current output
is stable, but duplicate selection can differ from the documented rule.

**Required correction:** sort, then deduplicate, then apply the ten-row cap.

### 5. Premium cabin wording is narrower than requested

The control says “Premium Economy”; the requested product wording was
“Economy+ / Premium Economy.”

**Required correction:** use the requested user-facing label without changing
the normalized `premium_economy` value.

## Release assessment

None of these findings invalidates the clearly labelled synthetic-only
release. Findings 1 and 5 affect current presentation and should be corrected
in a focused regression-tested slice. Findings 2–4 are provider-boundary
correctness gaps that must be resolved before accepting live baggage or
ancillary data.
