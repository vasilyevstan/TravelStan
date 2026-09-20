# Contributing to TravelStan

## Branch and release flow

- `master` is the protected release branch.
- `dev` is the protected integration branch.
- Create every feature branch from `dev`; merge feature pull requests into
  `dev`.
- Release only through a pull request from `dev` to `master`.
- Do not push feature work directly to `dev` or `master`.

The designated orchestrator owns commits, pushes, pull requests, Actions,
approvals, merges, and releases. Reusable agents have no Git or deployment
authority. Pull requests require exact base/head revisions, focused validation
evidence, provider/privacy impact, risks and rollback, and the applicable
agent-chain results.

## Current branch-protection status

TravelStan is public as authorized on 2026-09-19. Both `master` and `dev` have
verified GitHub branch protection: pull-request workflow, strict `governance`
status checks, admin enforcement, stale-review dismissal, required
conversation resolution, and blocked force pushes/deletions. The protection
requires zero human approvals because CLI-owned work follows the authorized
automatic approval path after its exact-SHA checks pass.

## Development principles

- Keep TravelStan a small Django modular monolith with server-rendered pages.
- Use deterministic synthetic fixtures only in tests and CI; never use real
  provider calls or credentials there.
- Keep every external provider disabled until current first-party evidence,
  an issued credential, and a real response validate the configured use case.
- Never scrape, automate browsers, bypass access controls, expose secrets, or
  silently substitute synthetic results for a failed live request.
- Preserve unknown baggage, price, seller, and freshness information honestly.

## Agent chain

The initial product is a material change:

```text
travelstan-architect
  -> travelstan-simplifier (three sealed independent passes + synthesis)
  -> travelstan-developer
  -> travelstan-provider-integrity
  -> travelstan-critic-tester
  -> travelstan-final-validator
```

See [`.github/agents/README.md`](.github/agents/README.md) for roles,
handoffs, evidence binding, and stall handling.
