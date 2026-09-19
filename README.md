# TravelStan

TravelStan is a lightweight, server-rendered application for comparing
airline-ticket alternatives. It does not sell tickets, accept payments, issue
tickets, service bookings, or guarantee fares.

## Status

The initial implementation is in progress. It will run without external
credentials using a visibly labelled deterministic `synthetic_demo` provider.
Live fare search is disabled: the completed first-party provider research found
no `GO` provider for the required custom table and proven airline-direct links.
See [provider research](docs/provider-research.md).

## Development

The intended stack is Python 3.13, Django 5.2, SQLite, server-rendered
templates, vanilla CSS, and minimal vanilla JavaScript. Setup and release
instructions will be added with the first runnable slice.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the protected branch workflow and
[docs/architecture.md](docs/architecture.md) for the provider boundary once
the architecture gate is complete.
