# Testing

Tests and CI use deterministic synthetic fixtures only. They must not make
real provider calls or require provider credentials.

The accepted contract requires Python 3.13 tests for IATA/date/mode/class
validation, blank one-way returns, bounded canonical flexible offsets,
four-way baggage, checked-bag filtering, deterministic dedupe/sort/ten-row
cap, absent demo purchase links, no-network operation, redacted errors, and
accessible server-rendered markup.
