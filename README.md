# TravelStan

TravelStan is a lightweight, server-rendered application for comparing
airline-ticket alternatives. It does not sell tickets, accept payments, issue
tickets, service bookings, or guarantee fares.

## Status

The first runnable slice is implemented: a single Django `flights` app with a
server-rendered search form and result table. It runs without any external
credential or network access and uses a visibly labelled deterministic
`synthetic_demo` provider whose offers are fictional, non-live, and
non-bookable. Live fare search is disabled: the completed first-party provider
research found no `GO` provider for the required custom table and proven
airline-direct links. See [provider research](docs/provider-research.md).

## Development

Stack: Python 3.13, Django 5.2, SQLite (unused by search), server-rendered
templates, vanilla CSS, no JavaScript required.

### Local commands

```bash
# create the environment (uv)
uv venv --python 3.13 .venv
uv pip install -r requirements-dev.txt

# or with plain pip
python3.13 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt

# checks
.venv/bin/ruff format --check .
.venv/bin/ruff check .
.venv/bin/python manage.py check
.venv/bin/python manage.py test

# run the demo locally at http://127.0.0.1:8000/
.venv/bin/python manage.py runserver
```

No migrations, database records, caches, or sessions are used by the search
slice, and no provider credential or environment variable enables live data.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the protected branch workflow,
[docs/architecture.md](docs/architecture.md) for the accepted contract, and
[docs/testing.md](docs/testing.md) for the test layout.
