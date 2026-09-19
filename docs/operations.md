# Operations

`synthetic_demo` is the default credential-free mode. Live mode is disabled
until a documented provider `GO` decision and valid environment configuration
exist. A live failure must be explicit and must never fall back to synthetic
results.

## Running the demo

The application needs no credential, environment variable, or network egress.
`DJANGO_SECRET_KEY` and `DJANGO_DEBUG` are the only optional overrides, and no
setting enables a live provider.

```bash
uv venv --python 3.13 .venv
uv pip install -r requirements-dev.txt
.venv/bin/python manage.py check
.venv/bin/python manage.py test
.venv/bin/python manage.py runserver
```

The search path performs no database writes or reads, uses a dummy cache, has
no session or authentication middleware, and never logs query values, results,
or IP addresses.

## Repository controls

TravelStan was made public as authorized on 2026-09-19, which enabled GitHub
branch protection under the current account. `master` and `dev` require the
strict exact-SHA `governance` status check, enforce protections for admins,
require resolved conversations, dismiss stale reviews, and block force pushes
and deletions. The configured approval count is zero because CLI-owned work
uses the authorized automatic path once technical checks pass.
