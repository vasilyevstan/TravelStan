# Architecture

Architecture approval is pending. TravelStan will remain a Django modular
monolith with server-rendered templates, SQLite for local development,
deterministic `synthetic_demo` by default, and a small normalized provider
interface. It will not contain booking, payment, ticketing, booking support,
scraping, or an unapproved live provider.

