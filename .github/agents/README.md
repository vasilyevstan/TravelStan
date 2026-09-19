# TravelStan agent chain

The reusable agents below are development and review roles. They do not make
runtime provider calls, manage credentials, perform Git operations, approve
their own work, or deploy.

| Agent | Scope |
| --- | --- |
| `travelstan-architect` | Read-only architecture, provider boundary, privacy, and dependency-ordered contract. |
| `travelstan-simplifier` | Read-only sealed three-pass simplification/validation and separate synthesis. |
| `travelstan-developer` | Bounded implementation and focused tests; no Git or deployment authority. |
| `travelstan-provider-integrity` | Read-only source, terms, freshness, baggage, seller-link, and privacy review. |
| `travelstan-critic-tester` | Read-only adversarial functional, UX, security, contract, operations review and test execution. |
| `travelstan-final-validator` | Read-only release acceptance across all accumulated evidence. |

## Handoffs

Every handoff records this minimum non-sensitive evidence:

```yaml
slice_id: stable-kebab-id
from_agent: agent-name
to_agent: agent-name
status: namespaced-status
base_sha: exact SHA or no commits yet
head_sha: exact SHA or null
files_changed: []
findings:
  open: []
  resolved: []
tests:
  commands: []
  exit_codes: []
risks: []
```

Findings return to the agent that owns the affected stage. No agent approves
its own prior output. The orchestrator remains responsible for Git, PRs,
exact-SHA CI, eligible CLI-owned approvals, merges, releases, and stalled
handoffs. Reuse unchanged-source evidence only by binding its original SHA and
scope to the final candidate; required final-SHA CI still runs.

