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

TravelStan remains private. GitHub rejected the requested `master` and `dev`
branch-protection configuration on 2026-09-19 with HTTP 403: private-repository
branch protection requires GitHub Pro or a public repository for this account.
The team will continue to use the documented pull-request-only workflow, but
this is an explicit operational blocker—not a claim that server-enforced
protection is active. Do not make the repository public to work around it.

## Development principles

- Keep TravelStan a small Django modular monolith with server-rendered pages.
- Use deterministic synthetic fixtures only in tests and CI; never use real
  provider calls or credentials there.
- Treat provider access as `NO_GO` until current first-party evidence approves
  the exact comparison use case.
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
