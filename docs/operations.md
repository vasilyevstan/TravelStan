# Operations

`synthetic_demo` is the default credential-free mode. Live mode is disabled
until a documented provider `GO` decision and valid environment configuration
exist. A live failure must be explicit and must never fall back to synthetic
results.

## Repository controls

On 2026-09-19 GitHub returned HTTP 403 when applying protected branch rules to
this private repository: the current account requires GitHub Pro for that
feature. The repository remains private; the orchestrator must follow the
documented PR flow manually until an authorized account capability change
allows server-enforced `master` and `dev` protections.
