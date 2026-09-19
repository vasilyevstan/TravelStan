# Operations

`synthetic_demo` is the default credential-free mode. Live mode is disabled
until a documented provider `GO` decision and valid environment configuration
exist. A live failure must be explicit and must never fall back to synthetic
results.

## Repository controls

TravelStan was made public as authorized on 2026-09-19, which enabled GitHub
branch protection under the current account. `master` and `dev` require the
strict exact-SHA `governance` status check, enforce protections for admins,
require resolved conversations, dismiss stale reviews, and block force pushes
and deletions. The configured approval count is zero because CLI-owned work
uses the authorized automatic path once technical checks pass.
