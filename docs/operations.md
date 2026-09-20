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

## External providers

Create developer applications with the providers you intend to use, then
export only those providers and keys. Never put populated secrets in the
repository or client-side code.

```bash
export TRAVELSTAN_PROVIDERS=afkl,singapore,tui
export AFKL_API_KEY='...'
export SINGAPORE_API_KEY='...'
export TUI_API_KEY='...'
.venv/bin/python manage.py check --fail-level WARNING
```

Use `AFKL_DATA_STATUS`, `SINGAPORE_DATA_STATUS`, and `TUI_DATA_STATUS` to
select `trial`, `sandbox`, or `live`. Their default is `trial`; change one to
`live` only after the provider confirms production data for the issued
credential.

`TRAVELSTAN_COUNTRY=EE` and `TRAVELSTAN_LOCALE=en-EE` set the local point of
sale and language. TUI currently requires GBP in this adapter.
`AFKL_TRAVEL_HOST` accepts `KL` or `AF` and defaults to `KL`.

## Failure and quota behavior

- One search makes zero upstream calls in synthetic mode and at most one call
  to each configured external provider.
- Calls run concurrently with an eight-second timeout and no retry.
- A partial outage leaves other results visible with a generic provider notice.
- Total external failure produces one redacted error and never synthetic data.
- No response cache or persistent quota ledger exists. At twenty searches per
  month, three configured providers produce at most sixty search calls, plus
  any manual credential-validation calls.

HTTP 401/403 means the relevant key, product subscription, or environment is
wrong. HTTP 429 means the provider quota is exhausted. Neither condition is
retried automatically.

## Credential validation checklist

Before changing a provider from trial to live:

1. Run `manage.py check` with only that provider selected.
2. Submit one ordinary exact-date search on a route the provider operates.
3. Confirm that the result is current and that price currency and passenger
   scope match the provider page.
4. Open one rendered booking link and confirm its seller and itinerary without
   sharing or recording the full URL.
5. Confirm the account's current quota, retention, and permitted personal-use
   terms in the provider portal.

Disable a provider immediately by removing it from `TRAVELSTAN_PROVIDERS`.
